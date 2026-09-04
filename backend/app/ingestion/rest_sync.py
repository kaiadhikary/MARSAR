"""
Blockstream REST client for historical hops.

This is the second half of Engine 1's "dual-layer" design: `mempool_ws.py`
gives us the live, unconfirmed layer; this module gives us the historical /
confirmed layer, used for:

  1. Fallback ingestion when the WebSocket connection is down (block
     ingestion never fully stops).
  2. Multi-hop graph expansion — when the clustering/graph engine needs to
     walk backward or forward from a UTXO that isn't in our live queue
     history, it calls out here.

Uses Blockstream's public Esplora API (https://blockstream.info/api), which
returns the same tx JSON shape mempool.space does, so everything routes
through the same `parser.parse_raw_tx` / `parse_batch` normalization used by
the WebSocket layer — one internal transaction format regardless of source.
"""
from __future__ import annotations

import asyncio
import logging

import aiohttp

from app.core.config import settings
from app.ingestion.parser import parse_batch, parse_raw_tx

logger = logging.getLogger("btif.ingestion.rest_sync")

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0


class RestSyncClient:
    """Thin async wrapper around the Blockstream Esplora REST API."""

    def __init__(self, base_url: str | None = None, session: aiohttp.ClientSession | None = None):
        self.base_url = (base_url or settings.BLOCKSTREAM_REST_URL).rstrip("/")
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "RestSyncClient":
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT)
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()

    async def _get_json(self, path: str):
        assert self._session is not None, "Use RestSyncClient as an async context manager"
        url = f"{self.base_url}{path}"

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with self._session.get(url) as resp:
                    if resp.status == 404:
                        return None
                    resp.raise_for_status()
                    return await resp.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = exc
                delay = _RETRY_BASE_DELAY * attempt
                logger.warning(
                    "REST request failed (%s), attempt %d/%d, retrying in %.1fs: %s",
                    url, attempt, _MAX_RETRIES, delay, exc,
                )
                await asyncio.sleep(delay)

        logger.error("REST request permanently failed after %d attempts: %s", _MAX_RETRIES, url)
        raise last_exc  # type: ignore[misc]

    # --- Public API -----------------------------------------------------

    async def get_tx(self, txid: str) -> dict | None:
        """Fetch and normalize a single transaction by TXID."""
        raw = await self._get_json(f"/tx/{txid}")
        if raw is None:
            return None
        return parse_raw_tx(raw)

    async def get_address_txs(self, address: str, after_txid: str | None = None) -> list[dict]:
        """
        Fetch and normalize the (up to 25 most recent, per Esplora paging)
        confirmed + mempool transactions touching `address`. Pass
        `after_txid` (the last txid of a previous page) to page further back.
        """
        path = f"/address/{address}/txs"
        if after_txid:
            path += f"/chain/{after_txid}"
        raw_txs = await self._get_json(path)
        if not raw_txs:
            return []
        return parse_batch(raw_txs)

    async def get_address_all_txs(self, address: str, max_pages: int = 10) -> list[dict]:
        """
        Page through all available history for `address`, up to `max_pages`
        pages (Esplora returns ~25 txs/page), for multi-hop backfill.
        """
        all_txs: list[dict] = []
        after_txid: str | None = None

        for _ in range(max_pages):
            page = await self.get_address_txs(address, after_txid=after_txid)
            if not page:
                break
            all_txs.extend(page)
            after_txid = page[-1]["txid"]
            if len(page) < 25:
                break  # last page was partial -> no more history

        return all_txs

    async def get_tip_height(self) -> int | None:
        """Fetch the current confirmed blockchain tip height."""
        assert self._session is not None, "Use RestSyncClient as an async context manager"
        url = f"{self.base_url}/blocks/tip/height"
        async with self._session.get(url) as resp:
            if resp.status != 200:
                return None
            text = await resp.text()
            try:
                return int(text)
            except ValueError:
                return None


async def backfill_address(address: str, queue: asyncio.Queue, max_pages: int = 10) -> int:
    """
    Convenience helper: fetch an address's full known history via REST and
    push every parsed transaction onto the shared ingestion queue, same as
    the live WS layer does. Returns the number of transactions enqueued.

    Typical use: the graph engine hits a gap in its local data during a
    multi-hop trace and needs to backfill an address's history on demand.
    """
    async with RestSyncClient() as client:
        txs = await client.get_address_all_txs(address, max_pages=max_pages)

    for tx in txs:
        await queue.put(tx)

    logger.info("Backfilled %d transactions for %s via REST", len(txs), address)
    return len(txs)
