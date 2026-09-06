"""
Engine 5 — Feature Extractor.

Builds a fixed-order numeric feature vector for a single transaction, to be
fed into the XGBoost classifier in `inference.py`.

Honesty note: the BTIF spec references the Elliptic dataset's 166
topological/temporal features (degree, centrality, clustering coefficient,
etc., computed over the *entire* transaction graph via NetworkX). We do not
have that full graph persisted here — only cluster membership and per-tx
metadata (see app/db/sqlite_client.py's schema). This module instead
extracts a smaller, honest set of *local* features that are actually
available from the live pipeline: input/output structure, fee behaviour,
mixing entropy, and cluster/blacklist/typology context gathered earlier in
`run_worker.py`'s pipeline for the same transaction.

If a real Elliptic-trained model is dropped in at
`app/ml/weights/elliptic_xgb.joblib` expecting a different feature schema,
either retrain it against `FEATURE_NAMES` below, or adapt this extractor to
match the model's expected input order.
"""
from __future__ import annotations

from typing import List

import numpy as np

# Order matters — this is the exact column order fed to the model.
FEATURE_NAMES: List[str] = [
    "num_inputs",
    "num_outputs",
    "fee_rate_sat_vb",
    "shannon_entropy",
    "is_coinjoin",
    "total_input_btc",
    "total_output_btc",
    "avg_output_btc",
    "input_output_ratio",
    "cluster_member_count",
    "blacklist_hit_count",
    "typology_finding_count",
]


def extract_features(
    tx: dict,
    *,
    input_values: List[int] | None = None,
    output_values: List[int] | None = None,
    fee_rate: float = 0.0,
    entropy: float = 0.0,
    is_coinjoin: bool = False,
    cluster_member_count: int = 0,
    blacklist_hit_count: int = 0,
    typology_finding_count: int = 0,
) -> np.ndarray:
    """
    Returns a 1D numpy array matching FEATURE_NAMES, in order.

    Callers (run_worker.py) already compute most of these values earlier in
    the pipeline (Engine 2/3/4 output) — pass them straight through instead
    of recomputing, to avoid doing the work twice per transaction.
    """
    input_values = input_values or []
    output_values = output_values or []

    num_inputs = tx.get("num_inputs", len(tx.get("inputs", tx.get("vin", []))))
    num_outputs = tx.get("num_outputs", len(tx.get("outputs", tx.get("vout", []))))

    total_input_sats = sum(input_values)
    total_output_sats = sum(output_values)
    avg_output_sats = (total_output_sats / len(output_values)) if output_values else 0.0

    # Guard against divide-by-zero on coinbase-like or malformed transactions.
    input_output_ratio = (total_input_sats / total_output_sats) if total_output_sats > 0 else 0.0

    features = [
        float(num_inputs),
        float(num_outputs),
        float(fee_rate),
        float(entropy),
        1.0 if is_coinjoin else 0.0,
        total_input_sats / 1e8,
        total_output_sats / 1e8,
        avg_output_sats / 1e8,
        float(input_output_ratio),
        float(cluster_member_count),
        float(blacklist_hit_count),
        float(typology_finding_count),
    ]
    return np.array(features, dtype=np.float64)
