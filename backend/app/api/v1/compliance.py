from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.db.sqlite_client import get_db_connection
from app.engine.scoring import RiskPropagationEngine

router = APIRouter()


class SeedItem(BaseModel):
    address: str
    category: str
    severity: float = 1.0


@router.get("/seeds")
def list_illicit_seeds():
    """Retrieves all seeded OFAC, ransomware, and darknet watchlist addresses."""
    conn = get_db_connection()
    seeds = conn.execute("SELECT * FROM illicit_seeds ORDER BY severity DESC").fetchall()
    conn.close()

    return {
        "total_seeds": len(seeds),
        "seeds": [dict(s) for s in seeds]
    }


@router.post("/seeds")
def add_illicit_seed(seed: SeedItem):
    """Registers an illicit seed address into the offline watchlist database."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO illicit_seeds (address, category, severity)
        VALUES (?, ?, ?)
    ''', (seed.address.strip(), seed.category.strip().upper(), seed.severity))
    conn.commit()
    conn.close()

    return {"status": "success", "message": f"Seed address {seed.address} registered."}


@router.delete("/seeds/{address}")
def delete_illicit_seed(address: str):
    """Removes an address from the illicit seed table."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM illicit_seeds WHERE address = ?", (address.strip(),))
    conn.commit()
    conn.close()

    return {"status": "success", "message": f"Seed {address} removed."}


@router.get("/check/{address}")
def screen_address(address: str):
    """
    Performs on-demand screening of an address against seeds and graph taint scores.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    seed = cur.execute("SELECT * FROM illicit_seeds WHERE address = ?", (address,)).fetchone()
    cluster = cur.execute("SELECT cluster_id FROM entity_clusters WHERE wallet_address = ?", (address,)).fetchone()
    conn.close()

    engine = RiskPropagationEngine()
    taint_map = engine.propagate_taint()
    taint_score = taint_map.get(address, 0.0)

    is_direct_hit = seed is not None
    return {
        "address": address,
        "is_sanctioned_seed": is_direct_hit,
        "seed_category": seed["category"] if seed else None,
        "cluster_id": cluster["cluster_id"] if cluster else "UNCLUSTERED",
        "propagated_taint_score": taint_score,
        "compliance_verdict": "BLOCKED" if (is_direct_hit or taint_score > 0.5) else "CLEAR"
    }