import json
import numpy as np
from typing import Dict, Set, List
from sklearn.decomposition import TruncatedSVD
from app.db.sqlite_client import get_db_connection


class DisjointSetUnion:
    def __init__(self):
        self.parent: Dict[str, str] = {}
        self.rank: Dict[str, int] = {}

    def find(self, item: str) -> str:
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0
            return item
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, item1: str, item2: str):
        root1 = self.find(item1)
        root2 = self.find(item2)
        if root1 != root2:
            if self.rank[root1] < self.rank[root2]:
                self.parent[root1] = root2
            elif self.rank[root1] > self.rank[root2]:
                self.parent[root2] = root1
            else:
                self.parent[root2] = root1
                self.rank[root1] += 1


class EntityClusterEngine:
    """
    NTRO Focus Area 1: Entity Clustering.
    Produces ownership clusters only from Common-Input-Ownership evidence.
    IP co-location and graph similarity are retained as supporting evidence, but
    never silently merged into an ownership conclusion (shared exchange and
    hosting infrastructure would otherwise over-merge unrelated wallets).
    """
    def __init__(self, embedding_similarity_threshold: float = 0.88):
        self.dsu = DisjointSetUnion()
        self.address_to_ips: Dict[str, Set[str]] = {}
        self.ip_to_addresses: Dict[str, Set[str]] = {}
        self.co_occurrence: Dict[str, Dict[str, float]] = {}
        self.sim_threshold = embedding_similarity_threshold

    def _record_co_occurrence(self, addr_a: str, addr_b: str, weight: float = 1.0):
        if addr_a not in self.co_occurrence:
            self.co_occurrence[addr_a] = {}
        if addr_b not in self.co_occurrence:
            self.co_occurrence[addr_b] = {}
        self.co_occurrence[addr_a][addr_b] = self.co_occurrence[addr_a].get(addr_b, 0.0) + weight
        self.co_occurrence[addr_b][addr_a] = self.co_occurrence[addr_b].get(addr_a, 0.0) + weight

    def _apply_graph_embeddings(self, all_addresses: List[str]) -> Dict[str, List[Dict[str, float]]]:
        """
        Derives low-dimensional node embeddings from the normalized graph adjacency matrix
        and clusters wallets exhibiting topological interaction similarity.
        """
        n = len(all_addresses)
        if n < 4:
            return {}

        addr_idx = {addr: i for i, addr in enumerate(all_addresses)}
        adj_matrix = np.zeros((n, n), dtype=np.float32)

        for src, neighbors in self.co_occurrence.items():
            if src in addr_idx:
                i = addr_idx[src]
                for dst, weight in neighbors.items():
                    if dst in addr_idx:
                        j = addr_idx[dst]
                        adj_matrix[i, j] = weight

        # SVD Graph Embedding
        dim = min(8, n - 1)
        svd = TruncatedSVD(n_components=dim, random_state=42)
        embeddings = svd.fit_transform(adj_matrix)

        # Normalize embeddings to unit hypersphere
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8
        norm_embeddings = embeddings / norms

        # Similarity is retained as supporting evidence. It does not prove
        # ownership and therefore must not union two wallets by itself.
        evidence: Dict[str, List[Dict[str, float]]] = {}
        for i in range(n):
            for j in range(i + 1, n):
                similarity = float(np.dot(norm_embeddings[i], norm_embeddings[j]))
                if similarity >= self.sim_threshold:
                    evidence.setdefault(all_addresses[i], []).append({"address": all_addresses[j], "similarity": round(similarity, 4)})
                    evidence.setdefault(all_addresses[j], []).append({"address": all_addresses[i], "similarity": round(similarity, 4)})
        return evidence

    def run_clustering(self) -> Dict[str, List[str]]:
        conn = get_db_connection()
        cur = conn.cursor()
        rows = cur.execute("SELECT txid, src_ip, inputs_json, outputs_json FROM transactions").fetchall()

        all_addresses: Set[str] = set()

        for row in rows:
            inputs = json.loads(row["inputs_json"])
            outputs = json.loads(row["outputs_json"])
            src_ip = (row["src_ip"] or "").strip()
            input_addrs = [inp["address"] for inp in inputs if inp.get("address")]
            output_addrs = [out["address"] for out in outputs if out.get("address")]

            for addr in input_addrs:
                all_addresses.add(addr)
                self.dsu.find(addr)

                if addr not in self.address_to_ips:
                    self.address_to_ips[addr] = set()
                if src_ip and src_ip != "UNKNOWN":
                    self.address_to_ips[addr].add(src_ip)
                    if src_ip not in self.ip_to_addresses:
                        self.ip_to_addresses[src_ip] = set()
                    self.ip_to_addresses[src_ip].add(addr)

            # Heuristic 1: CIOH
            if len(input_addrs) > 1:
                base_addr = input_addrs[0]
                for co_input in input_addrs[1:]:
                    self.dsu.union(base_addr, co_input)
                    self._record_co_occurrence(base_addr, co_input, weight=2.0)

            # Topological interaction edges for Graph Embeddings
            for in_a in input_addrs:
                for out_a in output_addrs:
                    all_addresses.add(out_a)
                    self.dsu.find(out_a)
                    self._record_co_occurrence(in_a, out_a, weight=1.0)

        # Execute graph embedding analysis as supporting evidence. It is never
        # used as a standalone ownership merge.
        embedding_evidence = self._apply_graph_embeddings(sorted(all_addresses))

        # Compile clusters
        clusters: Dict[str, List[str]] = {}
        for addr in all_addresses:
            root = self.dsu.find(addr)
            cluster_id = f"ENT_{root[:10]}"
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(addr)

        cur.execute("DELETE FROM entity_clusters")
        for cluster_id, addresses in clusters.items():
            for addr in addresses:
                ips = self.address_to_ips.get(addr, set())
                primary_ip = next(iter(ips)) if ips else "UNKNOWN"
                # CIOH is strong evidence. A repeated observed IP adds modest
                # support only; it never creates or expands this cluster.
                shared_ip_support = any(len(self.ip_to_addresses.get(ip, set())) > 1 for ip in ips)
                confidence = 0.95 if len(addresses) > 1 else 0.70
                if shared_ip_support:
                    confidence = min(0.98, confidence + 0.02)
                evidence = []
                if len(addresses) > 1:
                    evidence.append({"type": "CIOH", "strength": "strong", "detail": "Observed as common inputs in at least one transaction."})
                if shared_ip_support:
                    evidence.append({"type": "IP_COLOCATION", "strength": "supporting", "detail": "Shared broadcast IP is supporting evidence only."})
                for match in embedding_evidence.get(addr, [])[:3]:
                    evidence.append({"type": "GRAPH_SIMILARITY", "strength": "supporting", **match})
                cur.execute('''
                    INSERT INTO entity_clusters (cluster_id, wallet_address, primary_ip, confidence, evidence_json)
                    VALUES (?, ?, ?, ?, ?)
                ''', (cluster_id, addr, primary_ip, confidence, json.dumps(evidence)))

        conn.commit()
        conn.close()
        return clusters
