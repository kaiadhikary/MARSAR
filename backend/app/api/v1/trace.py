from fastapi import APIRouter, HTTPException
import json
from typing import Dict, Any, List
from app.db.sqlite_client import get_db_connection

router = APIRouter()


@router.get("/tx/{txid}")
def trace_transaction_hop(txid: str):
    """
    Returns forward and backward hop context for a specific transaction ID.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    tx = cur.execute("SELECT * FROM transactions WHERE txid = ?", (txid,)).fetchone()
    if not tx:
        conn.close()
        raise HTTPException(status_code=404, detail="Transaction not found.")

    inputs = json.loads(tx["inputs_json"])
    outputs = json.loads(tx["outputs_json"])

    in_addresses = [i["address"] for i in inputs if i.get("address")]
    backward_hops = []
    for addr in in_addresses:
        prior_txs = cur.execute(
            "SELECT txid, outputs_json FROM transactions WHERE outputs_json LIKE ? AND txid != ? LIMIT 3",
            (f"%{addr}%", txid)
        ).fetchall()
        for p_tx in prior_txs:
            backward_hops.append({"funding_txid": p_tx["txid"], "via_address": addr})

    out_addresses = [o["address"] for o in outputs if o.get("address")]
    forward_hops = []
    for addr in out_addresses:
        subsequent_txs = cur.execute(
            "SELECT txid, inputs_json FROM transactions WHERE inputs_json LIKE ? AND txid != ? LIMIT 3",
            (f"%{addr}%", txid)
        ).fetchall()
        for s_tx in subsequent_txs:
            forward_hops.append({"spent_in_txid": s_tx["txid"], "from_address": addr})

    conn.close()
    return {
        "txid": txid,
        "timestamp": tx["timestamp"],
        "total_btc": tx["total_input_btc"],
        "network": {
            "src_ip": tx["src_ip"],
            "country": tx["geo_country"],
            "asn": tx["geo_asn"]
        },
        "inputs": inputs,
        "outputs": outputs,
        "backward_lineage": backward_hops,
        "forward_lineage": forward_hops
    }


@router.get("/wallet/{address}")
def trace_wallet_flows(address: str):
    """
    Summarizes all ingress and egress flows and cluster identity for a wallet address.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cluster = cur.execute(
        "SELECT cluster_id, primary_ip FROM entity_clusters WHERE wallet_address = ?",
        (address,)
    ).fetchone()

    tx_rows = cur.execute('''
        SELECT txid, timestamp, src_ip, geo_country, inputs_json, outputs_json, total_input_btc
        FROM transactions
        WHERE inputs_json LIKE ? OR outputs_json LIKE ?
        ORDER BY timestamp ASC
    ''', (f"%{address}%", f"%{address}%")).fetchall()
    conn.close()

    received_total = 0.0
    sent_total = 0.0
    activity = []

    for tx in tx_rows:
        inputs = json.loads(tx["inputs_json"])
        outputs = json.loads(tx["outputs_json"])

        is_sender = any(i.get("address") == address for i in inputs)
        is_receiver = any(o.get("address") == address for o in outputs)

        amt_sent = sum(i.get("amount", 0.0) for i in inputs if i.get("address") == address)
        amt_received = sum(o.get("amount", 0.0) for o in outputs if o.get("address") == address)

        sent_total += amt_sent
        received_total += amt_received

        activity.append({
            "txid": tx["txid"],
            "timestamp": tx["timestamp"],
            "role": "SENDER" if is_sender else "RECEIVER",
            "net_flow": amt_received - amt_sent,
            "ip_origin": tx["src_ip"],
            "country": tx["geo_country"]
        })

    return {
        "wallet_address": address,
        "cluster_id": cluster["cluster_id"] if cluster else "UNCLUSTERED",
        "primary_ip": cluster["primary_ip"] if cluster else "UNKNOWN",
        "total_received_btc": round(received_total, 8),
        "total_sent_btc": round(sent_total, 8),
        "current_balance_btc": round(received_total - sent_total, 8),
        "transactions_count": len(activity),
        "activity": activity
    }