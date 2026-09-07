"use client";

import { useState } from "react";
import Canvas from "@/components/graph/Canvas";
import NodeDetails from "@/components/graph/NodeDetails";
import {
  fetchGraphTopology,
  fetchInvestigatorData,
  GraphEdge,
  GraphNode,
} from "@/lib/api";
import { flattenTopology } from "@/lib/graph-utils";

type ViewMode = "search" | "full";

export default function InvestigatorPage() {
  const [addressInput, setAddressInput] = useState("");
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("search");
  const [investigator, setInvestigator] = useState<
    Awaited<ReturnType<typeof fetchInvestigatorData>> | null
  >(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!addressInput.trim()) return;

    setLoading(true);
    setError(null);
    setViewMode("search");
    try {
      const data = await fetchInvestigatorData(addressInput.trim(), 3);
      setInvestigator(data);
      setNodes(data.nodes);
      setEdges(data.edges);
      setSelected(null);
    } catch {
      setError(
        "Search failed. Ensure the backend is running and data has been ingested."
      );
      setNodes([]);
      setEdges([]);
      setInvestigator(null);
    } finally {
      setLoading(false);
    }
  }

  async function loadFullGraph() {
    setLoading(true);
    setError(null);
    setViewMode("full");
    setInvestigator(null);
    try {
      const topology = await fetchGraphTopology(200);
      const { nodes: n, edges: e } = flattenTopology(topology);
      setNodes(n);
      setEdges(e);
      setSelected(null);
    } catch {
      setError("Could not load graph topology from backend.");
      setNodes([]);
      setEdges([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Link Analysis</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-400">
          Entity and transaction graph linking IPs, wallets, and TXIDs.
          Correlate network-layer P2P observations (IP, port, geo/ASN) with
          blockchain-layer flows (inputs, outputs, amounts, fees).
        </p>
      </header>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <form onSubmit={handleSearch} className="flex flex-1 gap-2">
          <input
            value={addressInput}
            onChange={(e) => setAddressInput(e.target.value)}
            placeholder="Search wallet address to expand local subgraph…"
            className="min-w-[280px] flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-sm text-slate-100 placeholder:text-slate-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {loading && viewMode === "search" ? "Loading…" : "Expand Address"}
          </button>
        </form>
        <button
          onClick={loadFullGraph}
          disabled={loading}
          className="rounded-md border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-50"
        >
          {loading && viewMode === "full" ? "Loading…" : "Full Topology"}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="mb-3 flex flex-wrap gap-4 text-[10px] text-slate-500">
        <Legend color="bg-blue-500" label="Wallet" />
        <Legend color="bg-violet-500" label="Transaction" />
        <Legend color="bg-cyan-500" label="IP Peer" />
        <Legend color="bg-amber-500" label="Search target" />
        <Legend color="bg-red-500" label="Watchlist hit" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_1fr]">
        <div>
          <Canvas nodes={nodes} edges={edges} onNodeSelect={setSelected} />
          <p className="mt-2 text-xs text-slate-500">
            {nodes.length} nodes · {edges.length} edges
            {viewMode === "search" && investigator
              ? ` · subgraph around ${investigator.address.slice(0, 12)}…`
              : viewMode === "full"
                ? " · full network topology (last 200 txs)"
                : ""}
          </p>
        </div>
        <NodeDetails
          node={selected}
          cluster={investigator?.cluster ?? null}
          wallet={investigator?.wallet ?? null}
          compliance={investigator?.compliance ?? null}
        />
      </div>
    </main>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
      {label}
    </span>
  );
}
