"""
Async WebSocket consumer for the live Bitcoin mempool.

Maintains a persistent connection to mempool.space's public WebSocket API.
The socket itself only announces lightweight events (new txids entering the
mempool, single hydrated tx payloads on some channels, and new block
headers) — full transaction detail for a txid-only announcement has to be
fetched separately over REST. This module does both: WS for the live event
stream, REST (via aiohttp) to hydrate txids into full transaction JSON,
normalizes everything through `parser.parse_raw_tx`, and pushes parsed
transactions onto the shared `asyncio.Queue`.

Fixed vs. the previous version of this file (see handover notes):
  - No more truncating a mempool burst to the first 8 txids. Every
    announced txid is fetched; concurrency is bounded by a semaphore
    instead of by silently dropping the rest of the list.
  - REST fetch tasks are tracked in a set (not fire-and-forget
    `asyncio.create_task` calls with no reference kept), so they can be
    accounted for, retried, and cancelled cleanly on reconnect/shutdown.
  - REST fetch failures are logged at WARNING (previously DEBUG, which
    made real data loss invisible in a normal INFO-level production log),
    plus a running failure counter surfaced via `get_ingestion_stats()`.
  - A small bounded set of "already fetched" txids prevents duplicate REST
    calls when mempool.space re-announces the same txid across messages.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import settings
from app.ingestion.parser import parse_raw_tx

logger = logging.getLogger("btif.ingestion.mempool_ws")

MEMPOOL_API_BASE = getattr(settings, "MEMPOOL_API_BASE_URL", "https://mempool.space/api")

# Bounds how many REST hydration requests are in flight at once. This
# replaces the old `added_txids[:8]` truncation: every txid is still
# fetched, just not all at the same instant.
_MAX_CONCURRENT_FETCHES = 16
_REST_FETCH_TIMEOUT_SECONDS = 8
_REST_MAX_RETRIES = 2

# Small ring buffer of recently-hydrated txids to skip duplicate REST calls
# when the same txid is re-announced (mempool.space does this on RBF bumps
# and reconnect replays).
_RECENT_TXID_CAP = 5_000


class IngestionStats:
    """Lightweight counters so ingestion health is observable, not just logged."""

    def __init__(self) -> None:
        self.txids_announced = 0
        self.tx_fetched_ok = 0
        self.tx_fetch_failed = 0
        self.tx_direct_payload = 0
        self.blocks_seen = 0

    def as_dict(self) -> dict:
        return {
            "txids_announced": self.txids_announced,
            "tx_fetched_ok": self.tx_fetched_ok,
            "tx_fetch_failed": self.tx_fetch_failed,
            "tx_direct_payload": self.tx_direct_payload,
            "blocks_seen": self.blocks_seen,
        }


stats = IngestionStats()


async def _fetch_and_enqueue_tx(
    session: aiohttp.ClientSession,
    txid: str,
    queue: asyncio.Queue,
    semaphore: asyncio.Semaphore,
) -> None:
    """Fetch one transaction's full JSON over REST and push it onto `queue`.

    Retries transient failures up to `_REST_MAX_RETRIES` times before
    counting the txid as dropped. Bounded by `semaphore` so a burst of
    announcements doesn't open hundreds of simultaneous connections.
    """
    url = f"{MEMPOOL_API_BASE}/tx/{txid}"
    async with semaphore:
        last_exc: Exception | None = None
        for attempt in range(1, _REST_MAX_RETRIES + 1):
            try:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=_REST_FETCH_TIMEOUT_SECONDS)
                ) as resp:
                    if resp.status == 404:
                        # Already confirmed and evicted from mempool, or an
                        # RBF replacement — not a failure worth retrying.
                        return
                    resp.raise_for_status()
                    raw_tx = await resp.json()

                parsed_tx = parse_raw_tx(raw_tx)
                if parsed_tx:
                    await queue.put(parsed_tx)
                    stats.tx_fetched_ok += 1
                return
            except Exception as exc:  # noqa: BLE001 - genuinely want to catch+retry broadly here
                last_exc = exc
                if attempt < _REST_MAX_RETRIES:
                    await asyncio.sleep(0.5 * attempt)

        # Every retry failed — this is real data loss, so it's WARNING, not
        # DEBUG. The old version logged this at DEBUG, which meant a
        # production INFO-level log looked perfectly healthy while
        # transactions were silently never reaching the queue.
        stats.tx_fetch_failed += 1
        logger.warning("Giving up on tx %s after %d attempts: %s", txid[:12], _REST_MAX_RETRIES, last_exc)


async def consume_mempool(queue: asyncio.Queue) -> None:
    """
    Connect to the mempool WebSocket and push normalized transactions onto
    `queue` forever. Intended to be run as a background asyncio task.
    """
    delay = settings.WS_RECONNECT_MIN_DELAY
    recent_txids: deque[str] = deque(maxlen=_RECENT_TXID_CAP)
    recent_txids_set: set[str] = set()

    def _mark_seen(txid: str) -> bool:
        """Returns True if this is a new txid (and records it), False if a dup."""
        if txid in recent_txids_set:
            return False
        if len(recent_txids) == recent_txids.maxlen:
            oldest = recent_txids[0]
            recent_txids_set.discard(oldest)
        recent_txids.append(txid)
        recent_txids_set.add(txid)
        return True

    while True:
        in_flight: set[asyncio.Task] = set()
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

        try:
            async with websockets.connect(
                settings.MEMPOOL_WS_URL,
                ping_interval=20,
                ping_timeout=20,
                max_size=32 * 1024 * 1024,
            ) as ws, aiohttp.ClientSession() as http_session:

                logger.info("Connected to mempool WebSocket: %s", settings.MEMPOOL_WS_URL)

                await ws.send(json.dumps({"action": "init"}))
                await ws.send(json.dumps({"action": "want", "data": ["blocks", "mempool-blocks", "stats"]}))
                await ws.send(json.dumps({"track-mempool-txids": True}))

                logger.info("Sent mempool subscription protocol. Awaiting live events...")
                delay = settings.WS_RECONNECT_MIN_DELAY

                async for raw_message in ws:
                    try:
                        message = json.loads(raw_message)
                    except json.JSONDecodeError:
                        logger.warning("Dropped non-JSON WS frame")
                        continue

                    # Unconfirmed transactions entering the mempool. Every
                    # announced txid is fetched now (no [:8] truncation) —
                    # concurrency is bounded by the semaphore inside
                    # _fetch_and_enqueue_tx instead.
                    if "mempool-txids" in message:
                        added_txids = message["mempool-txids"].get("added", [])
                        new_txids = [t for t in added_txids if _mark_seen(t)]
                        if new_txids:
                            stats.txids_announced += len(new_txids)
                            logger.info(
                                "Mempool surge: %d new unconfirmed txids (%d duplicate/seen skipped)",
                                len(new_txids), len(added_txids) - len(new_txids),
                            )
                            for txid in new_txids:
                                task = asyncio.create_task(
                                    _fetch_and_enqueue_tx(http_session, txid, queue, semaphore)
                                )
                                in_flight.add(task)
                                task.add_done_callback(in_flight.discard)

                    # Some channels push a full transaction payload directly.
                    elif "tx" in message and isinstance(message["tx"], dict):
                        parsed_tx = parse_raw_tx(message["tx"])
                        if parsed_tx:
                            await queue.put(parsed_tx)
                            stats.tx_direct_payload += 1

                    elif "block" in message:
                        height = message["block"].get("height", "unknown")
                        stats.blocks_seen += 1
                        logger.info("New Bitcoin block confirmed on-chain: #%s", height)

        except (ConnectionClosed, OSError) as exc:
            logger.warning("Mempool WS disconnected (%s); reconnecting in %.1fs", exc, delay)
        except Exception:
            logger.exception("Unexpected error in mempool WS consumer; reconnecting in %.1fs", delay)
        finally:
            # Don't let REST hydration tasks from a dying connection leak
            # into the next reconnect cycle.
            for task in list(in_flight):
                task.cancel()
            if in_flight:
                await asyncio.gather(*in_flight, return_exceptions=True)

        await asyncio.sleep(delay)
        delay = min(delay * 2, settings.WS_RECONNECT_MAX_DELAY)


def get_ingestion_stats() -> dict:
    """Exposed for a future /health or /metrics endpoint (see report P2 item)."""
    return stats.as_dict()
