import json
import numpy as np
from typing import Dict, Any, List
from sklearn.ensemble import IsolationForest
from app.db.sqlite_client import get_db_connection


class TransactionAnomalyDetector:
    """
    Unsupervised Isolation Forest anomaly detection flagging unusual transaction flows.
    Provides feature-level Z-score deviance for investigative explainability.
    """
    def __init__(self, contamination: float = 0.08):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.feature_names = [
            "total_input_btc",
            "output_count",
            "input_count",
            "fee_ratio",
            "is_high_risk_asn",
            "non_standard_port"
        ]
        self.high_risk_asns = {"AS12389", "AS58224", "AS49981"}
        self.standard_ports = {8333, 18333, 80, 443}

    def _extract_features(self, rows: List[Any]) -> np.ndarray:
        feature_matrix = []
        for r in rows:
            inputs = json.loads(r["inputs_json"])
            outputs = json.loads(r["outputs_json"])
            total_btc = r["total_input_btc"] or 0.0001
            fee = r["fee"] or 0.0001

            fee_ratio = fee / total_btc
            is_hr_asn = 1.0 if any(asn in (r["geo_asn"] or "") for asn in self.high_risk_asns) else 0.0
            non_std_port = 1.0 if r["dst_port"] not in self.standard_ports else 0.0

            feature_matrix.append([
                float(total_btc),
                float(len(outputs)),
                float(len(inputs)),
                float(fee_ratio),
                is_hr_asn,
                non_std_port
            ])
        return np.array(feature_matrix)

    def run_anomaly_detection(self) -> Dict[str, Dict[str, Any]]:
        conn = get_db_connection()
        cur = conn.cursor()
        rows = cur.execute("SELECT * FROM transactions").fetchall()

        if len(rows) < 5:
            conn.close()
            return {r["txid"]: {"anomaly_score": 0.1, "primary_deviance": "insufficient_data", "z_score": 0.0} for r in rows}

        X = self._extract_features(rows)
        self.model.fit(X)

        # Raw scores: lower = more anomalous; invert to make higher = more anomalous
        raw_scores = -self.model.score_samples(X)
        min_s, max_s = raw_scores.min(), raw_scores.max()
        norm_scores = (raw_scores - min_s) / (max_s - min_s + 1e-6)

        # Compute feature distribution statistics for explainability
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0) + 1e-6

        results = {}
        for idx, row in enumerate(rows):
            score = norm_scores[idx]
            sample = X[idx]
            z_scores = np.abs((sample - means) / stds)
            dominant_idx = int(np.argmax(z_scores))

            results[row["txid"]] = {
                "anomaly_score": float(round(score, 4)),
                "is_outlier": bool(score > 0.70),
                "primary_deviance": self.feature_names[dominant_idx],
                "z_score": float(round(z_scores[dominant_idx], 2)),
                "feature_snapshot": {
                    self.feature_names[i]: float(round(sample[i], 4)) for i in range(len(self.feature_names))
                }
            }

        conn.close()
        return results