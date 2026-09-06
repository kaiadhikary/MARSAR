"""
Engine 5 — 4-Layer Multi-Factor Risk Scoring Engine.

Implements the exact weighted formula from the SIH26146 spec:

    Risk Score = (0.40 x Taint_Exposure)
               + (0.25 x Typology_Score)
               + (0.20 x ML_Probability)
               + (0.15 x Mixer_Penalty)

Weights and suspicious/high-risk thresholds come from `settings`
(WEIGHT_TAINT, WEIGHT_TYPOLOGY, WEIGHT_ML_PROBABILITY, WEIGHT_MIXER_PENALTY,
THRESHOLD_SUSPICIOUS, THRESHOLD_HIGH_RISK) so they can be tuned without a
code change.

Each layer is scored 0-100 individually before weighting:

  Layer 1 (Taint):      100 if any address in the tx hit the OFAC/scam
                         blacklist, else 0. This is a direct-hit check, not
                         the spec's full FIFO/haircut multi-hop taint
                         propagation model — propagating taint percentage
                         across N hops of a fund-flow graph needs that graph
                         persisted, which is a further step beyond the
                         current schema (see NodeDetails "risk_score: 0.0"
                         limitation discussed earlier in this project).
  Layer 2 (Typology):    driven by Engine 4's findings for this tx —
                         peeling_chain / scatter_gather = 100 (structural,
                         high-confidence laundering pattern), rapid_velocity
                         alone = 70, nothing found = 0.
  Layer 3 (ML):          Engine 5's XGBoost probability x 100 (0 if no
                         model is loaded — see app/ml/inference.py).
  Layer 4 (Mixer):       100 when Engine 3 flags a probable CoinJoin AND its
                         Shannon entropy is low (uniform, predictable
                         outputs — the strongest mixer signal), decaying
                         linearly to 0 as entropy rises toward 4 bits; 0 if
                         not flagged as a mixer at all.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from app.core.config import settings


@dataclass
class RiskBreakdown:
    """Per-layer 0-100 scores plus the final weighted total, for transparency."""
    taint_score: float = 0.0
    typology_score: float = 0.0
    ml_probability_score: float = 0.0
    mixer_penalty_score: float = 0.0
    total: float = 0.0
    flags: List[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if self.total >= settings.THRESHOLD_HIGH_RISK:
            return "HIGH_RISK"
        if self.total >= settings.THRESHOLD_SUSPICIOUS:
            return "SUSPICIOUS"
        return "LICIT"


_TYPOLOGY_SEVERITY = {
    "peeling_chain": 100.0,
    "scatter_gather": 100.0,
    "rapid_velocity": 70.0,
}


def score_typology(typology_findings: List[dict]) -> float:
    """Layer 2 — highest-severity Engine 4 finding for this transaction, or 0."""
    if not typology_findings:
        return 0.0
    return max(_TYPOLOGY_SEVERITY.get(f.get("type"), 50.0) for f in typology_findings)


def score_mixer_penalty(is_coinjoin: bool, entropy: float) -> float:
    """Layer 4 — CoinJoin confidence, weighted by how uniform the outputs are."""
    if not is_coinjoin:
        return 0.0
    # entropy=0 (perfectly uniform outputs) -> 100; entropy>=4 bits -> 0.
    return max(0.0, min(100.0, 100.0 * (1.0 - entropy / 4.0)))


def compute_risk_score(
    *,
    blacklist_hit: bool,
    typology_findings: List[dict],
    ml_probability: float,
    is_coinjoin: bool,
    mixer_entropy: float,
) -> RiskBreakdown:
    """
    Combines all 4 layers into a single 0-100 risk score using the weights
    defined in `settings`. `ml_probability` is expected in [0, 1] (as
    returned by RiskInferenceEngine.predict_proba) and is scaled to 0-100
    here.
    """
    taint = 100.0 if blacklist_hit else 0.0
    typology = score_typology(typology_findings)
    ml_score = max(0.0, min(100.0, ml_probability * 100.0))
    mixer = score_mixer_penalty(is_coinjoin, mixer_entropy)

    total = (
        settings.WEIGHT_TAINT * taint
        + settings.WEIGHT_TYPOLOGY * typology
        + settings.WEIGHT_ML_PROBABILITY * ml_score
        + settings.WEIGHT_MIXER_PENALTY * mixer
    )

    flags = []
    if blacklist_hit:
        flags.append("BLACKLIST_HIT")
    flags.extend(f.get("type", "").upper() for f in typology_findings)
    if is_coinjoin:
        flags.append("COINJOIN")

    return RiskBreakdown(
        taint_score=taint,
        typology_score=typology,
        ml_probability_score=ml_score,
        mixer_penalty_score=mixer,
        total=round(total, 2),
        flags=flags,
    )
