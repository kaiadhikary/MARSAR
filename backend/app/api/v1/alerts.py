"""WebSocket alerts for mempool events (high-risk tx / address hits)."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.websocket("/ws")
async def alerts_ws(websocket: WebSocket):
    """
    Live feed of high-risk transaction alerts. Once scoring.py is wired up,
    this should subscribe to a broadcast channel fed by the scoring engine
    (risk_score >= THRESHOLD_HIGH_RISK) rather than the raw tx queue.
    """
    await websocket.accept()
    try:
        while True:
            # Placeholder: echo a heartbeat until the scoring engine
            # publishes real alert events for this connection to relay.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
