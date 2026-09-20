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
                        "pattern": "PEELING_TRANSACTION",
                        "assessment": "Single asymmetric transaction; a linked sequence is required for a peeling-chain finding.",
                        "peeled_amount": smaller,
                        "change_amount": larger,
                        "peeled_address": peeled_addr,
                        "change_address": change_addr,
                        "asymmetry_ratio": round(ratio, 2)
                    }
        return False, 0.0, {}

    def detect_peeling_chains(self, transactions: List[Dict[str, Any]], min_chain_length: int = 3) -> Dict[str, Dict[str, Any]]:
        """Find linked sequences of asymmetric change outputs across transactions.

        A chain only exists when the large change address from one candidate is
        spent as an input by the next candidate.  The return value is keyed by
        every TXID in a confirmed chain so alert generation can attach the same
        transaction-specific evidence wherever the chain appears.
        """
        candidates: Dict[str, Dict[str, Any]] = {}
        spenders: Dict[str, List[str]] = {}
        for tx in transactions:
            txid = tx.get("txid")
            if not txid:
                continue
            matched, confidence, evidence = self.detect_peeling_chain(tx.get("inputs", []), tx.get("outputs", []))
            if matched:
                candidates[txid] = {"confidence": confidence, **evidence, "timestamp": int(tx.get("timestamp") or 0)}
            for item in tx.get("inputs", []):
                address = item.get("address")
                if address:
                    spenders.setdefault(address, []).append(txid)
        next_tx: Dict[str, str] = {}
        for txid, evidence in candidates.items():
            descendants = [candidate for candidate in spenders.get(evidence["change_address"], []) if candidate in candidates and candidate != txid]
            if descendants:
                next_tx[txid] = min(descendants, key=lambda candidate: candidates[candidate]["timestamp"])
        confirmed: Dict[str, Dict[str, Any]] = {}
        starts = [txid for txid in candidates if txid not in set(next_tx.values())]
        for start in starts:
            chain, seen = [], set()
            current = start
            while current and current not in seen:
                seen.add(current)
                chain.append(current)
                current = next_tx.get(current)
            if len(chain) < min_chain_length:
                continue
            items = [candidates[txid] for txid in chain]
            ratios = [item["asymmetry_ratio"] for item in items]
            values = [item["change_amount"] for item in items]
            evidence = {
                "pattern": "PEELING_CHAIN", "chain_length": len(chain), "txids": chain,
                "addresses": [item["change_address"] for item in items],
                "amounts": values, "timestamps": [item["timestamp"] for item in items],
                "evidence": {"repeated_change_address_flow": True,
                             "asymmetry_consistency": round(min(ratios) / max(ratios), 4) if max(ratios) else 0.0,
                             "value_decay": round(1.0 - (values[-1] / values[0]), 4) if values and values[0] else 0.0},
                "confidence": round(sum(item["confidence"] for item in items) / len(items), 4),
            }
            for txid in chain:
                confirmed[txid] = evidence
        return confirmed

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

            equal_groups = {amt: cnt for amt, cnt in counts.items() if cnt >= 2}

            if equal_groups:
                identical_output_count = sum(equal_groups.values())
                match_ratio = identical_output_count / len(outputs)

                if match_ratio >= 0.5:
                    confidence = min(0.98, 0.60 + (match_ratio * 0.35))
                    return True, confidence, {
                        "pattern": "COINJOIN_LIKE_PATTERN",
                        "assessment": "Heuristic lead only; equal denominations do not confirm a mixer service.",
                        "uniform_denominations": equal_groups,
                        "total_outputs": len(outputs),
                        "mixing_participants": len(inputs),
                        "input_count": len(inputs),
                        "equal_output_count": identical_output_count,
                        "denomination_variance": 0.0 if len(equal_groups) == 1 and identical_output_count == len(outputs) else None,
                        "uniformity_ratio": round(match_ratio, 2)
                    }
        return False, 0.0, {}
