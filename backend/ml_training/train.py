"""Train a candidate blockchain-only Gradient Boosting model from prepared CSV."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from app.ml.model_contract import FEATURE_SCHEMA_VERSION
from ml_training.feature_pipeline import FEATURE_NAMES, FEATURE_SCHEMA
from ml_training.model_registry import register
from ml_training.evaluate import evaluate


def _split(X, y, groups, seed):
    """Prefer entity-aware splitting; otherwise use stratification."""
    if len(set(groups)) > 1 and any(groups):
        train_idx, test_idx = next(GroupShuffleSplit(test_size=0.20, random_state=seed).split(X, y, groups))
        local_train, local_val = next(GroupShuffleSplit(test_size=0.20, random_state=seed).split(X[train_idx], y[train_idx], np.asarray(groups)[train_idx]))
        return train_idx[local_train], train_idx[local_val], test_idx
    train_idx, test_idx = train_test_split(np.arange(len(y)), test_size=.20, stratify=y, random_state=seed)
    train_idx, val_idx = train_test_split(train_idx, test_size=.20, stratify=y[train_idx], random_state=seed)
    return train_idx, val_idx, test_idx


def train(prepared: Path, registry: Path, version: str, promote: bool = False, seed: int = 42) -> dict:
    with prepared.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) < 20:
        raise ValueError("At least 20 labelled records are required to train a candidate model.")
    X = np.asarray([[float(row[name]) for name in FEATURE_NAMES] for row in rows], dtype=np.float32)
    y = np.asarray([int(row["label"]) for row in rows])
    if len(set(y)) != 2:
        raise ValueError("Training dataset must contain both licit and illicit labels.")
    train_idx, val_idx, test_idx = _split(X, y, [row.get("entity_id", "") for row in rows], seed)
    model = GradientBoostingClassifier(n_estimators=150, learning_rate=.05, max_depth=3, subsample=.85, random_state=seed)
    model.fit(X[train_idx], y[train_idx])
    model.marsar_feature_baseline_ = np.median(X[train_idx], axis=0).astype(np.float32)
    metadata = {"model_version": version, "algorithm": "sklearn GradientBoostingClassifier", "feature_schema": FEATURE_SCHEMA,
                "feature_names": list(FEATURE_NAMES), "training_dataset": str(prepared),
                "training_count": int(len(train_idx)), "validation_count": int(len(val_idx)), "test_count": int(len(test_idx)),
                "positive_count": int(y.sum()), "negative_count": int((1-y).sum()), "random_seed": seed,
                "training_timestamp": datetime.now(timezone.utc).isoformat(), "hyperparameters": model.get_params(),
                "metrics": {"validation": evaluate(model, X[val_idx], y[val_idx]), "test": evaluate(model, X[test_idx], y[test_idx])}}
    model.marsar_metadata_ = metadata
    temporary = registry / f"{version}.candidate.joblib"; temporary.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, temporary, compress=3)
    target = register(temporary, metadata, registry, version, promote)
    temporary.unlink()
    return {"path": str(target), **metadata}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("prepared", type=Path); parser.add_argument("--registry", type=Path, default=Path("models")); parser.add_argument("--version", required=True); parser.add_argument("--promote", action="store_true")
    print(json.dumps(train(parser.parse_args().prepared, parser.parse_args().registry, parser.parse_args().version, parser.parse_args().promote), indent=2, default=str))
