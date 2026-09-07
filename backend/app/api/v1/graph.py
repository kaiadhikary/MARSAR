import json
from typing import Dict, Any, List
from fastapi import APIRouter, Query, HTTPException, status
from app.db.sqlite_client import get_db_connection
from app.engine.clustering import EntityClusterEngine

router = APIRouter()


@router.get("/topology")
def get_graph_topology(limit_tx: int = Query(100, ge=1, le=500)):
    """
    Returns graph topology formatted for Cytoscape and link-analysis visualizers.
    Builds unique nodes and directional edges linking IPs, Wallets, and Transactions
    without identifier collisions.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    tx_rows = cur.execute(
        "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?",
        (limit_tx,)
    ).fetchall()

    cluster_rows = cur.execute("SELECT * FROM entity_clusters").fetchall()
    clusters = {c["wallet_address"]: c["cluster_id"] for c in cluster_rows}

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_nodes = set()

    for tx in tx_rows:
        txid = tx["txid"]
        src_ip = (tx["src_ip"] or "").strip()
        dst_ip = (tx["dst_ip"] or "").strip()

        # 1. Transaction Node
        if txid not in seen_nodes:
            nodes.append({
                "data": {
                    "id": txid,
                    "label": f"TX: {txid[:8]}...",
                    "type": "transaction",
                    "btc": tx["total_input_btc"],
                    "fee": tx["fee"],
                    "country": tx["geo_country"] or "UNKNOWN"
                }
            })
            seen_nodes.add(txid)

        # 2. Network IP Node & P2P Edge
        if src_ip and src_ip != "UNKNOWN":
            ip_node_id = f"ip_{src_ip}"
            if ip_node_id not in seen_nodes:
                nodes.append({
                    "data": {
                        "id": ip_node_id,
                        "label": f"IP: {src_ip}",
                        "type": "ip",
                        "ip": src_ip,
                        "country": tx["geo_country"] or "UNKNOWN",
                        "asn": tx["geo_asn"] or "UNKNOWN"
                    }
                })
                seen_nodes.add(ip_node_id)

            edges.append({
                "data": {
                    "id": f"e_ip_{src_ip}_{txid}",
                    "source": ip_node_id,
                    "target": txid,
                    "relation": "BROADCASTED_FROM"
                }
            })

        # Preserve the receiving peer too: source and destination observations are
        # distinct evidence in P2P traffic correlation.
        if dst_ip and dst_ip != "UNKNOWN":
            dst_node_id = f"ip_{dst_ip}"
            if dst_node_id not in seen_nodes:
                nodes.append({"data": {
                    "id": dst_node_id, "label": f"IP: {dst_ip}", "type": "ip",
                    "ip": dst_ip, "country": tx["geo_country"] or "UNKNOWN",
                    "asn": tx["geo_asn"] or "UNKNOWN"
                }})
                seen_nodes.add(dst_node_id)
            edges.append({"data": {
                "id": f"e_tx_{txid}_dst_{dst_ip}", "source": txid, "target": dst_node_id,
                "relation": "OBSERVED_BY", "src_port": tx["src_port"],
                "dst_port": tx["dst_port"], "timestamp": tx["timestamp"]
            }})

        # 3. Input Wallet Nodes & Ingress Edges (Wallet -> TX)
        try:
            inputs = json.loads(tx["inputs_json"])
        except (ValueError, TypeError):
            inputs = []

        for idx, inp in enumerate(inputs):
            addr = inp.get("address")
            amt = float(inp.get("amount") or 0.0)
            if addr:
                if addr not in seen_nodes:
                    nodes.append({
                        "data": {
                            "id": addr,
                            "label": f"W: {addr[:8]}...",
                            "type": "wallet",
                            "cluster": clusters.get(addr, "UNCLUSTERED")
                        }
                    })
                    seen_nodes.add(addr)

                # Append index to guarantee edge uniqueness for multi-input transactions
                edges.append({
                    "data": {
                        "id": f"e_in_{addr}_{txid}_{idx}",
                        "source": addr,
                        "target": txid,
                        "amount": amt,
                        "relation": "SPENT_IN"
                    }
                })

        # 4. Output Wallet Nodes & Egress Edges (TX -> Wallet)
        try:
            outputs = json.loads(tx["outputs_json"])
        except (ValueError, TypeError):
            outputs = []

        for idx, out in enumerate(outputs):
            addr = out.get("address")
            amt = float(out.get("amount") or 0.0)
            if addr:
                if addr not in seen_nodes:
                    nodes.append({
                        "data": {
                            "id": addr,
                            "label": f"W: {addr[:8]}...",
                            "type": "wallet",
                            "cluster": clusters.get(addr, "UNCLUSTERED")
                        }
                    })
                    seen_nodes.add(addr)

                # Append index to guarantee edge uniqueness for multi-output transactions
                edges.append({
                    "data": {
                        "id": f"e_out_{txid}_{addr}_{idx}",
                        "source": txid,
                        "target": addr,
                        "amount": amt,
                        "relation": "TRANSFERRED_TO"
                    }
                })

    conn.close()
    return {"elements": {"nodes": nodes, "edges": edges}}


@router.get("/clusters")
def get_clusters():
    """
    Returns grouped wallet clusters derived from Common-Input-Ownership Heuristics (CIOH)
    and network IP co-location.
    """
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT cluster_id, primary_ip, confidence, COUNT(wallet_address) as wallet_count,
               GROUP_CONCAT(wallet_address, ',') as addresses
        FROM entity_clusters
        GROUP BY cluster_id
        ORDER BY wallet_count DESC
    ''').fetchall()
    conn.close()

    clusters = []
    for r in rows:
        addr_list = [a.strip() for a in (r["addresses"] or "").split(",") if a.strip()]
        clusters.append({
            "cluster_id": r["cluster_id"],
            "primary_ip": r["primary_ip"],
            "confidence": float(r["confidence"] or 0.95),
            "wallet_count": r["wallet_count"],
            "addresses": addr_list
        })
    return {"total_clusters": len(clusters), "clusters": clusters}


@router.post("/clusters/rebuild")
def rebuild_clusters():
    """
    Triggers execution of the offline CIOH clustering and IP co-location algorithms.
    """
    try:
        engine = EntityClusterEngine()
        clusters = engine.run_clustering()
        return {
            "status": "success",
            "cluster_count": len(clusters),
            "message": "Entity clusters successfully recomputed."
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clustering execution failed: {str(exc)}"
        )
