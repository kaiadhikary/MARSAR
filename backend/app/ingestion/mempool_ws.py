"""
Async WebSocket consumer for the live Bitcoin mempool.

Maintains a persistent connection to mempool.space's public WebSocket API,
subscribes to the raw mempool transaction feed, normalizes incoming
transactions via `parser.parse_raw_tx`, and pushes them onto an
`asyncio.Queue` for the clustering/scoring engines to consume downstream.

Reconnects automatically with exponential backoff on any disconnect, since
this worker is expected to run unattended as a long-lived daemon
(see run_worker.py).

Note: mempool.space's public docs describe `{"track-mempool": true}` as the
subscription for new-mempool-transaction events. The exact response
envelope key can shift between API versions — check the current
wss://mempool.space/api/v1/ws docs before a live demo, and adjust
`_extract_transactions` below if the key name has changed.
"""
from __future__ import annotations

import asyncio
import json
import logging

import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import settings
from app.ingestion.parser import parse_batch

logger = logging.getLogger("btif.ingestion.mempool_ws")

# Subscribe to the raw new-transaction mempool event stream.
_SUBSCRIBE_PAYLOAD = json.dumps({"track-mempool": True})

# Keys mempool.space has used (or plausibly could use) to carry new
# transaction payloads in a track-mempool response. We check all of them
# defensively so a minor API naming change doesn't silently drop data.
_TX_PAYLOAD_KEYS = ("mempool-transactions", "transactions", "added")


def _extract_transactions(message: dict) -> list[dict]:
    for key in _TX_PAYLOAD_KEYS:
        if key in message and isinstance(message[key], list):
            return message[key]
    return []


async def consume_mempool(queue: asyncio.Queue) -> None:
    """
    Connect to the mempool WebSocket and push normalized transactions onto
    `queue` forever. Intended to be run as a background asyncio task.
    """
    delay = settings.WS_RECONNECT_MIN_DELAY

    while True:
        try:
            async with websockets.connect(
                settings.MEMPOOL_WS_URL, ping_interval=20, ping_timeout=20
            ) as ws:
                logger.info("Connected to mempool WebSocket: %s", settings.MEMPOOL_WS_URL)
                await ws.send(_SUBSCRIBE_PAYLOAD)
                delay = settings.WS_RECONNECT_MIN_DELAY  # reset backoff on success

                async for raw_message in ws:
                    try:
                        message = json.loads(raw_message)
                    except json.JSONDecodeError:
                        logger.warning("Dropped non-JSON WS frame")
                        continue

                    raw_txs = _extract_transactions(message)
                    if not raw_txs:
                        continue

                    for parsed_tx in parse_batch(raw_txs):
                        await queue.put(parsed_tx)

        except (ConnectionClosed, OSError) as exc:
            logger.warning("Mempool WS disconnected (%s); reconnecting in %.1fs", exc, delay)
        except Exception:
            logger.exception("Unexpected error in mempool WS consumer; reconnecting in %.1fs", delay)

        await asyncio.sleep(delay)
        delay = min(delay * 2, settings.WS_RECONNECT_MAX_DELAY)
