"""
Root FastAPI application entry point.

Starts the mempool ingestion consumer as a background task on app startup,
exposes it via `app.state.tx_queue` so downstream routers (alerts, trace,
graph) can consume parsed transactions, and mounts the v1 API routers.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import alerts, compliance, graph, trace
from app.core.config import settings
from app.ingestion.mempool_ws import consume_mempool

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tx_queue = asyncio.Queue(maxsize=10_000)
    ingestion_task = asyncio.create_task(consume_mempool(app.state.tx_queue))
    yield
    ingestion_task.cancel()
    try:
        await ingestion_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.include_router(alerts.router, prefix=settings.API_V1_PREFIX)
app.include_router(compliance.router, prefix=settings.API_V1_PREFIX)
app.include_router(graph.router, prefix=settings.API_V1_PREFIX)
app.include_router(trace.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
