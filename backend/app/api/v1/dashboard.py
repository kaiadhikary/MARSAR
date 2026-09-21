"""Compatibility endpoints consumed by the bundled Next.js dashboard."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.db.sqlite_client import get_db_connection
from app.reports.generator import ReportGenerator
from app.ml.feature_extractor import FeatureExtractor

router = APIRouter()
public_router = APIRouter()


def _alert_rows(limit: int):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM alerts WHERE target_type = 'txid' ORDER BY risk_score DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows


def _transaction_view(row, alert=None):
    evidence = json.loads(alert["explanation_json"]) if alert else {}
    attribution = evidence.get("risk_attribution", {})
    components = attribution.get("risk_components", {})
    inputs = json.loads(row["inputs_json"])
    outputs = json.loads(row["outputs_json"])
    tx = {
        "inputs": inputs,
        "outputs": outputs,
        "total_input_btc": row["total_input_btc"],
        "total_output_btc": row["total_output_btc"],
        "fee": row["fee"],
        "dst_port": row["dst_port"],
        "geo_asn": row["geo_asn"],
        "geo_country": row["geo_country"],
        "script_type": row["script_type"],
        "timestamp": row["timestamp"],
    }
    vector, names = FeatureExtractor().extract_from_record(tx)
    score = float(alert["risk_score"]) if alert else None
    return {
        "txid": row["txid"],
        "cluster_id": None,
        "risk_score": round(score, 4) if score is not None else None,
        "risk_verdict": "HIGH_RISK" if score is not None and score >= 0.70 else "SUSPICIOUS" if score is not None and score >= 0.35 else "UNSCORED",
        "ml_probability": attribution.get("ml_classifier_probability"),
        "taint_score": attribution.get("seed_taint_score"),
        "typology_score": components.get("demixing"),
        "mixer_penalty_score": components.get("demixing"),
        "is_coinjoin": bool(alert["mixer_flag"]) if alert else None,
        "blacklist_hit": None,
        "typology_flags": alert["primary_focus_area"] if alert else None,
        "fee_rate": row["fee"],
        "fee": row["fee"],
        "shannon_entropy": float(vector[names.index("output_value_entropy")]),
        "created_at": row["timestamp"],
        "timestamp": row["timestamp"],
        "src_ip": row["src_ip"],
        "dst_ip": row["dst_ip"],
        "country": row["geo_country"],
        "asn": row["geo_asn"],
        "inputs": len(inputs),
        "outputs": len(outputs),
        "amount": float(row["total_input_btc"] or 0.0),
        "alert_id": alert["alert_id"] if alert else None,
    }


@router.get("/graph/expand/{address}")
def expand_address_graph(address: str, hops: int = Query(3, ge=1, le=5)):
    """Return a bounded address-centred graph in the dashboard's legacy shape."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM transactions WHERE inputs_json LIKE ? OR outputs_json LIKE ? ORDER BY timestamp DESC LIMIT 100",
        (f'%"address": "{address}"%', f'%"address": "{address}"%'),
    ).fetchall()
    cluster = conn.execute("SELECT cluster_id FROM entity_clusters WHERE wallet_address = ?", (address,)).fetchone()
    conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail="Address not found in local evidence store.")
    nodes, edges, known = [], [], set()
    def add_node(identifier, label, root=False):
        if identifier not in known:
            nodes.append({"id": identifier, "label": label, "is_root": root, "is_blacklisted": False, "blacklist_entity": None})
            known.add(identifier)
    add_node(address, f"W: {address[:12]}", True)
    for tx in rows:
        add_node(tx["txid"], f"TX: {tx['txid'][:12]}")
        inputs, outputs = json.loads(tx["inputs_json"]), json.loads(tx["outputs_json"])
        for item in inputs:
            wallet = item.get("address")
            if wallet:
                add_node(wallet, f"W: {wallet[:12]}", wallet == address)
                edges.append({"id": f"in:{wallet}:{tx['txid']}", "source": wallet, "target": tx["txid"]})
        for item in outputs:
            wallet = item.get("address")
            if wallet:
                add_node(wallet, f"W: {wallet[:12]}", wallet == address)
                edges.append({"id": f"out:{tx['txid']}:{wallet}", "source": tx["txid"], "target": wallet})
    cluster_data = None
    if cluster:
        conn = get_db_connection()
        member_rows = conn.execute("SELECT wallet_address FROM entity_clusters WHERE cluster_id = ?", (cluster["cluster_id"],)).fetchall()
        member_addresses = [item["wallet_address"] for item in member_rows]
        placeholders = ",".join("?" for _ in member_addresses)
        tx_rows = conn.execute(f"SELECT MIN(timestamp) AS first_seen, MAX(timestamp) AS last_seen FROM transactions WHERE inputs_json LIKE ? OR outputs_json LIKE ?", (f'%{address}%', f'%{address}%')).fetchone()
        risks = conn.execute(f"SELECT MAX(risk_score) AS score FROM alerts WHERE target_identifier IN ({placeholders})", member_addresses).fetchone() if member_addresses else None
        conn.close()
        cluster_data = {"cluster_id": cluster["cluster_id"], "root_address": address, "member_count": len(member_addresses),
                        "risk_score": float(risks["score"]) if risks and risks["score"] is not None else None,
                        "first_seen": tx_rows["first_seen"] if tx_rows and tx_rows["first_seen"] is not None else None,
                        "last_updated": tx_rows["last_seen"] if tx_rows and tx_rows["last_seen"] is not None else None}
    return {"status": "success", "address": address, "hops": hops, "cluster": cluster_data, "nodes": nodes, "edges": edges}


@public_router.get("/compliance/transactions")
def reportable_transactions(limit: int = Query(50, ge=1, le=500)):
    conn = get_db_connection()
    txs = conn.execute("SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    alerts = {row["target_identifier"]: row for row in _alert_rows(limit)}
    conn.close()
    recent = [_transaction_view(row, alerts.get(row["txid"])) for row in txs]
    flagged = [_flagged_view(row) for row in alerts.values()]
    suspicious = [item for item in recent if item["risk_score"] is not None and item["risk_score"] >= 0.35]
    return {"recent": recent, "suspicious": suspicious, "flagged": flagged}


def _flagged_view(alert):
    score = float(alert["risk_score"])
    return {"txid": alert["target_identifier"], "risk_score": round(score, 4),
            "risk_verdict": "HIGH_RISK" if score >= 0.70 else "SUSPICIOUS",
            "flags": alert["primary_focus_area"], "blacklist_hit": None,
            "is_coinjoin": int(alert["mixer_flag"]), "cluster_id": None,
            "flagged_at": alert["created_at"]}


@public_router.get("/compliance/flagged")
def flagged_transactions(limit: int = Query(100, ge=1, le=500)):
    return {"flagged": [_flagged_view(row) for row in _alert_rows(limit)]}


class ExportRequest(BaseModel):
    txid: str
    case_id: Optional[str] = None
    investigator_note: Optional[str] = None


@public_router.post("/export-str")
def export_str_report(request: ExportRequest):
    """Generate and download an offline HTML dossier with integrity headers."""
    report = ReportGenerator().generate_html_str(request.txid.strip())
    if not report:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    conn = get_db_connection()
    alert = conn.execute("SELECT risk_score FROM alerts WHERE target_identifier = ? ORDER BY risk_score DESC LIMIT 1", (request.txid.strip(),)).fetchone()
    conn.close()
    score = float(alert["risk_score"]) if alert else None
    verdict = "HIGH_RISK" if score is not None and score >= 0.70 else "SUSPICIOUS" if score is not None and score >= 0.35 else "UNSCORED"
    return FileResponse(Path(report["report_path"]), media_type="text/html", filename=report["filename"], headers={
        "X-TXID": request.txid.strip(), "X-Risk-Score": str(round(score, 4)) if score is not None else "UNKNOWN", "X-Verdict": verdict,
        "X-Evidence-SHA256": report["chain_of_custody_hash"], "X-Generated-At": str(int(time.time())),
    })


@public_router.post("/compliance/export-str")
def export_str_report_alias(request: ExportRequest):
    """Alias for POST /export-str."""
    return export_str_report(request)
