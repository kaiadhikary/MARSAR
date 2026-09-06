"use client";

// Interactive Cytoscape graph canvas — search a Bitcoin address, see its
// entity cluster expanded as a graph, and inspect any node.
import { useState } from "react";
import Canvas from "@/components/graph/Canvas";
import NodeDetails from "@/components/graph/NodeDetails";
import { fetchAddressGraph, GraphEdge, GraphNode, ClusterInfo } from "@/lib/api";

export default function InvestigatorPage() {
  const [addressInput, setAddressInput] = useState("");
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [cluster, setCluster] = useState<ClusterInfo | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!addressInput.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await fetchAddressGraph(addressInput.trim());
      setNodes(data.nodes);
      setEdges(data.edges);
      setCluster(data.cluster);
      setSelected(null);
    } catch (err) {
      setError(
        "Couldn't reach the backend. Make sure the FastAPI server is running on port 8000."
      );
      setNodes([]);
      setEdges([]);
      setCluster(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <h1 className="mb-4 text-xl font-semibold">MARSAR — Address Investigator</h1>

      <form onSubmit={handleSearch} className="mb-6 flex gap-2">
        <input
          value={addressInput}
          onChange={(e) => setAddressInput(e.target.value)}
          placeholder="Paste a Bitcoin address to expand its cluster graph…"
          className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-sm text-slate-100 placeholder:text-slate-500"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
        >
          {loading ? "Loading…" : "Expand"}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[2fr_1fr]">
        <Canvas nodes={nodes} edges={edges} onNodeSelect={setSelected} />
        <NodeDetails node={selected} cluster={cluster} />
      </div>

      {!loading && nodes.length === 0 && !error && (
        <p className="mt-4 text-sm text-slate-500">
          No graph loaded yet — search an address above. Try one of the
          addresses your worker has already clustered (check with{" "}
          <code className="rounded bg-slate-800 px-1">python check_clusters.py</code>{" "}
          on the backend).
        </p>
      )}
    </main>
  );
}
