#!/usr/bin/env python3
"""
Offline Model Training & Serialization Script.
Trains a Gradient Boosted Decision Tree on synthetic/Elliptic forensic feature vectors
and exports the serialized binary weights to app/ml/weights/elliptic_xgb.joblib.
"""

import argparse
import json
import os
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split


def generate_training_data(n_samples: int = 1500):
    """
    Generates synthetic forensic distributions across the 13 feature dimensions:
    1. total_input_btc
    2. total_output_btc
    3. num_inputs
    4. num_outputs
    5. miner_fee
    6. fee_ratio
    7. output_value_entropy
    8. max_output_asymmetry
    9. is_non_standard_port
    10. is_high_risk_asn
    11. is_high_risk_country
    12. script_type_code
    13. hour_of_broadcast
    """
    np.random.seed(42)
    half = n_samples // 2

    # --- Class 0: Licit Normal Transactions ---
    c0_in_btc = np.random.exponential(scale=0.8, size=half) + 0.001
    c0_out_btc = c0_in_btc * np.random.uniform(0.98, 0.999, size=half)
    c0_n_in = np.random.choice([1, 2, 3], size=half, p=[0.7, 0.2, 0.1])
    c0_n_out = np.random.choice([1, 2], size=half, p=[0.4, 0.6])
    c0_fee = c0_in_btc * np.random.uniform(0.0001, 0.001, size=half)
    c0_fee_ratio = c0_fee / c0_in_btc
    c0_entropy = np.random.uniform(0.5, 1.5, size=half)
    c0_asym = np.random.uniform(1.0, 3.5, size=half)
    c0_port = np.random.choice([0.0, 1.0], size=half, p=[0.97, 0.03])
    c0_asn = np.random.choice([0.0, 1.0], size=half, p=[0.95, 0.05])
    c0_country = np.random.choice([0.0, 1.0], size=half, p=[0.94, 0.06])
    c0_script = np.random.choice([1.0, 2.0, 3.0], size=half)
    c0_hour = np.random.uniform(0, 23, size=half)

    X_licit = np.column_stack([
        c0_in_btc, c0_out_btc, c0_n_in, c0_n_out, c0_fee, c0_fee_ratio,
        c0_entropy, c0_asym, c0_port, c0_asn, c0_country, c0_script, c0_hour
    ])
    y_licit = np.zeros(half, dtype=int)

    # --- Class 1: Illicit Patterns (Peeling chains, mixers, rapid layering) ---
    c1_in_btc = np.random.exponential(scale=4.5, size=half) + 0.1
    c1_out_btc = c1_in_btc * np.random.uniform(0.95, 0.99, size=half)
    c1_n_in = np.random.choice([1, 3, 5, 8], size=half, p=[0.4, 0.3, 0.2, 0.1])
    c1_n_out = np.random.choice([2, 4, 8], size=half, p=[0.5, 0.3, 0.2])
    c1_fee = c1_in_btc * np.random.uniform(0.005, 0.04, size=half)  # Urgent fees
    c1_fee_ratio = c1_fee / c1_in_btc
    c1_entropy = np.random.choice([0.1, 2.2], size=half)  # Peeling (low) or mixer (high)
    c1_asym = np.random.uniform(5.0, 60.0, size=half)     # High asymmetry
    c1_port = np.random.choice([0.0, 1.0], size=half, p=[0.4, 0.6])
    c1_asn = np.random.choice([0.0, 1.0], size=half, p=[0.2, 0.8])
    c1_country = np.random.choice([0.0, 1.0], size=half, p=[0.25, 0.75])
    c1_script = np.random.choice([2.0, 3.0, 4.0], size=half)
    c1_hour = np.random.uniform(0, 23, size=half)

    X_illicit = np.column_stack([
        c1_in_btc, c1_out_btc, c1_n_in, c1_n_out, c1_fee, c1_fee_ratio,
        c1_entropy, c1_asym, c1_port, c1_asn, c1_country, c1_script, c1_hour
    ])
    y_illicit = np.ones(half, dtype=int)

    X = np.vstack([X_licit, X_illicit])
    y = np.concatenate([y_licit, y_illicit])
    return X, y


def train_and_export(output: Path | None = None):
    weights_dir = Path(__file__).parent / "app" / "ml" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    weights_path = output or weights_dir / "elliptic_xgb.joblib"

    print("[*] Generating offline training distributions...")
    X, y = generate_training_data(2000)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    print("[*] Training GradientBoostingClassifier...")
    model = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.08,
        max_depth=4,
        subsample=0.85,
        random_state=42
    )
    model.fit(X_train, y_train)
    # Persist the training medians so inference can generate an auditable,
    # per-transaction counterfactual explanation without external packages.
    model.marsar_feature_baseline_ = np.median(X_train, axis=0).astype(np.float32)
    model.marsar_training_metadata_ = {
        "dataset": "synthetic forensic baseline",
        "limitations": "Demonstration model only; not trained on the Elliptic dataset or a real-world benchmark.",
        "feature_space": "MARSAR dual-layer 13-feature schema",
        "model": "sklearn GradientBoostingClassifier",
    }

    # Evaluate
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    print(f"[+] ROC-AUC Score: {auc:.4f}")
    print("\nClassification Report:\n", classification_report(y_test, preds))

    # Export weights
    joblib.dump(model, weights_path, compress=3)
    print(f"[+] Model weights serialized to: {weights_path}")
    print(f"[+] Binary size: {os.path.getsize(weights_path) / 1024:.2f} KB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train MARSAR's offline demonstration model.")
    parser.add_argument("--out", type=Path, help="Versioned output path. Defaults to the deployed weights path.")
    args = parser.parse_args()
    train_and_export(args.out)
