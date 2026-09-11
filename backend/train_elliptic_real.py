#!/usr/bin/env python3
"""
Train MARSAR's deployed GradientBoosting classifier on the official Elliptic
Bitcoin dataset and export artifacts compatible with MLInferenceEngine.

Runtime contract (app/ml/feature_extractor.py):
  13-dim vector, FEATURE_SCHEMA_VERSION = "blockchain_network_v1"
  Feature names:
    total_input_btc, total_output_btc, num_inputs, num_outputs, miner_fee,
    fee_ratio, output_value_entropy, max_output_asymmetry, is_non_standard_port,
    is_high_risk_asn, is_high_risk_country, script_type_code, hour_of_broadcast

Elliptic CSV layout (no header in features file):
  txId, time_step, local_feat_0..92 (93), agg_feat_0..71 (72)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

from app.ml.feature_extractor import FeatureExtractor
from app.ml.model_contract import FEATURE_SCHEMA_VERSION, validate_model_contract

ELLIPTIC_DIR = Path(__file__).resolve().parent / "data" / "elliptic"
DEFAULT_OUT_PRIMARY = Path(__file__).resolve().parent / "app" / "ml" / "weights" / "bitcoin_network_gbdt.joblib"
DEFAULT_OUT_ALIAS = Path(__file__).resolve().parent / "app" / "ml" / "weights" / "elliptic_xgb.joblib"

# Elliptic local-feature indices (0-based within the 93 local columns).
LOCAL = {
    "volume_a": 0,
    "volume_b": 1,
    "fee_signal": 2,
    "in_count": 3,
    "out_count": 4,
    "fee_level": 5,
    "dispersion": 6,
    "asymmetry": 7,
}
# Aggregated neighbour features used as graph-risk proxies (network layer absent in Elliptic).
AGG = {
    "neighbour_risk_a": 0,
    "neighbour_risk_b": 1,
    "neighbour_risk_c": 2,
}


def _pos_amount(z: float, base: float = 0.25, scale: float = 1.2) -> float:
    """Map a z-scored Elliptic local feature to a positive BTC-like magnitude."""
    z = float(np.clip(z, -2.5, 6.0))
    return float(np.clip(np.expm1(z) * scale + base, 0.01, 500.0))


def load_graph_degrees(edgelist_path: Path) -> Tuple[Dict[str, int], Dict[str, int]]:
    in_deg: Dict[str, int] = defaultdict(int)
    out_deg: Dict[str, int] = defaultdict(int)
    with edgelist_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            src = row["txId1"].strip()
            dst = row["txId2"].strip()
            out_deg[src] += 1
            in_deg[dst] += 1
    return in_deg, out_deg


def load_elliptic_tables(data_dir: Path) -> Tuple[Dict[str, np.ndarray], Dict[str, int]]:
    """Return feature rows keyed by txId and illicit labels (1=illicit)."""
    classes_path = data_dir / "elliptic_txs_classes.csv"
    features_path = data_dir / "elliptic_txs_features.csv"

    labels: Dict[str, int] = {}
    with classes_path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            txid = row["txId"].strip()
            klass = row["class"].strip()
            if klass == "unknown":
                continue
            if klass == "1":
                labels[txid] = 1
            elif klass == "2":
                labels[txid] = 0
            else:
                continue

    features: Dict[str, np.ndarray] = {}
    with features_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        for row in reader:
            if len(row) < 167:
                continue
            txid = row[0].strip()
            if txid not in labels:
                continue
            features[txid] = np.asarray([float(v) for v in row[1:]], dtype=np.float32)

    return features, labels


def elliptic_row_to_marsar_vector(
    row: np.ndarray,
    in_degree: int,
    out_degree: int,
) -> np.ndarray:
    """
    Project one Elliptic feature row into MARSAR's 13-dim runtime schema.

    row layout: [time_step, local_0..92, agg_0..71]
    """
    time_step = float(row[0])
    local = row[1:94]
    agg = row[94:]

    total_in = float(np.clip(
        _pos_amount(float(local[LOCAL["volume_a"]])) * _pos_amount(float(local[LOCAL["volume_b"]]), base=0.15, scale=0.8),
        0.01,
        500.0,
    ))
    fee_signal = float(np.clip(float(local[LOCAL["fee_signal"]]), -6.0, 6.0))
    total_out = float(np.clip(total_in * (0.90 + 0.10 / (1.0 + np.exp(-fee_signal))), 0.01, 500.0))

    n_in = max(1.0, min(64.0, float(in_degree or 0) or 1.0 + max(0.0, float(local[LOCAL["in_count"]]) + 2.0)))
    n_out = max(1.0, min(64.0, float(out_degree or 0) or 1.0 + max(0.0, float(local[LOCAL["out_count"]]) + 2.0)))

    fee = float(np.clip(total_in * 0.0015 * _pos_amount(float(local[LOCAL["fee_level"]]), base=0.05, scale=0.35), 1e-6, 5.0))
    fee_ratio = float(np.clip(fee / max(total_in, 1e-6), 1e-6, 0.25))

    entropy = float(np.clip(1.2 + float(local[LOCAL["dispersion"]]) * 0.35, 0.0, 3.5))
    asymmetry = float(np.clip(1.0 + abs(float(local[LOCAL["asymmetry"]])) * 2.5, 1.0, 60.0))

    # Elliptic has no P2P telemetry; neighbour aggregates act as graph-risk proxies.
    is_non_standard_port = 1.0 if float(agg[AGG["neighbour_risk_a"]]) > 0.75 else 0.0
    is_high_risk_asn = 1.0 if float(agg[AGG["neighbour_risk_b"]]) > 0.75 else 0.0
    is_high_risk_country = 1.0 if float(agg[AGG["neighbour_risk_c"]]) > 0.75 else 0.0

    script_type_code = 3.0  # p2wpkh default — script type is not disclosed in Elliptic.
    hour_of_broadcast = float(time_step % 24)

    return np.asarray(
        [
            total_in,
            total_out,
            n_in,
            n_out,
            fee,
            fee_ratio,
            entropy,
            asymmetry,
            is_non_standard_port,
            is_high_risk_asn,
            is_high_risk_country,
            script_type_code,
            hour_of_broadcast,
        ],
        dtype=np.float32,
    )


def build_training_matrix(
    data_dir: Path,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    in_deg, out_deg = load_graph_degrees(data_dir / "elliptic_txs_edgelist.csv")
    features, labels = load_elliptic_tables(data_dir)

    xs: List[np.ndarray] = []
    ys: List[int] = []
    for txid, row in features.items():
        vec = elliptic_row_to_marsar_vector(row, in_deg.get(txid, 0), out_deg.get(txid, 0))
        xs.append(vec)
        ys.append(labels[txid])

    if not xs:
        raise RuntimeError("No labelled Elliptic rows found. Check data/elliptic/ paths.")

    X = np.vstack(xs)
    X = np.nan_to_num(X, nan=0.0, posinf=500.0, neginf=0.0)
    y = np.asarray(ys, dtype=np.int32)
    names = FeatureExtractor.FEATURE_NAMES
    if X.shape[1] != len(names):
        raise RuntimeError(f"Feature width mismatch: built {X.shape[1]}, expected {len(names)}")
    return X, y, names


def train_elliptic_model(
    data_dir: Path,
    outputs: Iterable[Path],
    test_size: float = 0.25,
    random_state: int = 42,
    time_split: bool = False,
) -> dict:
    print("[*] Loading Elliptic dataset and projecting to MARSAR 13-feature schema...")
    t0 = time.time()
    X, y, feature_names = build_training_matrix(data_dir)
    print(f"    Labelled transactions: {len(y):,}  (illicit={int(y.sum()):,}, licit={int((1-y).sum()):,})")
    print(f"    Feature matrix shape: {X.shape}  ({', '.join(feature_names)})")

    if time_split:
        # Canonical Elliptic temporal hold-out: time_step < 35 train, >= 35 test.
        # Re-load time steps for the aligned rows only.
        features, labels = load_elliptic_tables(data_dir)
        steps = []
        for txid in features:
            if txid in labels:
                steps.append(float(features[txid][0]))
        steps_arr = np.asarray(steps, dtype=np.float32)
        train_mask = steps_arr < 35
        test_mask = ~train_mask
        X_train, X_test = X[train_mask], X[test_mask]
        y_train, y_test = y[train_mask], y[test_mask]
        print(f"    Time-based split: train={len(y_train):,}, test={len(y_test):,}")
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

    # Balance illicit under-representation with sample weights.
    weight_map = {
        0: 1.0,
        1: float((y_train == 0).sum()) / max(1, (y_train == 1).sum()),
    }
    sample_weight = np.asarray([weight_map[int(label)] for label in y_train], dtype=np.float32)

    print("[*] Training GradientBoostingClassifier...")
    model = GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.06,
        max_depth=4,
        subsample=0.85,
        random_state=random_state,
    )
    model.fit(X_train, y_train, sample_weight=sample_weight)
    model.marsar_feature_baseline_ = np.median(X_train, axis=0).astype(np.float32)
    model.marsar_metadata_ = {
        "feature_schema": FEATURE_SCHEMA_VERSION,
        "feature_names": feature_names,
        "dataset": "Elliptic Bitcoin Dataset (official)",
        "source_files": [
            "elliptic_txs_features.csv",
            "elliptic_txs_classes.csv",
            "elliptic_txs_edgelist.csv",
        ],
        "limitations": (
            "Trained on anonymized Elliptic graph features projected into MARSAR's "
            "13-feature dual-layer schema. Network-layer flags are graph-derived proxies."
        ),
        "feature_space": "MARSAR dual-layer 13-feature schema (Elliptic projection)",
        "model": "sklearn GradientBoostingClassifier",
        "training_count": int(len(y_train)),
        "test_count": int(len(y_test)),
        "illicit_count": int(y.sum()),
        "licit_count": int((1 - y).sum()),
        "projection": "elliptic_row_to_marsar_vector",
    }

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    report = classification_report(y_test, preds, target_names=["licit", "illicit"])

    print(f"\n[+] ROC-AUC Score: {auc:.4f}")
    print("\nClassification Report:\n", report)

    validate_model_contract(model)

    written = []
    for out_path in outputs:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, out_path, compress=3)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"[+] Model saved: {out_path} ({size_kb:.1f} KB)")
        written.append(str(out_path))

    elapsed = time.time() - t0
    summary = {
        "roc_auc": round(auc, 4),
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
        "outputs": written,
        "elapsed_seconds": round(elapsed, 1),
    }
    print(f"\n[+] Training complete in {elapsed:.1f}s")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train MARSAR ML weights from the official Elliptic dataset.")
    parser.add_argument("--data-dir", type=Path, default=ELLIPTIC_DIR, help="Directory containing elliptic_txs_*.csv")
    parser.add_argument(
        "--out",
        type=Path,
        nargs="+",
        default=[DEFAULT_OUT_PRIMARY, DEFAULT_OUT_ALIAS],
        help="joblib output path(s)",
    )
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--time-split", action="store_true", help="Use Elliptic time_step<35 train / >=35 test split")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    summary = train_elliptic_model(
        data_dir=args.data_dir,
        outputs=args.out,
        test_size=args.test_size,
        random_state=args.seed,
        time_split=args.time_split,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
