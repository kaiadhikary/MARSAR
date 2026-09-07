from typing import Dict, Any, Tuple, List


class LaunderingDetector:
    """
    Identifies laundering transaction topologies including:
    1. Peeling chains (rapid peel-off cashouts with large change carryover).
    2. CoinJoin mixing (uniform equal denominations across multiple parties).
    """

    def detect_peeling_chain(
        self, 
        inputs: List[Dict[str, Any]], 
        outputs: List[Dict[str, Any]]
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        A peeling chain transaction is characterized by:
        - Exactly 1 or 2 inputs.
        - Exactly 2 outputs: 1 small payment/cashout and 1 large change output.
        - High value asymmetry ratio >= 4.0.
        """
        if len(inputs) <= 2 and len(outputs) == 2:
            amt0 = float(outputs[0].get("amount", 0.0))
            amt1 = float(outputs[1].get("amount", 0.0))

            if amt0 > 0 and amt1 > 0:
                larger = max(amt0, amt1)
                smaller = min(amt0, amt1)
                ratio = larger / smaller

                if ratio >= 4.0:
                    peeled_addr = outputs[0]["address"] if amt0 == smaller else outputs[1]["address"]
                    change_addr = outputs[0]["address"] if amt0 == larger else outputs[1]["address"]
                    confidence = min(0.96, 0.65 + (ratio / 30.0))
                    
                    return True, confidence, {
                        "pattern": "PEELING_CHAIN",
                        "peeled_amount": smaller,
                        "change_amount": larger,
                        "peeled_address": peeled_addr,
                        "change_address": change_addr,
                        "asymmetry_ratio": round(ratio, 2)
                    }
        return False, 0.0, {}

    def detect_coinjoin_mixer(
        self, 
        inputs: List[Dict[str, Any]], 
        outputs: List[Dict[str, Any]]
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        CoinJoin mixer transactions exhibit:
        - >= 3 inputs from distinct parties.
        - >= 3 outputs with repeated, equal BTC denominations (e.g. 0.05, 0.1 BTC).
        """
        if len(inputs) >= 3 and len(outputs) >= 3:
            out_amts = [round(float(o.get("amount", 0.0)), 6) for o in outputs]
            counts: Dict[float, int] = {}
            for amt in out_amts:
                if amt > 0:
                    counts[amt] = counts.get(amt, 0) + 1

            # Identify equal denominations
            equal_groups = {amt: cnt for amt, cnt in counts.items() if cnt >= 2}

            if equal_groups:
                identical_output_count = sum(equal_groups.values())
                match_ratio = identical_output_count / len(outputs)

                if match_ratio >= 0.5:
                    confidence = min(0.98, 0.60 + (match_ratio * 0.35))
                    return True, confidence, {
                        "pattern": "COINJOIN_MIXER",
                        "uniform_denominations": equal_groups,
                        "total_outputs": len(outputs),
                        "mixing_participants": len(inputs),
                        "uniformity_ratio": round(match_ratio, 2)
                    }
        return False, 0.0, {}