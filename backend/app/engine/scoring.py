import json
import networkx as nx
from typing import Dict
from app.db.sqlite_client import get_db_connection


class RiskPropagationEngine:
    """
    Propagates taint from known illicit seed addresses (OFAC, ransomware, scams)
    through the directed transaction graph using Poison & Haircut decay.
    """
    def __init__(self, decay_factor: float = 0.85, max_hops: int = 3):
        self.graph = nx.DiGraph()
        self.decay_factor = decay_factor
        self.max_hops = max_hops

    def _build_graph(self):
        self.graph.clear()
        conn = get_db_connection()
        cur = conn.cursor()
        rows = cur.execute("SELECT txid, inputs_json, outputs_json FROM transactions").fetchall()

        for r in rows:
            txid = r["txid"]
            inputs = json.loads(r["inputs_json"])
            outputs = json.loads(r["outputs_json"])

            # Edge: Input Wallet -> TXID
            for inp in inputs:
                addr = inp.get("address")
                amt = float(inp.get("amount") or 0.0)
                if addr:
                    self.graph.add_edge(addr, txid, weight=amt)

            # Edge: TXID -> Output Wallet
            for out in outputs:
                addr = out.get("address")
                amt = float(out.get("amount") or 0.0)
                if addr:
                    self.graph.add_edge(txid, addr, weight=amt)

        conn.close()

    def propagate_taint(self) -> Dict[str, float]:
        """Value-aware bounded-sum Haircut propagation.

        For each directed edge, contribution is
        ``source_path_taint * (edge_value / total_outgoing_value) * decay``.
        Contributions arriving through independent paths are added and clamped
        at 1.0.  The frontier holds each node's own path contribution, so one
        branch can never overwrite another branch's taint.
        """
        self._build_graph()
        conn = get_db_connection()
        cur = conn.cursor()

        seeds = cur.execute("SELECT address, severity FROM illicit_seeds").fetchall()
        taint_scores: Dict[str, float] = {node: 0.0 for node in self.graph.nodes()}

        active_seeds = {s["address"]: float(s["severity"]) for s in seeds if s["address"] in self.graph}
        for seed_addr, severity in active_seeds.items():
            taint_scores[seed_addr] = severity

        total_edge_steps = self.max_hops * 2
        frontier = dict(active_seeds)
        for _ in range(total_edge_steps):
            next_frontier: Dict[str, float] = {}
            for node, path_taint in frontier.items():
                successors = list(self.graph.successors(node))
                weights = [max(0.0, float(self.graph[node][target].get("weight", 0.0))) for target in successors]
                total_weight = sum(weights)
                if total_weight <= 0.0:
                    continue
                for target, edge_weight in zip(successors, weights):
                    if edge_weight <= 0.0:
                        continue
                    contribution = path_taint * (edge_weight / total_weight) * self.decay_factor
                    next_frontier[target] = min(1.0, next_frontier.get(target, 0.0) + contribution)
                    taint_scores[target] = min(1.0, taint_scores[target] + contribution)
            frontier = next_frontier
            if not frontier:
                break

        conn.close()
        return {k: round(v, 4) for k, v in taint_scores.items()}
