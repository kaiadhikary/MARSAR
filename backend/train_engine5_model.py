"""
train_engine5_model.py — trains a real XGBoost model against the SAME
12-feature schema app/ml/feature_extractor.py already extracts live, using
data your own run_worker.py has accumulated in storage.db.

WHY THIS APPROACH (read before you run it):
The original spec calls for training on the Elliptic dataset's 166
topological/temporal features. We don't compute those live (see
feature_extractor.py's own docstring) — building that full pipeline is a
separate, much bigger task (see train_elliptic_xgboost.py in this same
folder for that path instead).

What THIS script does instead is train on your own 12 features, using
Engine 5's own rule-based verdict (risk_verdict: LICIT vs
SUSPICIOUS/HIGH_RISK, which Layers 1/2/4 already compute deterministically)
as the training label. This is a legitimate technique — it's essentially
"teacher-student" distillation: Layers 1/2/4 (Taint, Typology, Mixer) are
the teacher; the model learns to recognize the *structural pattern* behind
those flags (fee behavior, entropy, cluster size, etc.), so it can flag
transactions that look similar even when they haven't tripped an exact
rule threshold yet (e.g. a peeling chain one hop short of
PEELING_CHAIN_MIN_HOPS). That's genuinely useful — but be honest about the
ceiling: this model can only ever approximate the rule engine it learned
from, not exceed it. It's a bootstrap, not ground truth.

PREREQUISITE: you need real accumulated data with BOTH classes present.
    1. Run the worker (run_worker.py) for a while — hours/days, not minutes
       — so storage.db actually has enough transactions.
    2. You need at least some SUSPICIOUS/HIGH_RISK examples, not just
       LICIT ones. If your blacklist seed lists are small, real mempool
       traffic may rarely trip Layer 1. To bootstrap a class-balanced demo
       dataset faster, temporarily add a handful of currently-active
       addresses to blacklisted_seeds (category='TEST_BOOTSTRAP') so some
       real traffic through them gets flagged and the model has something
       to learn against — remove them again afterwards.

Usage:
    cd backend
    python train_engine5_model.py
"""
from __future__ import annotations

import sqlite3
import sys

import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

from app.core.config import settings
from app.ml.feature_extractor import extract_features, FEATURE_NAMES

MIN_ROWS = 50
MIN_MINORITY_CLASS = 5


def load_training_data() -> tuple[np.ndarray, np.ndarray]:
    conn = sqlite3.connect(settings.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT txid, inputs_count, outputs_count, fee_rate, shannon_entropy,
               is_coinjoin, cluster_id, blacklist_hit, typology_flags, risk_verdict
        FROM transactions;
    """)
    tx_rows = cursor.fetchall()

    X, y = [], []
    for tx in tx_rows:
        cursor.execute(
            "SELECT direction, value_sats FROM transaction_addresses WHERE txid = ?;",
            (tx["txid"],),
        )
        addr_rows = cursor.fetchall()
        input_values = [r["value_sats"] for r in addr_rows if r["direction"] == "INPUT"]
        output_values = [r["value_sats"] for r in addr_rows if r["direction"] == "OUTPUT"]

        cluster_member_count = 0
        if tx["cluster_id"]:
            cursor.execute("SELECT member_count FROM clusters WHERE cluster_id = ?;", (tx["cluster_id"],))
            crow = cursor.fetchone()
            cluster_member_count = crow["member_count"] if crow else 0

        typology_flags = [f for f in (tx["typology_flags"] or "").split(",") if f]
        typology_finding_count = len([f for f in typology_flags if f not in ("BLACKLIST_HIT", "COINJOIN")])

        features = extract_features(
            {"num_inputs": tx["inputs_count"], "num_outputs": tx["outputs_count"]},
            input_values=input_values,
            output_values=output_values,
            fee_rate=tx["fee_rate"] or 0.0,
            entropy=tx["shannon_entropy"] or 0.0,
            is_coinjoin=bool(tx["is_coinjoin"]),
            cluster_member_count=cluster_member_count,
            blacklist_hit_count=1 if tx["blacklist_hit"] else 0,
            typology_finding_count=typology_finding_count,
        )
        label = 1 if (tx["risk_verdict"] or "LICIT") != "LICIT" else 0

        X.append(features)
        y.append(label)

    conn.close()
    return np.array(X), np.array(y)


def main() -> None:
    print(f"Loading training data from {settings.SQLITE_DB_PATH} ...")
    X, y = load_training_data()

    if len(X) < MIN_ROWS:
        print(f"\n❌ Only {len(X)} transactions found — need at least {MIN_ROWS}.")
        print("   Let run_worker.py run longer, then try again.")
        sys.exit(1)

    n_positive = int(y.sum())
    n_negative = len(y) - n_positive
    print(f"Loaded {len(X)} rows -> {n_negative} LICIT, {n_positive} SUSPICIOUS/HIGH_RISK.")

    if n_positive < MIN_MINORITY_CLASS or n_negative < MIN_MINORITY_CLASS:
        print(
            f"\n❌ Need at least {MIN_MINORITY_CLASS} examples of EACH class to train "
            f"anything meaningful (got {n_negative} LICIT / {n_positive} flagged)."
        )
        print("   See this file's module docstring for how to bootstrap more flagged examples.")
        sys.exit(1)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    try:
        from xgboost import XGBClassifier
        model = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            eval_metric="logloss", random_state=42,
        )
        model_name = "XGBoost"
    except ImportError:
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
        model_name = "RandomForest (xgboost not installed)"

    print(f"\nTraining {model_name} on {len(FEATURE_NAMES)} features: {FEATURE_NAMES}")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\n=== Held-out test set performance ===")
    print(classification_report(y_test, y_pred, target_names=["LICIT", "FLAGGED"]))
    if len(set(y_test)) > 1:
        print(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.3f}")

    out_path = settings.ELLIPTIC_MODEL_PATH
    joblib.dump(model, out_path)
    print(f"\n✅ Model saved to {out_path}")
    print(f"   n_features_in_ = {getattr(model, 'n_features_in_', 'unknown')} "
          f"(must equal {len(FEATURE_NAMES)} for inference.py to accept it)")
    print("\nRestart run_worker.py — it will pick up this model automatically on next start.")


if __name__ == "__main__":
    main()
