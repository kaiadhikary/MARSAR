"use client";

import { FormEvent, useState } from "react";
import Canvas from "@/components/graph/Canvas";
import NodeDetails from "@/components/graph/NodeDetails";
import {
  fetchAddressGraph,
  GraphEdge,
  GraphNode,
  ClusterInfo,
  exportStrReport,
  ExportIntegrity,
} from "@/lib/api";

export default function InvestigatorPage() {
  const [addressInput, setAddressInput] = useState("");
  const [txidInput, setTxidInput] = useState("");
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [cluster, setCluster] = useState<ClusterInfo | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [integrity, setIntegrity] = useState<ExportIntegrity | null>(null);

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

  async function handleExport(e: FormEvent) {
    e.preventDefault();
    if (!txidInput.trim()) return;
    setExporting(true);
    setError(null);
    try {
      const { blob, integrity: meta } = await exportStrReport({ txid: txidInput.trim() });
      setIntegrity(meta);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `MARSAR-STR-${txidInput.trim().slice(0, 16)}.html`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (!status) setError("Cannot reach the API on http://localhost:8000. Start FastAPI (uvicorn) and try again.");
      else if (status === 404) setError("Transaction not found.");
      else if (status === 400) setError("Invalid TXID.");
      else setError(`Report generation failed (HTTP ${status}).`);
    } finally {
      setExporting(false);
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

      <section className="mb-6 rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h2 className="mb-3 text-sm font-semibold">Export forensic dossier</h2>
        <form onSubmit={handleExport} className="flex flex-wrap gap-2">
          <input
            value={txidInput}
            onChange={(e) => setTxidInput(e.target.value)}
            placeholder="Paste a persisted TXID…"
            className="min-w-[20rem] flex-1 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm"
          />
          <button
            type="submit"
            disabled={exporting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {exporting ? "Generating…" : "Generate HTML dossier"}
          </button>
        </form>
        {integrity && (
          <p className="mt-3 break-all font-mono text-xs text-slate-400">
            SHA-256 {integrity.evidence_sha256 || "Unavailable"} · {integrity.verdict} ·
            score {integrity.risk_score}
          </p>
        )}
      </section>

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
