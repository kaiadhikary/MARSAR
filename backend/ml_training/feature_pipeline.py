"""Blockchain-only feature contract for real labelled training data.

No IP, ASN, port, country, or synthetic network field is invented here.
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List

FEATURE_SCHEMA = "blockchain_v2"
FEATURE_NAMES = ("input_count", "output_count", "total_input_btc", "total_output_btc", "fee", "fee_ratio", "output_entropy", "output_asymmetry")


def _entropy(values: List[float]) -> float:
    positive = [value for value in values if value > 0]
    total = sum(positive)
    return -sum((value / total) * math.log2(value / total) for value in positive) if total else 0.0


def extract_blockchain_features(record: Dict[str, object]) -> List[float]:
    """Use supplied blockchain fields only; reject a record missing them."""
    try:
        inputs = [float(item) for item in str(record["input_amounts"]).split(";") if item]
        outputs = [float(item) for item in str(record["output_amounts"]).split(";") if item]
    except (KeyError, ValueError) as exc:
        raise ValueError("input_amounts and output_amounts are required semicolon-delimited numeric fields") from exc
    if not inputs or not outputs or min(inputs + outputs) < 0:
        raise ValueError("transactions require non-negative input and output values")
    total_in, total_out = sum(inputs), sum(outputs)
    fee = float(record.get("fee") or max(0.0, total_in - total_out))
    if fee < 0 or total_in <= 0:
        raise ValueError("total input must be positive and fee cannot be negative")
    nonzero = [value for value in outputs if value > 0]
    asymmetry = max(nonzero) / min(nonzero) if len(nonzero) >= 2 else 1.0
    return [len(inputs), len(outputs), total_in, total_out, fee, fee / total_in, _entropy(outputs), min(asymmetry, 100.0)]
