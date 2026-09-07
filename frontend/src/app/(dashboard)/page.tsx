"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  fetchHealth,
  fetchRankedAlerts,
  fetchSystemStatus,
  HealthResponse,
  SystemStatus,
} from "@/lib/api";
import AlertsTable from "@/components/widgets/AlertsTable";
import FileIngestPanel from "@/components/widgets/FileIngestPanel";
import StatCard from "@/components/widgets/StatCard";

const ML_FOCUS_AREAS = [
  {
    area: "Gradient Boosting Classifier",
    use: "Illicit transaction probability from 13 forensic feature vectors",
    explain: "Feature importance attribution (top contributing dimensions)",
  },
  {
    area: "Isolation Forest",
    use: "Statistical anomaly detection on transaction behaviour",
    explain: "Anomaly score surfaced per alert with deviation context",
  },
  {
    area: "CIOH + IP Co-location",
    use: "Entity clustering — link wallets sharing inputs or network peers",
    explain: "Cluster ID, member count, primary IP in graph view",
  },
  {
    area: "Peeling Chain / CoinJoin",
    use: "Laundering topology detection (layering & mixing patterns)",
    explain: "Topology flags with structural evidence in alert dossier",
  },
  {
    area: "Taint Propagation",
    use: "Decay-weighted flow from illicit seed addresses",
    explain: "Propagated taint score with hop depth in compliance screen",
  },
];

export default function CommandCenterPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [topAlerts, setTopAlerts] = useState<Alert[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [h, s, alerts] = await Promise.all([
        fetchHealth(),
        fetchSystemStatus(),
        fetchRankedAlerts(5),
      ]);
      setHealth(h);
      setStatus(s);
      setTopAlerts(alerts.alerts);
      setError(null);
    } catch {
      setError(
        "Cannot reach backend at localhost:8000. Start with: uvicorn app.main:app --port 8000"
      );
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const counts = health?.record_counts;

  return (
    <main className="p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Command Center</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-400">
          Offline Bitcoin forensic system — ingest bulk P2P/transaction metadata,
          correlate network-layer observations with blockchain flows, apply
          AI/ML detection, and review prioritized explainable investigative
          leads.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Transactions"
          value={counts?.transactions ?? "—"}
          sub="Blockchain + network records"
          accent="blue"
        />
        <StatCard
          label="Entity Clusters"
          value={counts?.unique_entity_clusters ?? "—"}
          sub="CIOH + IP co-location"
          accent="violet"
        />
        <StatCard
          label="Investigative Alerts"
          value={counts?.investigative_alerts ?? "—"}
          sub="Ranked explainable leads"
          accent="amber"
        />
        <StatCard
          label="Watchlist Seeds"
          value={counts?.watchlist_seeds ?? "—"}
          sub="OFAC / darknet / mixer seeds"
          accent="red"
        />
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <FileIngestPanel onComplete={refresh} />

        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-100">
            System Status
          </h3>
          <dl className="space-y-2 text-xs">
            <Row label="System" value={status?.system ?? "—"} />
            <Row label="Version" value={status?.version ?? "—"} />
            <Row label="Mode" value={status?.mode ?? "—"} />
            <Row
              label="Database"
              value={
                status?.database_connected ? "Connected (SQLite WAL)" : "—"
              }
            />
            <Row label="Storage" value={health?.storage_mode ?? "—"} />
          </dl>
          <div className="mt-4 flex gap-2">
            <Link
              href="/investigator"
              className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium hover:bg-blue-500"
            >
              Open Link Analysis →
            </Link>
            <Link
              href="/alerts"
              className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
            >
              View All Alerts
            </Link>
          </div>
        </div>
      </div>

      <section className="mb-6">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
          AI / ML Detection Stack
        </h2>
        <div className="overflow-hidden rounded-lg border border-slate-700">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-700 bg-slate-900/80 text-slate-400">
              <tr>
                <th className="px-4 py-2.5">Focus Area</th>
                <th className="px-4 py-2.5">Detection Use</th>
                <th className="px-4 py-2.5">Explainability</th>
              </tr>
            </thead>
            <tbody>
              {ML_FOCUS_AREAS.map((row) => (
                <tr
                  key={row.area}
                  className="border-b border-slate-800 text-slate-300"
                >
                  <td className="px-4 py-2.5 font-medium text-slate-200">
                    {row.area}
                  </td>
                  <td className="px-4 py-2.5">{row.use}</td>
                  <td className="px-4 py-2.5 text-slate-400">{row.explain}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Top Investigative Leads
          </h2>
          <Link href="/alerts" className="text-xs text-blue-400 hover:text-blue-300">
            View all →
          </Link>
        </div>
        <AlertsTable
          alerts={topAlerts}
          expandedId={expandedId}
          onToggle={(id) =>
            setExpandedId((prev) => (prev === id ? null : id))
          }
        />
      </section>
    </main>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right text-slate-300">{value}</dd>
    </div>
  );
}
