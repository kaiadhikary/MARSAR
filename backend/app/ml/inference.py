"""
Engine 5 — AI/ML Anomaly & Risk Scoring: model loader + inference.

Loads the offline-trained XGBoost classifier (see `training/` and the
project spec's Phase 3) from `settings.ELLIPTIC_MODEL_PATH` and exposes a
single `predict_proba()` call used by `app/engine/scoring.py`'s Layer 4.

IMPORTANT — current shipped state: `app/ml/weights/elliptic_xgb.joblib` in
this repository is a 0-byte placeholder; no model has actually been trained
and dropped in yet (that happens in the separate Colab pipeline the spec
describes under `training/`). Rather than crash the whole pipeline over a
missing/corrupt model file, this module degrades gracefully: it logs a
clear one-time warning and returns a neutral 0.0 probability, so Layer 4
simply contributes nothing to the risk score until a real model is
supplied. Everything else (Layers 1-3) keeps working normally.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np

from app.core.config import settings

logger = logging.getLogger("marsar.ml")


class RiskInferenceEngine:
    """Wraps the XGBoost model with a safe, always-callable predict_proba()."""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path or settings.ELLIPTIC_MODEL_PATH)
        self.model = None
        self.is_model_loaded = False
        self._load_attempted = False

    def _lazy_load(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True

        if not self.model_path.exists() or self.model_path.stat().st_size == 0:
            logger.warning(
                "Engine 5 ML model not found (or empty) at %s — Layer 4 "
                "(ML_Probability) will contribute 0 to every risk score "
                "until a real trained model is placed there.",
                self.model_path,
            )
            return

        try:
            import joblib  # imported lazily so the app still starts without it installed
            self.model = joblib.load(self.model_path)

            expected = getattr(self.model, "n_features_in_", None)
            if expected is not None:
                from app.ml.feature_extractor import FEATURE_NAMES
                if int(expected) != len(FEATURE_NAMES):
                    raise ValueError(
                        f"model expects {int(expected)} features but "
                        f"MARSAR extractor provides {len(FEATURE_NAMES)}"
                    )

            self.is_model_loaded = True
            logger.info("Engine 5 ML model loaded from %s", self.model_path)
        except Exception as err:
            logger.error(
                "Engine 5 ML model at %s failed to load (%s) — Layer 4 "
                "disabled for this run.",
                self.model_path, err,
            )
            self.model = None
            self.is_model_loaded = False

    def predict_proba(self, features: np.ndarray) -> float:
        """
        Returns the model's illicit-probability estimate in [0, 1].
        Returns 0.0 (neutral — no evidence either way) if no model is
        loaded, or if inference itself fails on a malformed feature vector.
        """
        self._lazy_load()
        if not self.is_model_loaded or self.model is None:
            return 0.0

        try:
            proba = self.model.predict_proba(features.reshape(1, -1))
            # xgboost/sklearn binary classifiers return [:, 1] as the
            # positive ("illicit") class probability.
            return float(proba[0][1])
        except Exception as err:
            logger.debug("Engine 5 inference failed on this transaction: %s", err)
            return 0.0


# Module-level singleton — one lazy-loaded model shared by the whole
# worker process, instead of re-reading the .joblib file per transaction.
inference_engine = RiskInferenceEngine()
