import math
from typing import Dict, Any, List, Tuple


class TransactionHeuristics:
    """
    Evaluates rule-based timing, structural, and behavioral markers
    indicative of extortion payoffs, ransom structuring, or evasion.
    """
    HIGH_RISK_ASNS = {"AS12389", "AS58224", "AS49981"}
    STANDARD_PORTS = {8333, 18333, 80, 443}

    @staticmethod
    def check_round_amounts(outputs: List[Dict[str, Any]]) -> Tuple[bool, float]:
        """Flags transactions paying exact round Bitcoin sums common in ransom demands."""
        for out in outputs:
            amt = float(out.get("amount") or 0.0)
            if amt > 0.0:
                if amt in (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0) or amt.is_integer():
                    return True, 0.75
        return False, 0.0

    @staticmethod
    def check_fee_urgency(fee: float, total_btc: float) -> Tuple[bool, float]:
        """Flags high miner fee-to-principal ratios indicating urgent mempool confirmation."""
        fee = float(fee or 0.0)
        total_btc = float(total_btc or 0.0)
        if total_btc <= 0:
            return False, 0.0
        fee_ratio = fee / total_btc
        if fee_ratio > 0.02:
            return True, min(0.90, 0.4 + (fee_ratio * 10))
        return False, 0.0

    @staticmethod
    def check_network_anomalies(src_port: int, dst_port: int, asn: str) -> Tuple[bool, float]:
        """Flags suspicious routing via non-standard Bitcoin P2P ports or high-risk ASNs."""
        reasons = 0
        if dst_port not in TransactionHeuristics.STANDARD_PORTS:
            reasons += 1
        if any(h_asn in (asn or "") for h_asn in TransactionHeuristics.HIGH_RISK_ASNS):
            reasons += 2

        if reasons >= 2:
            return True, 0.80
        if reasons == 1:
            return True, 0.45
        return False, 0.0

    def evaluate(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        outputs = tx.get("outputs", [])
        fee = float(tx.get("fee") or 0.0001)
        total_btc = float(tx.get("total_input_btc") or 0.0001)
        src_port = int(tx.get("src_port") or 8333)
        dst_port = int(tx.get("dst_port") or 8333)
        asn = str(tx.get("geo_asn") or "")

        round_flag, round_conf = self.check_round_amounts(outputs)
        fee_flag, fee_conf = self.check_fee_urgency(fee, total_btc)
        net_flag, net_conf = self.check_network_anomalies(src_port, dst_port, asn)

        score = max(round_conf, fee_conf, net_conf)
        return {
            "heuristic_score": round(score, 3),
            "flags": {
                "round_value_demand": round_flag,
                "urgent_fee_structure": fee_flag,
                "network_telemetry_anomaly": net_flag
            }
        }