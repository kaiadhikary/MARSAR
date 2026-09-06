"""
Tests for the feature extractor (app/ml/feature_extractor.py) and the
inference engine's model/feature mismatch guard (app/ml/inference.py).

Run with:
    cd backend
    pytest tests/test_ml_pipeline.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import joblib

from app.ml.feature_extractor import extract_features, FEATURE_NAMES
from app.ml.inference import RiskInferenceEngine


def test_feature_vector_shape_matches_names():
    features = extract_features(
        {"num_inputs": 2, "num_outputs": 2},
        input_values=[500_000, 300_000],
        output_values=[400_000, 390_000],
        fee_rate=10.0,
        entropy=1.0,
        is_coinjoin=False,
        cluster_member_count=2,
        blacklist_hit_count=1,
        typology_finding_count=0,
    )
    assert isinstance(features, np.ndarray)
    assert features.shape == (len(FEATURE_NAMES),)
    assert features.dtype == np.float64


def test_feature_values_are_correct_not_just_shaped_right():
    features = extract_features(
        {"num_inputs": 2, "num_outputs": 2},
        input_values=[500_000, 300_000],
        output_values=[400_000, 390_000],
        fee_rate=10.0,
        entropy=1.0,
        is_coinjoin=True,
        cluster_member_count=3,
        blacklist_hit_count=1,
        typology_finding_count=2,
    )
    as_dict = dict(zip(FEATURE_NAMES, features))
    assert as_dict["num_inputs"] == 2
    assert as_dict["num_outputs"] == 2
    assert as_dict["fee_rate_sat_vb"] == 10.0
    assert as_dict["shannon_entropy"] == 1.0
    assert as_dict["is_coinjoin"] == 1.0
    assert as_dict["total_input_btc"] == 800_000 / 1e8
    assert as_dict["total_output_btc"] == 790_000 / 1e8
    assert as_dict["cluster_member_count"] == 3
    assert as_dict["blacklist_hit_count"] == 1
    assert as_dict["typology_finding_count"] == 2


def test_no_crash_on_empty_outputs():
    """Divide-by-zero guard: a malformed tx with no outputs shouldn't crash."""
    features = extract_features({"num_inputs": 1, "num_outputs": 0})
    assert features.shape == (len(FEATURE_NAMES),)
    assert not np.isnan(features).any()
    assert not np.isinf(features).any()


def test_missing_model_file_degrades_gracefully():
    """No model on disk -> predict_proba returns neutral 0.0, never crashes."""
    engine = RiskInferenceEngine(model_path="/tmp/definitely_does_not_exist.joblib")
    features = np.zeros(len(FEATURE_NAMES))
    assert engine.predict_proba(features) == 0.0
    assert engine.is_model_loaded is False


def test_wrong_feature_count_model_is_rejected(tmp_path):
    """
    A model trained on a different feature count must NOT be silently used —
    this is exactly the guard added to inference.py this session.
    """
    from sklearn.ensemble import RandomForestClassifier

    # Train a throwaway model on 5 features (deliberately wrong vs. our 12).
    wrong_model = RandomForestClassifier(n_estimators=2, random_state=0)
    X = np.random.rand(20, 5)
    y = np.array([0, 1] * 10)
    wrong_model.fit(X, y)

    model_path = tmp_path / "wrong_feature_count.joblib"
    joblib.dump(wrong_model, model_path)

    engine = RiskInferenceEngine(model_path=str(model_path))
    features = np.zeros(len(FEATURE_NAMES))  # 12 features, model expects 5
    result = engine.predict_proba(features)

    assert result == 0.0
    assert engine.is_model_loaded is False, (
        "A model with a mismatched feature count must be rejected, not used."
    )


def test_correct_feature_count_model_is_accepted(tmp_path):
    """Sanity check the other direction: a matching model SHOULD load and be used."""
    from sklearn.ensemble import RandomForestClassifier

    right_model = RandomForestClassifier(n_estimators=2, random_state=0)
    X = np.random.rand(20, len(FEATURE_NAMES))
    y = np.array([0, 1] * 10)
    right_model.fit(X, y)

    model_path = tmp_path / "correct_feature_count.joblib"
    joblib.dump(right_model, model_path)

    engine = RiskInferenceEngine(model_path=str(model_path))
    features = np.random.rand(len(FEATURE_NAMES))
    result = engine.predict_proba(features)

    assert engine.is_model_loaded is True
    assert 0.0 <= result <= 1.0


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
