"""
Engine 4 — Typology & Graph Structural Engine.

Builds an in-memory address-level transaction graph (NetworkX DiGraph) as
transactions stream in, and scans it for the three structural laundering
signatures described in the spec:

  1. Peeling chains — a balance repeatedly split into one small "payment"
     output and one large "change" output across several rapid, consecutive
     single-input/two-output hops.
  2. Scatter-gather (layering) — one address fans out into many fresh
     addresses, which then funnel back into a single collection address
     within a bounded time window.
  3. Velocity telemetry — UTXOs spent unusually fast after being created
     (Δt < RAPID_VELOCITY_SECONDS_THRESHOLD), repeated across several
     consecutive hops for the same address — characteristic of an
     automated layering script rather than human spending behavior.

Honest limitation, worth calling out in the write-up/demo: BTIF has no full
archival node (by design — see the zero-budget architecture), so "UTXO
creation time" and "spend time" are approximated by wall-clock *observation*
time — when this process itself first saw the output appear, and when it
first saw it get spent. A UTXO created before this worker started has no
observed creation time and is correctly excluded from velocity scoring
(its Δt is unknown, not assumed to be zero or large).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import networkx as nx

from app.core.config import settings


# --------------------------------------------------------------------------
# Result types
# --------------------------------------------------------------------------

@dataclass
class PeelingChainResult:
    start_address: str
    hops: int
    chain: list[str]  # addresses in hop order, oldest first
    total_peeled_sats: int

    def to_dict(self) -> dict:
        return {
            "type": "peeling_chain",
            "start_address": self.start_address,
            "hops": self.hops,
            "chain": self.chain,
            "total_peeled_sats": self.total_peeled_sats,
        }


@dataclass
class ScatterGatherResult:
    source_address: str
    fanout_addresses: list[str]
    gather_address: str | None
    fanout_count: int
    window_seconds: float

    def to_dict(self) -> dict:
        return {
            "type": "scatter_gather",
            "source_address": self.source_address,
            "fanout_count": self.fanout_count,
            "fanout_addresses": self.fanout_addresses[:20],  # cap for STR report size
            "gather_address": self.gather_address,
            "window_seconds": round(self.window_seconds, 2),
        }


@dataclass
class VelocityFlag:
    address: str
    consecutive_rapid_hops: int
    avg_delta_seconds: float

    def to_dict(self) -> dict:
        return {
            "type": "rapid_velocity",
            "address": self.address,
            "consecutive_rapid_hops": self.consecutive_rapid_hops,
            "avg_delta_seconds": round(self.avg_delta_seconds, 2),
        }


@dataclass
class TypologyStats:
    txs_processed: int = 0
    peeling_chains_detected: int = 0
    scatter_gather_detected: int = 0
    velocity_flags_raised: int = 0


# --------------------------------------------------------------------------
# Typology engine
# --------------------------------------------------------------------------

class TypologyEngine:
    """
    Stateful engine: feed parsed transactions (Engine 1's normalized format)
    one at a time via `process_tx()`; it maintains an in-memory directed
    fund-flow graph and returns any typology findings triggered by that
    transaction.
    """

    def __init__(
        self,
        min_fanout: int | None = None,
        gather_window_seconds: float | None = None,
        peeling_min_hops: int | None = None,
        velocity_threshold_seconds: float | None = None,
    ) -> None:
        self.graph = nx.DiGraph()
        self.stats = TypologyStats()

        self.min_fanout = min_fanout or settings.SCATTER_GATHER_MIN_FANOUT
        self.gather_window_seconds = gather_window_seconds or settings.SCATTER_GATHER_MAX_WINDOW_SECONDS
        self.peeling_min_hops = peeling_min_hops or settings.PEELING_CHAIN_MIN_HOPS
        self.velocity_threshold_seconds = velocity_threshold_seconds or settings.RAPID_VELOCITY_SECONDS_THRESHOLD

        # (txid, vout_index) -> observed creation time (wall clock)
        self._utxo_created_at: dict[tuple[str, int], float] = {}
        # address -> recent Δt history (seconds), most recent last, capped
        self._address_velocity_history: dict[str, list[float]] = {}
        # De-duplication: once a given (source, gather) scatter-gather pair
        # or a given peeling chain has been reported, don't re-report it on
        # every subsequent transaction that still satisfies the same
        # condition — one alert per newly-confirmed pattern, not one per tx.
        self._reported_scatter_gather: set[tuple[str, str]] = set()
        self._reported_peeling_chains: set[str] = set()
        # large-output address -> immediately preceding qualifying peel hop.
        self._peeling_hop_into: dict[str, dict] = {}

    # ---- ingestion ------------------------------------------------------

    def process_tx(self, tx: dict, observed_at: float | None = None) -> list[dict]:
        """
        Feed one parsed transaction into the graph. Returns a list of any
        typology findings (peeling chain / scatter-gather / velocity)
        triggered by this transaction.
        """
        observed_at = observed_at if observed_at is not None else time.time()
        self.stats.txs_processed += 1

        txid = tx.get("txid")
        inputs = tx.get("inputs", [])
        outputs = tx.get("outputs", [])

        input_addresses = [i.get("address") for i in inputs if i.get("address")]
        output_entries = [
            (o.get("address"), o.get("value_sats") or 0, o.get("vout_index", idx))
            for idx, o in enumerate(outputs)
            if o.get("address")
        ]

        findings: list[dict] = []

        # --- velocity: how fast were this tx's spent UTXOs turned over
        # since they were created? ---
        rapid_hop_addrs: list[str] = []
        for inp in inputs:
            prev_txid, prev_vout = inp.get("prev_txid"), inp.get("prev_vout")
            addr = inp.get("address")
            if not addr or prev_txid is None or prev_vout is None:
                continue
            created_at = self._utxo_created_at.pop((prev_txid, prev_vout), None)
            if created_at is None:
                continue  # UTXO created before this worker started observing
            delta = observed_at - created_at
            if delta < 0:
                continue  # clock skew / out-of-order delivery guard
            history = self._address_velocity_history.setdefault(addr, [])
            history.append(delta)
            if len(history) > 20:
                del history[:-20]
            if delta < self.velocity_threshold_seconds:
                rapid_hop_addrs.append(addr)

        for addr in rapid_hop_addrs:
            recent = self._address_velocity_history[addr][-5:]
            if len(recent) >= 5 and all(d < self.velocity_threshold_seconds for d in recent):
                flag = VelocityFlag(
                    address=addr,
                    consecutive_rapid_hops=len(recent),
                    avg_delta_seconds=sum(recent) / len(recent),
                )
                self.stats.velocity_flags_raised += 1
                findings.append(flag.to_dict())

        # --- graph update: input addresses -> output addresses ---
        for in_addr in input_addresses:
            self.graph.add_node(in_addr)
            for out_addr, value_sats, _ in output_entries:
                self.graph.add_node(out_addr)
                if self.graph.has_edge(in_addr, out_addr):
                    edge = self.graph[in_addr][out_addr]
                    edge["value_sats"] += value_sats
                    edge["tx_count"] += 1
                    edge["last_seen"] = observed_at
                else:
                    self.graph.add_edge(
                        in_addr, out_addr,
                        value_sats=value_sats, tx_count=1,
                        first_seen=observed_at, last_seen=observed_at,
                        txid=txid,
                    )

        # --- record newly created UTXOs for future velocity checks ---
        for out_addr, value_sats, vout_index in output_entries:
            if txid is not None:
                self._utxo_created_at[(txid, vout_index)] = observed_at

        # --- record a transaction-level peeling hop before checking the chain ---
        if len(input_addresses) == 1 and len(output_entries) == 2:
            (addr_a, val_a, _), (addr_b, val_b, _) = output_entries
            if val_a > 0 or val_b > 0:
                small_val, large_val = (val_a, val_b) if val_a <= val_b else (val_b, val_a)
                large_addr = addr_b if val_a <= val_b else addr_a
                if large_val > 0 and small_val < large_val and small_val <= 0.5 * large_val:
                    self._peeling_hop_into[large_addr] = {
                        "source": input_addresses[0],
                        "peeled_sats": small_val,
                        "observed_at": observed_at,
                        "txid": txid,
                    }

        # --- peeling chain ---
        peel = self._check_peeling_chain(input_addresses, output_entries)
        if peel:
            chain_key = "->".join(peel.chain)
            if chain_key not in self._reported_peeling_chains:
                self._reported_peeling_chains.add(chain_key)
                self.stats.peeling_chains_detected += 1
                findings.append(peel.to_dict())

        # --- scatter-gather ---
        # The "gather" half of this pattern is only visible once the
        # fan-out addresses start paying onward — which happens in a *later*
        # transaction than the original fan-out tx. So on every tx we also
        # re-check each spent address's own predecessor (whoever originally
        # paid it), not just the addresses this tx itself is spending from.
        # That's what lets a scatter (SRC -> 15 fresh addrs) get *detected*
        # once enough of those 15 addresses later pay into one gather
        # address, rather than only at the moment of the original fan-out.
        scatter_candidates: set[str] = set(input_addresses)
        for in_addr in input_addresses:
            scatter_candidates.update(self.graph.predecessors(in_addr))

        for candidate in scatter_candidates:
            sg = self._check_scatter_gather(candidate, observed_at)
            if sg:
                key = (sg.source_address, sg.gather_address or "")
                if key not in self._reported_scatter_gather:
                    self._reported_scatter_gather.add(key)
                    self.stats.scatter_gather_detected += 1
                    findings.append(sg.to_dict())

        return findings

    # ---- detectors --------------------------------------------------------

    def _check_peeling_chain(
        self,
        input_addresses: list[str],
        output_entries: list[tuple[str, int, int]],
    ) -> PeelingChainResult | None:
        """Confirm a peeling chain using transaction-level hop records."""
        if len(input_addresses) != 1 or len(output_entries) != 2:
            return None

        in_addr = input_addresses[0]
        (addr_a, val_a, _), (addr_b, val_b, _) = output_entries
        if val_a == 0 and val_b == 0:
            return None

        small_val, large_val = (val_a, val_b) if val_a <= val_b else (val_b, val_a)
        large_addr = addr_b if val_a <= val_b else addr_a
        if large_val == 0 or small_val >= large_val:
            return None
        if small_val > 0.5 * large_val:
            return None

        hops = 1
        chain = [in_addr, large_addr]
        total_peeled = small_val
        cursor = in_addr
        visited: set[str] = {in_addr}

        while hops < 8:
            previous = self._peeling_hop_into.get(cursor)
            if not previous:
                break
            prev_source = previous.get("source")
            if not prev_source or prev_source in visited:
                break
            visited.add(prev_source)
            hops += 1
            chain.insert(0, prev_source)
            total_peeled += int(previous.get("peeled_sats", 0) or 0)
            cursor = prev_source

        if hops < self.peeling_min_hops:
            return None

        return PeelingChainResult(
            start_address=chain[0],
            hops=hops,
            chain=chain,
            total_peeled_sats=total_peeled,
        )

    def _check_scatter_gather(self, source: str, observed_at: float) -> ScatterGatherResult | None:
        """
        Fan-out: `source` has paid >= min_fanout distinct *fresh* addresses
        (addresses with no other inbound edge — consistent with freshly
        generated laundering addresses rather than long-lived wallets).
        Fan-in: at least half of those fan-out addresses have themselves
        already paid onward to one common address, within
        `gather_window_seconds` of each other — the scatter -> gather
        funnel.
        """
        successors = list(self.graph.successors(source))
        if len(successors) < self.min_fanout:
            return None

        fresh_successors = [s for s in successors if self.graph.in_degree(s) == 1]
        if len(fresh_successors) < self.min_fanout:
            return None

        downstream_hits: dict[str, list[float]] = {}
        for s in fresh_successors:
            for _, dst, data in self.graph.out_edges(s, data=True):
                downstream_hits.setdefault(dst, []).append(data.get("last_seen", observed_at))

        for dst, timestamps in downstream_hits.items():
            if len(timestamps) >= max(2, len(fresh_successors) // 2):
                window = max(timestamps) - min(timestamps)
                if window <= self.gather_window_seconds:
                    return ScatterGatherResult(
                        source_address=source,
                        fanout_addresses=fresh_successors,
                        gather_address=dst,
                        fanout_count=len(fresh_successors),
                        window_seconds=window,
                    )

        return None

    # ---- introspection ------------------------------------------------

    def summary(self) -> dict:
        return {
            "txs_processed": self.stats.txs_processed,
            "peeling_chains_detected": self.stats.peeling_chains_detected,
            "scatter_gather_detected": self.stats.scatter_gather_detected,
            "velocity_flags_raised": self.stats.velocity_flags_raised,
            "graph_nodes": self.graph.number_of_nodes(),
            "graph_edges": self.graph.number_of_edges(),
        }
