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
        self._build_graph()
        conn = get_db_connection()
        cur = conn.cursor()

        seeds = cur.execute("SELECT address, severity FROM illicit_seeds").fetchall()
        taint_scores: Dict[str, float] = {node: 0.0 for node in self.graph.nodes()}

        active_seeds = {s["address"]: float(s["severity"]) for s in seeds if s["address"] in self.graph}
        for seed_addr, severity in active_seeds.items():
            taint_scores[seed_addr] = severity

        # Each full Bitcoin transaction hop is 2 graph edges (Wallet -> TX, TX -> Wallet)
        # Total edge iterations must be max_hops * 2
        total_edge_steps = self.max_hops * 2

        for seed_node, initial_taint in active_seeds.items():
            current_layer = [seed_node]
            layer_taint = initial_taint

            for _ in range(total_edge_steps):
                next_layer = []
                for node in current_layer:
                    successors = list(self.graph.successors(node))
                    if not successors:
                        continue

                    out_weights = [self.graph[node][succ].get("weight", 1.0) for succ in successors]
                    total_out = sum(out_weights) or 1.0

                    for succ in successors:
                        edge_weight = self.graph[node][succ].get("weight", 1.0)
                        hop_taint = (layer_taint * self.decay_factor) * (edge_weight / total_out)
                        taint_scores[succ] = min(1.0, taint_scores[succ] + hop_taint)
                        if succ not in next_layer:
                            next_layer.append(succ)

                layer_taint *= self.decay_factor
                current_layer = next_layer
                if not current_layer:
                    break

        conn.close()
        return {k: round(v, 4) for k, v in taint_scores.items()}