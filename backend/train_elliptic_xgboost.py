"""
train_elliptic_xgboost.py — standard training recipe on the REAL Elliptic
dataset, as originally described in the spec (166 topological/temporal
features, 203,769 nodes).

IMPORTANT — READ BEFORE RUNNING:
This trains a model on the Elliptic dataset's native 166-feature schema.
That is NOT the same schema this project's app/ml/feature_extractor.py
produces live (12 features — see that file's docstring for why). A model
trained by THIS script cannot be dropped into app/ml/weights/elliptic_xgb.joblib
and used by the live pipeline as-is — inference.py's feature-count guard
will correctly reject it (166 != 12) rather than silently misuse it.

To actually wire a model trained this way into the live system, someone
would need to build the full live feature pipeline the Elliptic dataset
assumes: a persisted, continuously-updated transaction graph with 2-hop
neighborhood aggregates, degree/centrality stats, and time-step bucketing
— a genuinely separate, larger engineering task from anything else in
this repo.

Use this script for: a standalone demo/proof that "we trained a real
model on the real Elliptic dataset" (useful for a hackathon writeup or
judge Q&A), or as a starting point for the larger feature-pipeline project
above. For the model that's ACTUALLY live in this pipeline today, use
train_engine5_model.py instead.

Setup:
    1. Download the Elliptic Data Set (Kaggle: "Elliptic Data Set", or the
       original https://www.kaggle.com/datasets/ellipticco/elliptic-data-set).
    2. You need these 3 files in the same folder as this script:
         elliptic_txs_features.csv
         elliptic_txs_classes.csv
         elliptic_txs_edgelist.csv   (not used by this basic script, but
                                       needed if you extend this to build
                                       graph-based features rather than
                                       using the pre-computed 166 columns)
    3. pip install pandas scikit-learn xgboost joblib

Run (locally or in Google Colab, per the original spec):
    python train_elliptic_xgboost.py
"""
from __future__ import annotations

import sys

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

try:
    from xgboost import XGBClassifier
except ImportError:
    print("pip install xgboost first.")
    sys.exit(1)


FEATURES_CSV = "elliptic_txs_features.csv"
CLASSES_CSV = "elliptic_txs_classes.csv"
OUTPUT_MODEL = "elliptic_xgb_166feature.joblib"


def main() -> None:
    try:
        # elliptic_txs_features.csv has no header: col0=txId, col1=timestep,
        # col2..167 = the 166 features.
        features = pd.read_csv(FEATURES_CSV, header=None)
    except FileNotFoundError:
        print(f"❌ {FEATURES_CSV} not found. See this file's docstring for where to get it.")
        sys.exit(1)

    classes = pd.read_csv(CLASSES_CSV)  # columns: txId, class ("1"=illicit, "2"=licit, "unknown")

    features.columns = ["txId", "timestep"] + [f"feat_{i}" for i in range(1, 167)]
    merged = features.merge(classes, on="txId", how="inner")

    # Drop "unknown"-labeled rows — no ground truth to train or evaluate against.
    labeled = merged[merged["class"] != "unknown"].copy()
    labeled["label"] = (labeled["class"] == "1").astype(int)  # 1 = illicit, 0 = licit

    print(f"Labeled rows: {len(labeled)} "
          f"({(labeled['label'] == 1).sum()} illicit, {(labeled['label'] == 0).sum()} licit)")

    feature_cols = [c for c in labeled.columns if c.startswith("feat_")]
    X = labeled[feature_cols].values
    y = labeled["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        eval_metric="logloss", random_state=42,
    )
    print(f"\nTraining XGBoost on {len(feature_cols)} Elliptic features...")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    print("\n=== Held-out test set performance ===")
    print(classification_report(y_test, y_pred, target_names=["licit", "illicit"]))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.3f}")

    joblib.dump(model, OUTPUT_MODEL)
    print(f"\n✅ Saved to {OUTPUT_MODEL} (166 features — NOT drop-in compatible with "
          f"this project's live inference.py; see this file's docstring).")


if __name__ == "__main__":
    main()
