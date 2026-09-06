"""Multi-hop graph expansion & entity cluster querying."""
from __future__ import annotations

from fastapi import APIRouter

from app.db.sqlite_client import get_cluster_by_address, check_address_blacklist

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/expand/{address}")
async def expand_address(address: str, hops: int = 3):
    """
    Return the fund-flow subgraph around `address` as Cytoscape-ready
    nodes/edges.

    Current data model: `clusters` + `address_clusters` (populated by the
    ingestion worker's CIOH clustering step) give us a hub-and-spoke view —
    a cluster's root address plus every address the DSU has merged into
    that same entity. That's what this endpoint expands today.

    `hops` is accepted for forward-compatibility with a future
    transaction-level (address -> address, via txid) expansion once that
    graph is persisted; it isn't used yet because only cluster membership
    is currently stored, not individual tx edges.
    """
    cluster = get_cluster_by_address(address)

    if cluster is None:
        # No cluster on record for this address yet — still return a
        # valid (single-node) graph rather than an error, so the frontend
        # always has something to render.
        hit = check_address_blacklist(address)
        return {
            "status": "ok",
            "address": address,
            "hops": hops,
            "cluster": None,
            "nodes": [
                {
                    "id": address,
                    "label": _short(address),
                    "is_root": True,
                    "is_blacklisted": hit is not None,
                    "blacklist_entity": hit.get("entity_label") if hit else None,
                }
            ],
            "edges": [],
        }

    root = cluster["root_address"]
    members = cluster.get("members", [])

    nodes = []
    edges = []
    seen_ids = set()

    for member in members:
        hit = check_address_blacklist(member)
        nodes.append({
            "id": member,
            "label": _short(member),
            "is_root": member == root,
            "is_blacklisted": hit is not None,
            "blacklist_entity": hit.get("entity_label") if hit else None,
        })
        seen_ids.add(member)
        if member != root:
            edges.append({
                "id": f"{root}->{member}",
                "source": root,
                "target": member,
            })

    # The queried address is always present, even if it wasn't in the
    # members list returned (defensive — keeps the graph anchored on what
    # the user actually asked for).
    if address not in seen_ids:
        hit = check_address_blacklist(address)
        nodes.append({
            "id": address,
            "label": _short(address),
            "is_root": address == root,
            "is_blacklisted": hit is not None,
            "blacklist_entity": hit.get("entity_label") if hit else None,
        })

    return {
        "status": "ok",
        "address": address,
        "hops": hops,
        "cluster": {
            "cluster_id": cluster["cluster_id"],
            "root_address": root,
            "member_count": cluster["member_count"],
            "risk_score": cluster["risk_score"],
            "first_seen": cluster["first_seen"],
            "last_updated": cluster["last_updated"],
        },
        "nodes": nodes,
        "edges": edges,
    }


def _short(address: str) -> str:
    """Shorten an address for node labels (e.g. bc1qxy...z9k4)."""
    if len(address) <= 14:
        return address
    return f"{address[:8]}…{address[-4:]}"
