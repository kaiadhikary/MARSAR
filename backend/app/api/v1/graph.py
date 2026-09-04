"""Multi-hop graph expansion & entity cluster querying."""
from fastapi import APIRouter

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/expand/{address}")
async def expand_address(address: str, hops: int = 3):
    """
    Return the multi-hop fund-flow subgraph around `address`, out to `hops`
    hops. Wire this to app.engine.clustering / NetworkX once built.
    """
    return {"status": "not_implemented", "address": address, "hops": hops}
