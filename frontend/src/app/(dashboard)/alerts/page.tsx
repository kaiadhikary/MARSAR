"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  fetchRankedAlerts,
  recomputeAlerts,
} from "@/lib/api";
import AlertsTable from "@/components/widgets/AlertsTable";

const FOCUS_FILTERS = [
  "All",
  "Peeling-Chain Detection",
  "Mixing / CoinJoin",
  "ML Anomaly Detection",
  "Taint Propagation",
  "Network / Geo Risk",
];

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [recomputing, setRecomputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchRankedAlerts(
        100,
        filter === "All" ? undefined : filter
      );
      setAlerts(res.alerts);
      setError(null);
    } catch {
      setError("Failed to load alerts. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRecompute() {
    setRecomputing(true);
    try {
      await recomputeAlerts();
      await load();
    } catch {
      setError("Alert recomputation failed.");
    } finally {
      setRecomputing(false);
    }
  }

  return (
    <main className="p-6">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            Investigative Leads
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Ranked, explainable alerts — each entry shows why a wallet or
            transaction was flagged, with composite risk score, model confidence,
            and forensic evidence.
          </p>
        </div>
        <button
          onClick={handleRecompute}
          disabled={recomputing}
          className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium hover:bg-violet-500 disabled:opacity-50"
        >
          {recomputing ? "Running ML pipeline…" : "Recompute Alerts"}
        </button>
      </header>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {FOCUS_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-400 hover:text-slate-200"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Loading alerts…</p>
      ) : (
        <AlertsTable
          alerts={alerts}
          expandedId={expandedId}
          onToggle={(id) =>
            setExpandedId((prev) => (prev === id ? null : id))
          }
        />
      )}

      <div className="mt-6 rounded-lg border border-slate-800 bg-slate-900/30 p-4 text-xs text-slate-500">
        <strong className="text-slate-400">Legend:</strong> P = Peeling chain ·
        M = Mixer/CoinJoin · A = ML anomaly · T = Taint propagation. Expand
        &quot;Evidence&quot; to view full explainability JSON from the detection
        engine.
      </div>
    </main>
  );
}
