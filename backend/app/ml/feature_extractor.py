import math
import numpy as np
from typing import Dict, Any, List, Tuple


class FeatureExtractor:
    """
    Extracts correlated dual-layer (network telemetry + blockchain graph) 
    forensic features for offline machine learning inference.
    """
    FEATURE_NAMES = [
        "total_input_btc",          # Aggregate input value
        "total_output_btc",         # Aggregate output value
        "num_inputs",               # In-degree / fan-in
        "num_outputs",              # Out-degree / fan-out
        "miner_fee",                # Absolute transaction fee
        "fee_ratio",                # Fee divided by total transacted value
        "output_value_entropy",     # Uniformity/dispersion across outputs
        "max_output_asymmetry",     # Asymmetry ratio between highest & lowest outputs
        "is_non_standard_port",     # Flag: non-standard Bitcoin P2P port
        "is_high_risk_asn",         # Flag: high-risk Autonomous System Number
        "is_high_risk_country",     # Flag: high-risk jurisdiction
        "script_type_code",         # Encoded output script type
        "hour_of_broadcast"         # Time of day (UTC hour 0-23)
    ]

    HIGH_RISK_ASNS = {"AS12389", "AS58224", "AS49981", "AS205100", "AS51852"}
    HIGH_RISK_COUNTRIES = {"RU", "IR", "KP", "SC", "VG"}
    STANDARD_PORTS = {8333, 18333, 80, 443}

    SCRIPT_ENCODING = {
        "p2pkh": 1.0,
        "p2sh": 2.0,
        "p2wpkh": 3.0,
        "p2wsh": 4.0,
        "p2tr": 5.0
    }

    def _calculate_entropy(self, amounts: List[float]) -> float:
        """Calculates Shannon entropy of output amount distributions."""
        valid_amts = [a for a in amounts if a > 0]
        if not valid_amts:
            return 0.0
        total = sum(valid_amts)
        probabilities = [a / total for a in valid_amts]
        return float(-sum(p * math.log2(p) for p in probabilities if p > 0))

    def extract_from_record(self, tx: Dict[str, Any]) -> Tuple[np.ndarray, List[str]]:
        """
        Transforms a raw or database transaction record into a standardized 1D feature vector.
        """
        inputs = tx.get("inputs", [])
        outputs = tx.get("outputs", [])

        in_amts = [float(i.get("amount", 0.0)) for i in inputs]
        out_amts = [float(o.get("amount", 0.0)) for o in outputs]

        total_in = float(tx.get("total_input_btc") or sum(in_amts) or 0.0001)
        total_out = float(tx.get("total_output_btc") or sum(out_amts) or 0.0001)
        fee = float(tx.get("fee") or 0.0001)
        fee_ratio = fee / total_in

        # Output dispersion & asymmetry
        entropy = self._calculate_entropy(out_amts)
        asymmetry = 1.0
        if len(out_amts) >= 2:
            min_o, max_o = min(out_amts), max(out_amts)
            if min_o > 0:
                asymmetry = max_o / min_o

        # Network layer features
        dst_port = int(tx.get("dst_port") or 8333)
        non_std_port = 1.0 if dst_port not in self.STANDARD_PORTS else 0.0

        asn_str = str(tx.get("geo_asn") or "")
        is_hr_asn = 1.0 if any(asn in asn_str for asn in self.HIGH_RISK_ASNS) else 0.0

        country = str(tx.get("geo_country") or "").upper()
        is_hr_country = 1.0 if country in self.HIGH_RISK_COUNTRIES else 0.0

        script_type = str(tx.get("script_type") or "p2wpkh").lower()
        script_code = self.SCRIPT_ENCODING.get(script_type, 0.0)

        timestamp = int(tx.get("timestamp") or 0)
        hour = float((timestamp // 3600) % 24)

        features = [
            total_in,
            total_out,
            float(len(inputs)),
            float(len(outputs)),
            fee,
            float(round(fee_ratio, 6)),
            float(round(entropy, 4)),
            float(round(min(asymmetry, 100.0), 4)),
            non_std_port,
            is_hr_asn,
            is_hr_country,
            script_code,
            hour
        ]

        return np.array(features, dtype=np.float32), self.FEATURE_NAMES

    def extract_batch(self, tx_list: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[str]]:
        """Extracts a 2D feature matrix for batch inference."""
        vectors = []
        for tx in tx_list:
            v, _ = self.extract_from_record(tx)
            vectors.append(v)
        return np.vstack(vectors) if vectors else np.empty((0, len(self.FEATURE_NAMES))), self.FEATURE_NAMES