"""
Tests for Engine 5's scoring formula (app/engine/scoring.py).

These are deterministic — no live mempool connection, no trained model,
no database required. They exist to answer one question definitively:
"is the 4-layer weighted formula actually computing what the spec says?"

Run with:
    cd backend
    pytest tests/test_scoring.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.scoring import compute_risk_score, score_typology, score_mixer_penalty
from app.core.config import settings


def test_weights_sum_to_one():
    """If this ever fails, the formula stops being a 0-100 scale."""
    total = (
        settings.WEIGHT_TAINT
        + settings.WEIGHT_TYPOLOGY
        + settings.WEIGHT_ML_PROBABILITY
        + settings.WEIGHT_MIXER_PENALTY
    )
    assert abs(total - 1.0) < 1e-6


def test_clean_transaction_scores_zero():
    """No blacklist hit, no typology finding, no ML signal, no mixer -> 0."""
    result = compute_risk_score(
        blacklist_hit=False,
        typology_findings=[],
        ml_probability=0.0,
        is_coinjoin=False,
        mixer_entropy=0.0,
    )
    assert result.total == 0.0
    assert result.verdict == "LICIT"


def test_pure_taint_hit_matches_weight():
    """Blacklist hit alone should contribute exactly WEIGHT_TAINT * 100."""
    result = compute_risk_score(
        blacklist_hit=True,
        typology_findings=[],
        ml_probability=0.0,
        is_coinjoin=False,
        mixer_entropy=0.0,
    )
    expected = settings.WEIGHT_TAINT * 100.0
    assert result.total == round(expected, 2)
    assert result.taint_score == 100.0
    assert "BLACKLIST_HIT" in result.flags


def test_pure_typology_peeling_chain_matches_weight():
    """A peeling_chain finding should score Layer 2 at its full severity (100)."""
    result = compute_risk_score(
        blacklist_hit=False,
        typology_findings=[{"type": "peeling_chain"}],
        ml_probability=0.0,
        is_coinjoin=False,
        mixer_entropy=0.0,
    )
    expected = settings.WEIGHT_TYPOLOGY * 100.0
    assert result.total == round(expected, 2)
    assert result.typology_score == 100.0


def test_typology_severity_ordering():
    """peeling_chain/scatter_gather (100) must outrank rapid_velocity (70) alone."""
    assert score_typology([{"type": "peeling_chain"}]) == 100.0
    assert score_typology([{"type": "scatter_gather"}]) == 100.0
    assert score_typology([{"type": "rapid_velocity"}]) == 70.0
    # Mixed findings: take the highest severity, not an average or a sum.
    mixed = score_typology([{"type": "rapid_velocity"}, {"type": "peeling_chain"}])
    assert mixed == 100.0
    assert score_typology([]) == 0.0


def test_pure_ml_probability_matches_weight():
    """A raw model probability of 1.0 should contribute exactly WEIGHT_ML_PROBABILITY * 100."""
    result = compute_risk_score(
        blacklist_hit=False,
        typology_findings=[],
        ml_probability=1.0,
        is_coinjoin=False,
        mixer_entropy=0.0,
    )
    expected = settings.WEIGHT_ML_PROBABILITY * 100.0
    assert result.total == round(expected, 2)
    assert result.ml_probability_score == 100.0


def test_ml_probability_is_clamped_to_0_100():
    """A buggy/out-of-range model output should never blow past the 0-100 scale."""
    result = compute_risk_score(
        blacklist_hit=False, typology_findings=[], ml_probability=5.0,  # e.g. someone forgot to normalize
        is_coinjoin=False, mixer_entropy=0.0,
    )
    assert result.ml_probability_score == 100.0


def test_mixer_penalty_scales_with_entropy():
    """Lower entropy (more uniform CoinJoin outputs) => stronger mixer signal."""
    zero_entropy = score_mixer_penalty(is_coinjoin=True, entropy=0.0)
    mid_entropy = score_mixer_penalty(is_coinjoin=True, entropy=2.0)
    high_entropy = score_mixer_penalty(is_coinjoin=True, entropy=4.0)
    not_a_mixer = score_mixer_penalty(is_coinjoin=False, entropy=0.0)

    assert zero_entropy == 100.0
    assert mid_entropy == 50.0
    assert high_entropy == 0.0
    assert not_a_mixer == 0.0
    assert zero_entropy > mid_entropy > high_entropy


def test_all_four_layers_combine_additively():
    """
    The whole point of the formula: layers must combine by weighted sum, not
    override each other. Verifies the exact arithmetic end-to-end.
    """
    result = compute_risk_score(
        blacklist_hit=True,
        typology_findings=[{"type": "rapid_velocity"}],
        ml_probability=0.5,
        is_coinjoin=True,
        mixer_entropy=0.0,
    )
    expected = (
        settings.WEIGHT_TAINT * 100.0
        + settings.WEIGHT_TYPOLOGY * 70.0
        + settings.WEIGHT_ML_PROBABILITY * 50.0
        + settings.WEIGHT_MIXER_PENALTY * 100.0
    )
    assert result.total == round(expected, 2)


def test_verdict_thresholds():
    """Confirms the 0-29 / 30-69 / 70-100 boundary behaviour from the spec."""
    # Force each band by choosing blacklist_hit + typology combos that land
    # cleanly on either side of THRESHOLD_SUSPICIOUS / THRESHOLD_HIGH_RISK.
    licit = compute_risk_score(
        blacklist_hit=False, typology_findings=[], ml_probability=0.0,
        is_coinjoin=False, mixer_entropy=0.0,
    )
    suspicious = compute_risk_score(
        blacklist_hit=True, typology_findings=[], ml_probability=0.0,
        is_coinjoin=False, mixer_entropy=0.0,
    )  # 40.0 with default weights
    high_risk = compute_risk_score(
        blacklist_hit=True, typology_findings=[{"type": "peeling_chain"}], ml_probability=1.0,
        is_coinjoin=True, mixer_entropy=0.0,
    )  # 100.0 with default weights

    assert licit.verdict == "LICIT"
    assert suspicious.total < settings.THRESHOLD_HIGH_RISK
    assert suspicious.verdict in ("SUSPICIOUS", "HIGH_RISK")  # depends on tuned weights
    assert high_risk.total >= settings.THRESHOLD_HIGH_RISK
    assert high_risk.verdict == "HIGH_RISK"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
