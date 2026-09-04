"""
Standalone daemon running live ingestion.

Runs the mempool WebSocket consumer independently of the FastAPI process —
useful for deployments where you want ingestion to keep running (and be
restarted by systemd/Docker) separately from the API server, or for local
debugging of the ingestion pipeline in isolation.

Usage:
    python run_worker.py
"""
from __future__ import annotations

import asyncio
import logging

from app.ingestion.mempool_ws import consume_mempool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("btif.run_worker")


async def main() -> None:
    queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)

    consumer_task = asyncio.create_task(consume_mempool(queue))

    logger.info("Ingestion worker started. Draining queue to stdout...")
    try:
        while True:
            tx = await queue.get()
            logger.info(
                "tx=%s inputs=%d outputs=%d fee_rate=%.2f sat/vB",
                tx["txid"],
                tx["num_inputs"],
                tx["num_outputs"],
                tx["fee_rate_sat_vb"] or 0.0,
            )
    except asyncio.CancelledError:
        pass
    finally:
        consumer_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down.")
