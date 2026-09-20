import json
import time
from typing import Dict, Any, Optional
from app.db.sqlite_client import get_db_connection
from app.reports.hashing import ForensicHasher


class EvidenceCollector:
    """Build a sealed forensic dossier for a flagged transaction."""

    def collect_tx_dossier(self, txid: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cur = conn.cursor()

        tx_row = cur.execute("SELECT * FROM transactions WHERE txid = ?", (txid,)).fetchone()
        if not tx_row:
            conn.close()
            return None

        alert_row = cur.execute(
            "SELECT * FROM alerts WHERE target_identifier = ? ORDER BY risk_score DESC LIMIT 1",
            (txid,)
        ).fetchone()

        inputs = json.loads(tx_row["inputs_json"])
        outputs = json.loads(tx_row["outputs_json"])

        input_addrs = [i.get("address") for i in inputs if i.get("address")]
        cluster_map = {}
        for addr in input_addrs:
            c_row = cur.execute(
                "SELECT cluster_id, primary_ip, confidence FROM entity_clusters WHERE wallet_address = ?",
                (addr,)
            ).fetchone()
            if c_row:
                cluster_map[addr] = {
                    "cluster_id": c_row["cluster_id"],
                    "primary_ip": c_row["primary_ip"],
                    "cluster_confidence": c_row["confidence"]
                }
            else:
                cluster_map[addr] = {"cluster_id": "UNCLUSTERED", "primary_ip": "UNKNOWN", "cluster_confidence": 0.0}

        conn.close()

        explanation = json.loads(alert_row["explanation_json"]) if alert_row else {}

        dossier = {
            "metadata": {
                "dossier_id": f"DOS_{txid[:12].upper()}",
                "generated_at": int(time.time()),
                "investigation_target": txid,
                "target_type": "BITCOIN_TRANSACTION"
            },
            "blockchain_layer": {
                "txid": tx_row["txid"],
                "timestamp": tx_row["timestamp"],
                "fee_btc": tx_row["fee"],
                "script_type": tx_row["script_type"],
                "total_input_btc": tx_row["total_input_btc"],
                "total_output_btc": tx_row["total_output_btc"],
                "inputs": inputs,
                "outputs": outputs
            },
            "network_layer": {
                "src_ip": tx_row["src_ip"],
                "dst_ip": tx_row["dst_ip"],
                "src_port": tx_row["src_port"],
                "dst_port": tx_row["dst_port"],
                "geo_country": tx_row["geo_country"],
                "geo_asn": tx_row["geo_asn"]
            },
            "entity_intelligence": {
                "input_clusters": cluster_map
            },
            "forensic_scoring": {
                "composite_risk_score": alert_row["risk_score"] if alert_row else 0.0,
                "model_confidence": alert_row["confidence"] if alert_row else 0.0,
                "primary_focus_area": alert_row["primary_focus_area"] if alert_row else "NONE",
                "peeling_chain_flag": bool(alert_row["peeling_chain_flag"]) if alert_row else False,
                "mixer_coinjoin_flag": bool(alert_row["mixer_flag"]) if alert_row else False,
                "taint_score": alert_row["taint_score"] if alert_row else 0.0,
                "anomaly_score": alert_row["anomaly_score"] if alert_row else 0.0,
                "explainability": explanation
            }
        }

        dossier["chain_of_custody_hash"] = ForensicHasher.hash_payload(dossier)
        return dossier