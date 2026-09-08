import uuid
import time
import json
from typing import Dict, Any, List
from app.db.sqlite_client import get_db_connection
from app.engine.demixing import LaunderingDetector
from app.engine.heuristics import TransactionHeuristics
from app.engine.anomaly_detector import TransactionAnomalyDetector
from app.engine.scoring import RiskPropagationEngine
from app.ml.inference import MLInferenceEngine
from app.core.config import settings


def generate_investigative_alerts() -> List[Dict[str, Any]]:
    """
    Executes all detection engines and aggregates findings into prioritized,
    explainable alerts for BOTH transactions and suspect wallets.
    """
    detector = LaunderingDetector()
    heuristics = TransactionHeuristics()
    anomaly_detector = TransactionAnomalyDetector()
    risk_engine = RiskPropagationEngine()
    ml_engine = MLInferenceEngine()

    # 1. Run Analytical Models
    anomaly_map = anomaly_detector.run_anomaly_detection()
    taint_map = risk_engine.propagate_taint()

    conn = get_db_connection()
    cur = conn.cursor()
    tx_rows = cur.execute("SELECT * FROM transactions").fetchall()
    cluster_rows = cur.execute("SELECT wallet_address, cluster_id FROM entity_clusters").fetchall()
    cluster_map = {c["wallet_address"]: c["cluster_id"] for c in cluster_rows}

    all_transactions = []
    for row in tx_rows:
        all_transactions.append({"txid": row["txid"], "timestamp": row["timestamp"],
                                 "inputs": json.loads(row["inputs_json"]), "outputs": json.loads(row["outputs_json"])})
    peeling_chains = detector.detect_peeling_chains(all_transactions)
    cur.execute("DELETE FROM alerts")
    generated_alerts = []

    # -------------------------------------------------------------
    # STAGE A: Transaction Alerts (Supervised ML + Anomaly + Demix)
    # -------------------------------------------------------------
    for r in tx_rows:
        txid = r["txid"]
        inputs = json.loads(r["inputs_json"])
        outputs = json.loads(r["outputs_json"])
        country = r["geo_country"] or "UNKNOWN"
        asn = r["geo_asn"] or "UNKNOWN"

        # Demixing
        is_peeling_transaction, peel_conf, peel_meta = detector.detect_peeling_chain(inputs, outputs)
        chain_meta = peeling_chains.get(txid)
        is_peeling = chain_meta is not None
        is_mixer, mix_conf, mix_meta = detector.detect_coinjoin_mixer(inputs, outputs)

        # Rule Heuristics
        tx_dict = {
            "txid": txid,
            "inputs": inputs,
            "outputs": outputs,
            "fee": r["fee"],
            "total_input_btc": r["total_input_btc"],
            "total_output_btc": r["total_output_btc"],
            "src_port": r["src_port"],
            "dst_port": r["dst_port"],
            "geo_asn": asn,
            "geo_country": country,
            "script_type": r["script_type"],
            "timestamp": r["timestamp"]
        }
        heuristic_res = heuristics.evaluate(tx_dict)
        h_score = heuristic_res["heuristic_score"]

        # Supervised ML Classification (app/ml/inference.py)
        ml_res = ml_engine.predict(tx_dict)
        ml_prob = ml_res["illicit_probability"]

        # Unsupervised Outlier Anomaly Score
        anom_res = anomaly_map.get(txid, {"anomaly_score": None, "status": "unavailable"})
        anom_score = anom_res.get("anomaly_score")
        taint_score = taint_map.get(txid, 0.0)

        # Geo/ASN Risk
        geo_risk = 0.85 if country in ("RU", "IR", "KP") else 0.0
        demix_conf = float(chain_meta["confidence"]) if is_peeling else (peel_conf if is_peeling_transaction else (mix_conf if is_mixer else 0.0))

        # Unified Composite Risk
        component_scores = {"ml": ml_prob, "taint": taint_score, "anomaly": anom_score,
                            "demixing": demix_conf, "heuristics": h_score, "network": geo_risk}
        available_weights = sum(settings.RISK_WEIGHTS[name] for name, value in component_scores.items() if value is not None)
        composite_risk = sum(settings.RISK_WEIGHTS[name] * value for name, value in component_scores.items() if value is not None) / available_weights

        confidence = max(demix_conf, ml_prob, anom_score or 0.0, taint_score)

        if composite_risk >= settings.COMPOSITE_ALERT_THRESHOLD or is_peeling_transaction or is_mixer or ml_prob >= 0.65:
            if is_peeling:
                focus_area = "Peeling-Chain Detection"
            elif is_peeling_transaction:
                focus_area = "Peeling Transaction Indicator"
            elif is_mixer:
                focus_area = "Mixing / CoinJoin Detection"
            elif taint_score >= 0.40:
                focus_area = "Illicit Taint Propagation"
            elif ml_prob >= 0.60:
                focus_area = "Supervised ML Classification"
            else:
                focus_area = "Statistical Anomaly Detection"

            explanation_payload = {
                "alert_summary": f"Transaction flagged under {focus_area} with composite risk {round(composite_risk, 3)}",
                "risk_attribution": {
                    "ml_classifier_probability": round(ml_prob, 4),
                    "risk_components": {key: round(value, 4) if value is not None else None for key, value in component_scores.items()},
                    "risk_weights": settings.RISK_WEIGHTS,
                    "ml_contributing_features": ml_res.get("top_contributing_features", []),
                    "unsupervised_anomaly_score": round(anom_score, 4),
                    "primary_anomalous_feature": anom_res.get("primary_deviance"),
                    "seed_taint_score": round(taint_score, 4),
                    "heuristic_triggers": heuristic_res["flags"],
                    "peeling_chain_evidence": chain_meta,
                    "peeling_transaction_evidence": peel_meta if is_peeling_transaction else None,
                    "mixer_evidence": mix_meta if is_mixer else None,
                    "network_origin": f"{r['src_ip']} [{country} - {asn}]"
                }
            }

            alert_id = f"ALT_TX_{uuid.uuid4().hex[:8].upper()}"
            cur.execute('''
                INSERT INTO alerts (
                    alert_id, target_type, target_identifier, risk_score, confidence,
                    primary_focus_area, anomaly_score, taint_score, peeling_chain_flag,
                    mixer_flag, explanation_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert_id, "txid", txid, float(round(composite_risk, 4)), float(round(confidence, 4)),
                focus_area, anom_score, taint_score,
                1 if is_peeling else 0, 1 if is_mixer else 0,
                json.dumps(explanation_payload), int(time.time())
            ))
            generated_alerts.append({"alert_id": alert_id, "target": txid, "risk": composite_risk})

    # -------------------------------------------------------------
    # STAGE B: Wallet-Level Alerts (Tainted Wallets & Peel Cashouts)
    # -------------------------------------------------------------
    wallet_scores: Dict[str, float] = {}
    for node, score in taint_map.items():
        if not node.startswith("tx_") and score >= 0.35:
            wallet_scores[node] = score

    for wallet, t_score in wallet_scores.items():
        w_alert_id = f"ALT_W_{uuid.uuid4().hex[:8].upper()}"
        w_cluster = cluster_map.get(wallet, "UNCLUSTERED")

        w_explanation = {
            "alert_summary": f"Wallet address {wallet} flagged with taint index {round(t_score, 3)}",
            "risk_attribution": {
                "wallet_address": wallet,
                "cluster_id": w_cluster,
                "propagated_taint_score": round(t_score, 4),
                "association": "Downstream recipient of designated illicit seed flow"
            }
        }

        cur.execute('''
            INSERT INTO alerts (
                alert_id, target_type, target_identifier, risk_score, confidence,
                primary_focus_area, anomaly_score, taint_score, peeling_chain_flag,
                mixer_flag, explanation_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            w_alert_id, "wallet", wallet, float(round(t_score, 4)), float(round(t_score, 4)),
            "Wallet Risk Scoring / Taint", 0.0, float(round(t_score, 4)),
            0, 0, json.dumps(w_explanation), int(time.time())
        ))
        generated_alerts.append({"alert_id": w_alert_id, "target": wallet, "risk": t_score})

    conn.commit()
    conn.close()
    return generated_alerts
