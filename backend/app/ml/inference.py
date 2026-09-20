import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingClassifier

from app.ml.feature_extractor import FeatureExtractor
from app.ml.model_contract import FEATURE_SCHEMA_VERSION, ModelContractError, validate_model_contract
from app.core.config import settings


class MLInferenceEngine:
    """
    Offline Machine Learning Inference Engine.
    Executes classification on dual-layer transaction vectors, outputs confidence
    scores, and generates feature-level explainability attributions.
    """
    def __init__(self, weights_path: Optional[str] = None):
        self.extractor = FeatureExtractor()
        if weights_path is None:
            weights_path = str(settings.WEIGHTS_PATH)
        
        self.weights_path = weights_path
        self.model = self._load_or_bootstrap_model()

    def _load_or_bootstrap_model(self) -> Any:
        """
        Loads pre-trained offline weights if valid; otherwise initializes
        an embedded fallback estimator to maintain air-gapped continuity.
        """
        if os.path.exists(self.weights_path) and os.path.getsize(self.weights_path) > 1024:
            try:
                loaded = joblib.load(self.weights_path)
                validate_model_contract(loaded)
                return loaded
            except ModelContractError:
                raise
            except Exception as exc:
                raise ModelContractError(f"Unable to load model artifact {self.weights_path}: {exc}") from exc

        # Offline self-contained fallback trained on synthetic baseline signatures
        fallback = GradientBoostingClassifier(n_estimators=30, max_depth=3, random_state=42)
        X_mock = np.array([
            # Licit regular transfers
            [0.2, 0.199, 1, 2, 0.0001, 0.0005, 0.8, 1.2, 0, 0, 0, 3, 14],
            [1.5, 1.498, 2, 2, 0.0002, 0.0001, 0.9, 2.1, 0, 0, 0, 3, 10],
            [0.05, 0.049, 1, 1, 0.0001, 0.0020, 0.0, 1.0, 0, 0, 0, 1, 16],
            # Illicit patterns (peeling chains, high risk ASN, rapid layering)
            [10.0, 9.998, 1, 2, 0.0020, 0.0002, 0.3, 45.0, 1, 1, 1, 2, 3],
            [4.5, 4.495, 4, 4, 0.0050, 0.0011, 2.0, 1.0, 1, 1, 1, 2, 2],
            [25.0, 24.95, 1, 2, 0.0500, 0.0020, 0.2, 30.0, 0, 1, 1, 3, 4]
        ], dtype=np.float32)
        y_mock = np.array([0, 0, 0, 1, 1, 1])
        fallback.fit(X_mock, y_mock)
        fallback.marsar_feature_baseline_ = np.median(X_mock, axis=0).astype(np.float32)
        fallback.marsar_metadata_ = {
            "model_version": "demo-fallback", "algorithm": "GradientBoostingClassifier",
            "feature_schema": FEATURE_SCHEMA_VERSION, "training_dataset": "synthetic demonstration fallback",
            "limitations": "Fallback only; not a real-data production model.",
        }
        return fallback

    def explain_prediction(self, feature_vector: np.ndarray, feature_names: List[str]) -> List[Dict[str, Any]]:
        """
        Calculates local, counterfactual contributions for this prediction.
        Each feature is replaced by the model's training median in turn and the
        change in illicit probability is measured.  This is intentionally
        labelled as a local sensitivity explanation, not SHAP.
        """
        if not hasattr(self.model, "predict_proba"):
            return []
        baseline = np.asarray(getattr(self.model, "marsar_feature_baseline_", np.zeros(len(feature_vector))), dtype=np.float32)
        if baseline.shape != feature_vector.shape:
            baseline = np.zeros(len(feature_vector), dtype=np.float32)
        observed = float(self.model.predict_proba(feature_vector.reshape(1, -1))[0][-1])
        explanations = []
        for index, name in enumerate(feature_names):
            counterfactual = feature_vector.copy()
            counterfactual[index] = baseline[index]
            probability_without_feature = float(self.model.predict_proba(counterfactual.reshape(1, -1))[0][-1])
            contribution = observed - probability_without_feature
            explanations.append({
                "feature": name,
                "value": float(round(feature_vector[index], 4)),
                "baseline_value": float(round(baseline[index], 4)),
                "probability_contribution": float(round(contribution, 4)),
                "direction": "increases_risk" if contribution >= 0 else "reduces_risk",
                "method": "local_counterfactual_sensitivity",
            })
        return sorted(explanations, key=lambda item: abs(item["probability_contribution"]), reverse=True)[:4]

    def predict(self, tx_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs ML inference on a single transaction dictionary.
        Returns illicit probability, class verdict, and explainability evidence.
        """
        feature_vector, feature_names = self.extractor.extract_from_record(tx_dict)
        X = feature_vector.reshape(1, -1)

        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(X)[0]
            # Probability of illicit class (Class 1)
            illicit_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])
        else:
            pred = self.model.predict(X)[0]
            illicit_prob = 1.0 if pred == 1 else 0.0

        confidence = max(illicit_prob, 1.0 - illicit_prob)
        is_illicit = bool(illicit_prob >= 0.50)
        explanations = self.explain_prediction(feature_vector, feature_names)

        return {
            "is_illicit": is_illicit,
            "illicit_probability": round(illicit_prob, 4),
            "confidence": round(confidence, 4),
            "top_contributing_features": explanations
        }

    def batch_predict(self, tx_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluates a batch of transactions and returns inferences sequentially."""
        return [self.predict(tx) for tx in tx_list]
