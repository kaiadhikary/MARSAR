"""Address & TXID forensic inspection triggers."""
from fastapi import APIRouter

router = APIRouter(prefix="/trace", tags=["trace"])


@router.get("/address/{address}")
async def trace_address(address: str):
    """Look up cluster membership, risk score, and tx history for an address."""
    return {"status": "not_implemented", "address": address}


@router.get("/tx/{txid}")
async def trace_tx(txid: str):
    """Look up parsed details and risk score for a single transaction."""
    return {"status": "not_implemented", "txid": txid}
