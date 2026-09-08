"""Evaluate a versioned candidate without training on the held-out rows."""
from __future__ import annotations

import json
from typing import Iterable

import numpy as np
from sklearn.metrics import average_precision_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def evaluate(model, X: np.ndarray, y: np.ndarray) -> dict:
    probabilities = model.predict_proba(X)[:, 1]
    predictions = (probabilities >= .5).astype(int)
    discrimination = {"roc_auc": float(roc_auc_score(y, probabilities)), "pr_auc": float(average_precision_score(y, probabilities))} if len(np.unique(y)) == 2 else {"roc_auc": None, "pr_auc": None, "warning": "split contains one class; discrimination metrics unavailable"}
    return {**discrimination,
            "precision": float(precision_score(y, predictions, zero_division=0)), "recall": float(recall_score(y, predictions, zero_division=0)),
            "f1": float(f1_score(y, predictions, zero_division=0)), "confusion_matrix": confusion_matrix(y, predictions).tolist(),
            "class_distribution": {"negative": int((y == 0).sum()), "positive": int((y == 1).sum())}}
