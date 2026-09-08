from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import json

from app.db.sqlite_client import get_db_connection
from app.engine.alert_generator import generate_investigative_alerts
from app.reports.generator import ReportGenerator

router = APIRouter()


@router.get("/ranked")
def list_ranked_alerts(limit: int = Query(50, ge=1, le=500), focus_area: Optional[str] = None):
    """
    Returns prioritized investigative alerts sorted by composite risk score with explanation metadata.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    query = "SELECT * FROM alerts"
    params = []

    if focus_area:
        query += " WHERE primary_focus_area = ?"
        params.append(focus_area)

    query += " ORDER BY risk_score DESC LIMIT ?"
    params.append(limit)

    rows = cur.execute(query, params).fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "alert_id": r["alert_id"],
            "target_type": r["target_type"],
            "target_identifier": r["target_identifier"],
            "risk_score": round(r["risk_score"], 4),
            "confidence": round(r["confidence"], 4),
            "primary_focus_area": r["primary_focus_area"],
            "flags": {
                "peeling_chain": bool(r["peeling_chain_flag"]),
                "mixer_coinjoin": bool(r["mixer_flag"]),
                "anomaly_score": round(r["anomaly_score"], 4),
                "taint_score": round(r["taint_score"], 4)
            },
            "evidence": json.loads(r["explanation_json"]),
            "created_at": r["created_at"]
        })

    return {"total": len(results), "alerts": results}


@router.get("/{alert_id}")
def get_alert_detail(alert_id: str):
    """Fetches full granular forensic evidence for an alert."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Alert identifier not found.")

    return {
        "alert_id": row["alert_id"],
        "target_type": row["target_type"],
        "target_identifier": row["target_identifier"],
        "risk_score": row["risk_score"],
        "confidence": row["confidence"],
        "primary_focus_area": row["primary_focus_area"],
        "evidence": json.loads(row["explanation_json"]),
        "created_at": row["created_at"]
    }


@router.post("/recompute")
def trigger_alert_generation():
    """Forces execution of AI/ML anomaly, demixing, taint diffusion, and alert aggregation."""
    alerts = generate_investigative_alerts()
    return {"status": "success", "generated_alert_count": len(alerts)}


@router.get("/{txid}/report/html")
def generate_html_report(txid: str):
    """Generates an offline Suspicious Transaction Report (STR) HTML dossier."""
    generator = ReportGenerator()
    report_info = generator.generate_html_str(txid)
    if not report_info:
        raise HTTPException(status_code=404, detail="Transaction not found to generate report.")
    return report_info


@router.get("/{txid}/report/markdown")
def generate_markdown_report(txid: str):
    """Outputs a text/Markdown summary of evidence suitable for terminal output."""
    generator = ReportGenerator()
    md = generator.generate_markdown_summary(txid)
    if not md:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return {"txid": txid, "report_markdown": md}