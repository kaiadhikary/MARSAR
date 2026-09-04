"""
Mixer De-Obfuscation & Combinatorial Engine.

Formulates CoinJoin demixing as a subset-sum problem:

    sum(Inputs_i for i in S_in) - Fee(S) = sum(Outputs_j for j in S_out)

For every candidate subset of inputs, we look for a subset of outputs whose
total falls within the transaction's fee margin below the input subset's
total. When exactly one output subset satisfies this for a given input
subset (and vice versa), that's a confirmed link — the transaction's mixing
has been at least partially broken. When several output subsets satisfy it
equally well, the link stays ambiguous, which is exactly what CoinJoin is
designed to produce.

Search space control: subset depth is capped at k=4 per the spec ("iterates
over combinations of inputs and outputs up to depth k=4"), and the number of
inputs/outputs considered per side is capped (see `_MAX_ITEMS_PER_SIDE`) so a
large real-world CoinJoin doesn't blow up combinatorially — this is a
hackathon-scale demonstrator, not a production-grade solver like those used
by commercial chain-analysis firms.
"""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations

# Per spec: branch-and-bound up to subset depth k=4.
MAX_SUBSET_DEPTH = 4

# Guard rail: combinations(N, 4) grows fast (15 choose 4 = 1365, 20 choose 4
# = 4845). Cap N so a large real-world CoinJoin (50+ outputs) degrades to
# "no full solve attempted" instead of hanging.
_MAX_ITEMS_PER_SIDE = 16


@dataclass
class DemixLink:
    input_indices: tuple[int, ...]
    output_indices: tuple[int, ...]
    input_sum: int
    output_sum: int
    diff_sats: int          # implied fee attributed to this link
    confidence: str         # "confirmed" (unique match) or "ambiguous"

    def to_dict(self) -> dict:
        return {
            "input_indices": list(self.input_indices),
            "output_indices": list(self.output_indices),
            "input_sum": self.input_sum,
            "output_sum": self.output_sum,
            "implied_fee_sats": self.diff_sats,
            "confidence": self.confidence,
        }


@dataclass
class DemixResult:
    txid: str | None
    entropy_bits: float
    links: list[DemixLink] = field(default_factory=list)
    solved: bool = True
    reason: str | None = None  # populated when solved=False

    def to_dict(self) -> dict:
        return {
            "txid": self.txid,
            "entropy_bits": self.entropy_bits,
            "solved": self.solved,
            "reason": self.reason,
            "confirmed_links": [
                l.to_dict() for l in self.links if l.confidence == "confirmed"
            ],
            "ambiguous_links": [
                l.to_dict() for l in self.links if l.confidence == "ambiguous"
            ],
        }


# --------------------------------------------------------------------------
# Shannon entropy
# --------------------------------------------------------------------------

def shannon_entropy(values: list[int]) -> float:
    """
    H(X) = -sum(P(x_i) * log2(P(x_i))) over the distribution of output
    values in a transaction. Low entropy => outputs cluster into a few
    predictable amounts (e.g. one obvious "change" value standing apart from
    many identical mix denominations) => easier to reason about which
    output is change. High entropy => value distribution is closer to
    uniform/unpredictable => harder to distinguish participants, i.e.
    better mixing.
    """
    if not values:
        return 0.0

    counts = Counter(values)
    total = len(values)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return round(entropy, 4)


# --------------------------------------------------------------------------
# Subset-sum solver
# --------------------------------------------------------------------------

def _subset_sums(values: list[int], max_depth: int) -> list[tuple[int, tuple[int, ...]]]:
    """
    All (sum, index-tuple) pairs for subsets of `values` of size 1..max_depth.
    Returned unsorted; caller sorts as needed.
    """
    n = len(values)
    results: list[tuple[int, tuple[int, ...]]] = []
    for size in range(1, min(max_depth, n) + 1):
        for combo in combinations(range(n), size):
            results.append((sum(values[i] for i in combo), combo))
    return results


def solve_demix(
    input_values: list[int],
    output_values: list[int],
    fee_sats: int,
    max_depth: int = MAX_SUBSET_DEPTH,
) -> list[DemixLink]:
    """
    Core subset-sum matcher. For every input subset (size 1..max_depth),
    find output subsets whose total lands in
    [input_sum - fee_sats, input_sum] (i.e. the fee this subset "paid" is
    non-negative and doesn't exceed the transaction's total fee — a
    simplification of the per-spec Fee(S) term, since apportioning the fee
    exactly per subset isn't observable from outputs alone).

    A link is "confirmed" when exactly one output subset falls in range for
    a given input subset AND that output subset doesn't also match a
    different input subset equally well. Otherwise it's "ambiguous".
    """
    if len(input_values) > _MAX_ITEMS_PER_SIDE or len(output_values) > _MAX_ITEMS_PER_SIDE:
        return []

    input_subsets = _subset_sums(input_values, max_depth)
    output_subsets = _subset_sums(output_values, max_depth)
    if not input_subsets or not output_subsets:
        return []

    # Sort output subsets by sum for binary-search range queries (the
    # "branch-and-bound with fee margin pruning" from the spec).
    output_subsets.sort(key=lambda t: t[0])
    output_sums = [s for s, _ in output_subsets]

    # For each output subset, track which input subsets matched it, so we
    # can tell confirmed (1:1) links apart from ambiguous (1:many) ones.
    matches_per_input: dict[tuple[int, ...], list[tuple[int, ...]]] = {}
    matches_per_output: dict[tuple[int, ...], list[tuple[int, ...]]] = {}

    for in_sum, in_idx in input_subsets:
        lo = in_sum - fee_sats
        hi = in_sum
        left = bisect_left(output_sums, lo)
        right = bisect_right(output_sums, hi)
        if left >= right:
            continue

        candidate_out_indices = [output_subsets[k][1] for k in range(left, right)]
        matches_per_input[in_idx] = candidate_out_indices
        for out_idx in candidate_out_indices:
            matches_per_output.setdefault(out_idx, []).append(in_idx)

    links: list[DemixLink] = []
    seen_pairs: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()

    for in_idx, out_candidates in matches_per_input.items():
        in_sum = sum(input_values[i] for i in in_idx)
        is_unique_pairing = (
            len(out_candidates) == 1
            and len(matches_per_output[out_candidates[0]]) == 1
        )
        for out_idx in out_candidates:
            key = (in_idx, out_idx)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            out_sum = sum(output_values[j] for j in out_idx)
            links.append(DemixLink(
                input_indices=in_idx,
                output_indices=out_idx,
                input_sum=in_sum,
                output_sum=out_sum,
                diff_sats=in_sum - out_sum,
                confidence="confirmed" if is_unique_pairing else "ambiguous",
            ))

    return links


# --------------------------------------------------------------------------
# Engine wrapper
# --------------------------------------------------------------------------

class DemixingEngine:
    """Applies subset-sum demixing + entropy scoring to a parsed transaction."""

    def __init__(self, max_depth: int = MAX_SUBSET_DEPTH) -> None:
        self.max_depth = max_depth

    def demix(self, tx: dict) -> DemixResult:
        inputs = tx.get("inputs", [])
        outputs = tx.get("outputs", [])
        output_values = [o.get("value_sats", 0) for o in outputs]
        entropy = shannon_entropy(output_values)

        if len(inputs) > _MAX_ITEMS_PER_SIDE or len(outputs) > _MAX_ITEMS_PER_SIDE:
            return DemixResult(
                txid=tx.get("txid"),
                entropy_bits=entropy,
                solved=False,
                reason=(
                    f"tx has more than {_MAX_ITEMS_PER_SIDE} inputs or outputs; "
                    "skipped full subset-sum solve to bound compute"
                ),
            )

        input_values = [i.get("value_sats") or 0 for i in inputs]
        fee_sats = tx.get("fee_sats") or 0

        links = solve_demix(input_values, output_values, fee_sats, self.max_depth)

        return DemixResult(
            txid=tx.get("txid"),
            entropy_bits=entropy,
            links=links,
        )
