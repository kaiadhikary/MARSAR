from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, Optional
import json

from app.db.sqlite_client import get_db_connection
from app.engine.alert_generator import generate_investigative_alerts
from app.reports.generator import ReportGenerator

router = APIRouter()

_CATEGORY_FILTERS = {
    "ml": (
        "primary_focus_area LIKE '%ML%' OR primary_focus_area LIKE '%Classif%' "
        "OR COALESCE(CAST(json_extract(explanation_json, '$.risk_attribution.ml_classifier_probability') AS REAL), 0) >= 0.5 "
        "OR COALESCE(CAST(json_extract(explanation_json, '$.risk_attribution.risk_components.ml') AS REAL), 0) >= 0.5"
    ),
    "taint": (
        "COALESCE(taint_score, 0) >= 0.35 "
        "OR primary_focus_area LIKE '%Taint%' "
        "OR COALESCE(CAST(json_extract(explanation_json, '$.risk_attribution.seed_taint_score') AS REAL), 0) >= 0.35 "
        "OR COALESCE(CAST(json_extract(explanation_json, '$.risk_attribution.propagated_taint_score') AS REAL), 0) >= 0.35"
    ),
    "anomaly": (
        "COALESCE(anomaly_score, 0) >= 0.35 "
        "OR primary_focus_area LIKE '%Anomaly%' "
        "OR COALESCE(CAST(json_extract(explanation_json, '$.risk_attribution.unsupervised_anomaly_score') AS REAL), 0) >= 0.35"
    ),
    "peeling": (
        "peeling_chain_flag = 1 "
        "OR primary_focus_area LIKE '%Peel%' "
        "OR (json_extract(explanation_json, '$.risk_attribution.peeling_chain_evidence') IS NOT NULL "
        "AND json_type(json_extract(explanation_json, '$.risk_attribution.peeling_chain_evidence')) != 'null') "
        "OR (json_extract(explanation_json, '$.risk_attribution.peeling_transaction_evidence') IS NOT NULL "
        "AND json_type(json_extract(explanation_json, '$.risk_attribution.peeling_transaction_evidence')) != 'null')"
    ),
    "coinjoin": (
        "mixer_flag = 1 "
        "OR primary_focus_area LIKE '%CoinJoin%' "
        "OR primary_focus_area LIKE '%Mixing%' "
        "OR (json_extract(explanation_json, '$.risk_attribution.mixer_evidence') IS NOT NULL "
        "AND json_type(json_extract(explanation_json, '$.risk_attribution.mixer_evidence')) != 'null')"
    ),
    "network": (
        "COALESCE(CAST(json_extract(explanation_json, '$.risk_attribution.risk_components.network') AS REAL), 0) > 0 "
        "OR primary_focus_area LIKE '%Network%' "
        "OR primary_focus_area LIKE '%Geo%'"
    ),
}


def _compact_alert(row) -> Dict[str, Any]:
    explanation = json.loads(row["explanation_json"] or "{}")
    attr = explanation.get("risk_attribution") or {}
    components = attr.get("risk_components") or {}
    ml_score = components.get("ml")
    if ml_score is None:
        ml_score = attr.get("ml_classifier_probability")
    network_score = components.get("network")
    return {
        "alert_id": row["alert_id"],
        "target_type": row["target_type"],
        "target_identifier": row["target_identifier"],
        "risk_score": round(row["risk_score"], 4),
        "confidence": round(row["confidence"], 4),
        "primary_focus_area": row["primary_focus_area"],
        "flags": {
            "peeling_chain": bool(row["peeling_chain_flag"]),
            "mixer_coinjoin": bool(row["mixer_flag"]),
            "anomaly_score": round(row["anomaly_score"] or 0.0, 4),
            "taint_score": round(row["taint_score"] or 0.0, 4),
            "ml_score": round(float(ml_score), 4) if ml_score is not None else None,
            "network_score": round(float(network_score), 4) if network_score is not None else None,
        },
        "evidence": {
            "alert_summary": explanation.get("alert_summary"),
            "risk_attribution": {
                "ml_classifier_probability": attr.get("ml_classifier_probability"),
                "risk_components": components,
                "seed_taint_score": attr.get("seed_taint_score"),
                "propagated_taint_score": attr.get("propagated_taint_score"),
                "unsupervised_anomaly_score": attr.get("unsupervised_anomaly_score"),
                "peeling_chain_evidence": attr.get("peeling_chain_evidence"),
                "peeling_transaction_evidence": attr.get("peeling_transaction_evidence"),
                "mixer_evidence": attr.get("mixer_evidence"),
                "network_origin": attr.get("network_origin"),
            },
        },
        "created_at": row["created_at"],
    }


def _where_clause(focus_area: Optional[str], category: Optional[str]):
    clauses = []
    params = []
    if focus_area:
        clauses.append("primary_focus_area = ?")
        params.append(focus_area)
    if category:
        normalized = category.strip().lower()
        category_sql = _CATEGORY_FILTERS.get(normalized)
        if not category_sql:
            raise HTTPException(status_code=400, detail=f"Unknown alert category '{category}'.")
        clauses.append(f"({category_sql})")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


@router.get("/ranked")
def list_ranked_alerts(
    limit: int = Query(50, ge=1, le=10_000),
    focus_area: Optional[str] = None,
    category: Optional[str] = None,
):
    """
    Returns prioritized investigative alerts sorted by composite risk score with explanation metadata.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    where, params = _where_clause(focus_area, category)
    rows = cur.execute(
        f"SELECT * FROM alerts{where} ORDER BY risk_score DESC LIMIT ?",
        [*params, limit],
    ).fetchall()
    conn.close()
    results = [_compact_alert(r) for r in rows]
    return {"total": len(results), "alerts": results}


@router.get("/summary")
def alert_filter_summary():
    """Counts used by the Alerts toolbar so every engine chip has a live total."""
    conn = get_db_connection()
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    counts = {"all": int(total)}
    for name, sql in _CATEGORY_FILTERS.items():
        counts[name] = int(cur.execute(f"SELECT COUNT(*) FROM alerts WHERE ({sql})").fetchone()[0])
    conn.close()
    return {"total": int(total), "counts": counts}


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