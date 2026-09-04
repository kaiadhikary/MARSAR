"""
Entity Clustering & Change Address Detection Engine.

Two responsibilities, per the spec:

1. Common Input Ownership Heuristic (CIOH) — when a transaction spends
   multiple input addresses in one signature payload, all of those input
   addresses are proven to be controlled by the same entity. We union them
   into one cluster using Disjoint-Set Union (Union-Find) with path
   compression + union by rank, giving amortized O(α(N)) merges.

2. CoinJoin pre-filter — if a transaction's outputs contain several
   identical-value amounts (the fingerprint of a CoinJoin/mixing tx), CIOH
   is *skipped* for that transaction. Applying CIOH to a CoinJoin would
   incorrectly merge unrelated participants into one false cluster —
   exactly the kind of poisoning this filter exists to prevent.

Change-address identification is a separate, softer heuristic (it doesn't
affect clustering correctness, just annotates which output is "change"
returning to the sender vs. the actual payment).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Disjoint-Set Union (Union-Find)
# --------------------------------------------------------------------------

class DisjointSetUnion:
    """
    Union-Find over arbitrary hashable items (Bitcoin addresses, here).
    Path compression on find() + union by rank gives amortized O(α(N))
    per operation, so clustering millions of addresses stays cheap.
    """

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def _make_set(self, item: str) -> None:
        if item not in self._parent:
            self._parent[item] = item
            self._rank[item] = 0

    def find(self, item: str) -> str:
        self._make_set(item)
        # Path compression (iterative, to avoid recursion depth issues on
        # long chains).
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[item] != root:
            self._parent[item], item = root, self._parent[item]
        return root

    def union(self, a: str, b: str) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a == root_b:
            return
        # Union by rank: attach the shorter tree under the taller one.
        if self._rank[root_a] < self._rank[root_b]:
            root_a, root_b = root_b, root_a
        self._parent[root_b] = root_a
        if self._rank[root_a] == self._rank[root_b]:
            self._rank[root_a] += 1

    def connected(self, a: str, b: str) -> bool:
        return self.find(a) == self.find(b)

    def clusters(self) -> dict[str, list[str]]:
        """Return {cluster_root: [members]} for every address seen so far."""
        groups: dict[str, list[str]] = defaultdict(list)
        for item in self._parent:
            groups[self.find(item)].append(item)
        return dict(groups)

    def cluster_size(self, item: str) -> int:
        root = self.find(item)
        return sum(1 for i in self._parent if self.find(i) == root)


# --------------------------------------------------------------------------
# CoinJoin pre-filter
# --------------------------------------------------------------------------

# If this many (or more) outputs share the exact same satoshi value, treat
# the tx as a probable CoinJoin/mixing transaction and skip CIOH.
COINJOIN_MIN_IDENTICAL_OUTPUTS = 5


def is_probable_coinjoin(tx: dict) -> bool:
    """
    Detect the CoinJoin fingerprint: several outputs of identical value
    (e.g. 10 outputs of exactly 0.1 BTC), which signals multiple
    independent participants pooling inputs into one mixing transaction.
    """
    outputs = tx.get("outputs", [])
    if len(outputs) < COINJOIN_MIN_IDENTICAL_OUTPUTS:
        return False

    value_counts = Counter(o["value_sats"] for o in outputs if o.get("value_sats"))
    if not value_counts:
        return False

    most_common_value, count = value_counts.most_common(1)[0]
    return count >= COINJOIN_MIN_IDENTICAL_OUTPUTS


# --------------------------------------------------------------------------
# Change address detection
# --------------------------------------------------------------------------

def identify_change_output(tx: dict) -> int | None:
    """
    Best-effort heuristic for which output (by vout_index) is change
    returning to the sender, rather than the actual payment. Returns None
    if no output looks confidently like change (e.g. CoinJoins, or txs
    with only one output).

    Heuristics applied, in order of confidence:
      1. Script-type matching: an output whose script type matches an
         input's script type is more likely to be a same-wallet change
         address (senders' wallets are usually address-type-consistent).
      2. Round-number heuristic: a payment amount is more often a "round"
         figure (in sats or fiat-equivalent terms) than the leftover
         change; the non-round output is more likely to be change when
         exactly one candidate remains after rule 1.
      3. Single-output fallback: with exactly two outputs and no other
         signal, the smaller output is a weak default guess for change
         (peeling-chain behavior: small payment, large change) — flagged
         as low confidence by the caller.
    """
    inputs = tx.get("inputs", [])
    outputs = tx.get("outputs", [])

    if len(outputs) < 2 or is_probable_coinjoin(tx):
        return None

    input_script_types = {
        _infer_script_type_from_address(i.get("address"))
        for i in inputs
        if i.get("address")
    }
    input_script_types.discard(None)

    # Rule 1: script-type match against inputs.
    candidates = [
        o for o in outputs
        if _infer_script_type_from_address(o.get("address")) in input_script_types
    ]
    if len(candidates) == 1:
        return candidates[0]["vout_index"]

    # Rule 2: among remaining candidates (or all outputs if rule 1 was
    # inconclusive), prefer the one with a "less round" value.
    pool = candidates if candidates else outputs
    non_round = [o for o in pool if not _is_round_sats(o.get("value_sats", 0))]
    if len(non_round) == 1:
        return non_round[0]["vout_index"]

    # Rule 3: two-output fallback — smaller output as weak default.
    if len(outputs) == 2:
        smaller = min(outputs, key=lambda o: o.get("value_sats", 0))
        return smaller["vout_index"]

    return None


def _infer_script_type_from_address(address: str | None) -> str | None:
    """Cheap script-type inference from address prefix (mainnet only)."""
    if not address:
        return None
    if address.startswith("bc1p"):
        return "p2tr"          # Taproot
    if address.startswith("bc1"):
        return "p2wpkh_or_wsh"  # Native SegWit
    if address.startswith("3"):
        return "p2sh"           # Wrapped SegWit / multisig
    if address.startswith("1"):
        return "p2pkh"          # Legacy
    return None


def _is_round_sats(value_sats: int) -> bool:
    """A crude 'looks like a round payment amount' check."""
    if value_sats <= 0:
        return False
    # Round to the nearest 1,000 sats, or a round BTC-fraction (e.g. exactly
    # divisible by 100,000 sats = 0.001 BTC) reads as an intentional amount.
    return value_sats % 1_000 == 0 or value_sats % 100_000 == 0


# --------------------------------------------------------------------------
# Clustering engine
# --------------------------------------------------------------------------

@dataclass
class ClusteringStats:
    txs_processed: int = 0
    txs_clustered: int = 0
    txs_skipped_coinjoin: int = 0
    addresses_seen: set[str] = field(default_factory=set)


class ClusteringEngine:
    """
    Stateful engine that consumes normalized transactions (from Engine 1)
    and maintains a running CIOH clustering of all addresses seen.
    """

    def __init__(self) -> None:
        self.dsu = DisjointSetUnion()
        self.stats = ClusteringStats()
        # cluster_root -> list of (txid, vout_index) flagged as change,
        # useful context for the graph/typology engine later.
        self._change_outputs: dict[str, list[tuple[str, int]]] = defaultdict(list)

    def process_tx(self, tx: dict) -> str | None:
        """
        Apply CIOH clustering to one parsed transaction. Returns the
        resulting cluster root address for this tx's inputs, or None if
        the tx had no clusterable inputs (e.g. a coinbase tx) or was
        skipped as a probable CoinJoin.
        """
        self.stats.txs_processed += 1

        input_addresses = [
            i["address"] for i in tx.get("inputs", []) if i.get("address")
        ]
        self.stats.addresses_seen.update(input_addresses)

        if is_probable_coinjoin(tx):
            self.stats.txs_skipped_coinjoin += 1
            # Still register addresses as known (each its own singleton
            # cluster for now) without unioning them.
            for addr in input_addresses:
                self.dsu.find(addr)
            return None

        if not input_addresses:
            return None

        # CIOH: union every input address in this tx into one cluster.
        first = input_addresses[0]
        for addr in input_addresses[1:]:
            self.dsu.union(first, addr)
        self.stats.txs_clustered += 1

        cluster_root = self.dsu.find(first)

        change_idx = identify_change_output(tx)
        if change_idx is not None:
            self._change_outputs[cluster_root].append((tx.get("txid"), change_idx))
            change_output = tx["outputs"][change_idx]
            change_address = change_output.get("address")
            if change_address:
                # The change address belongs to the same entity as the
                # inputs — union it in too, growing the cluster forward.
                self.dsu.union(first, change_address)

        return self.dsu.find(first)

    def get_cluster(self, address: str) -> list[str]:
        """All addresses currently known to belong to `address`'s cluster."""
        root = self.dsu.find(address)
        return self.dsu.clusters().get(root, [address])

    def cluster_id(self, address: str) -> str:
        """A stable identifier for an address's cluster (its DSU root)."""
        return self.dsu.find(address)

    def summary(self) -> dict:
        return {
            "txs_processed": self.stats.txs_processed,
            "txs_clustered": self.stats.txs_clustered,
            "txs_skipped_coinjoin": self.stats.txs_skipped_coinjoin,
            "unique_addresses_seen": len(self.stats.addresses_seen),
            "total_clusters": len(self.dsu.clusters()),
        }
