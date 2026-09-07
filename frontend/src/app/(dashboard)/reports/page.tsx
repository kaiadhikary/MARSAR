"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  fetchRankedAlerts,
  generateStrHtml,
  generateStrMarkdown,
} from "@/lib/api";
import { formatTimestamp, riskColor } from "@/lib/graph-utils";

export default function ReportsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedTxid, setSelectedTxid] = useState("");
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [reportMeta, setReportMeta] = useState<{
    filename: string;
    hash: string;
    dossier_id: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAlerts = useCallback(async () => {
    try {
      const res = await fetchRankedAlerts(50);
      const txAlerts = res.alerts.filter((a) => a.target_type === "txid");
      setAlerts(txAlerts);
      if (txAlerts.length > 0 && !selectedTxid) {
        setSelectedTxid(txAlerts[0].target_identifier);
      }
    } catch {
      setError("Failed to load transaction alerts for report generation.");
    }
  }, [selectedTxid]);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  async function handleGenerate() {
    if (!selectedTxid) return;
    setLoading(true);
    setError(null);
    setMarkdown(null);
    setReportMeta(null);
    try {
      const [md, html] = await Promise.all([
        generateStrMarkdown(selectedTxid),
        generateStrHtml(selectedTxid),
      ]);
      setMarkdown(md.report_markdown);
      setReportMeta({
        filename: html.filename,
        hash: html.chain_of_custody_hash,
        dossier_id: html.dossier_id,
      });
    } catch {
      setError(
        "Report generation failed. Ensure the TXID exists in the ingested dataset."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">
          Suspicious Transaction Reports
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-400">
          Generate offline STR dossiers with tamper-evident chain-of-custody
          hashing. Reports combine network telemetry, blockchain flows, entity
          clusters, ML attribution, and taint evidence.
        </p>
      </header>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-100">
            Generate STR
          </h3>
          <label className="mb-2 block text-xs text-slate-400">
            Select flagged transaction (TXID)
          </label>
          <select
            value={selectedTxid}
            onChange={(e) => setSelectedTxid(e.target.value)}
            className="mb-4 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-200"
          >
            {alerts.length === 0 && (
              <option value="">No TXID alerts available</option>
            )}
            {alerts.map((a) => (
              <option key={a.alert_id} value={a.target_identifier}>
                {a.target_identifier.slice(0, 20)}… — risk{" "}
                {(a.risk_score * 100).toFixed(0)}%
              </option>
            ))}
          </select>
          <button
            onClick={handleGenerate}
            disabled={!selectedTxid || loading}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
          >
            {loading ? "Generating…" : "Generate HTML + Markdown STR"}
          </button>
          {reportMeta && (
            <dl className="mt-4 space-y-1 text-xs">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">File</dt>
                <dd className="font-mono text-slate-300">{reportMeta.filename}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Dossier ID</dt>
                <dd className="font-mono text-slate-300">{reportMeta.dossier_id}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Chain-of-custody hash</dt>
                <dd className="truncate font-mono text-[10px] text-emerald-400">
                  {reportMeta.hash}
                </dd>
              </div>
            </dl>
          )}
        </div>

        <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-100">
            Flagged Transactions
          </h3>
          {alerts.length === 0 ? (
            <p className="text-xs text-slate-500">
              Run the detection pipeline to populate TXID alerts first.
            </p>
          ) : (
            <ul className="max-h-64 space-y-2 overflow-auto">
              {alerts.map((a) => (
                <li
                  key={a.alert_id}
                  className="cursor-pointer rounded-md border border-slate-800 p-2 text-xs hover:border-slate-600"
                  onClick={() => setSelectedTxid(a.target_identifier)}
                >
                  <p className="truncate font-mono text-slate-300">
                    {a.target_identifier}
                  </p>
                  <p className="mt-1 text-slate-500">
                    {a.primary_focus_area} ·{" "}
                    <span className={riskColor(a.risk_score)}>
                      {(a.risk_score * 100).toFixed(1)}% risk
                    </span>
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {markdown && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Report Preview (Markdown)
          </h2>
          <pre className="max-h-[480px] overflow-auto rounded-lg border border-slate-700 bg-slate-950 p-4 font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap">
            {markdown}
          </pre>
        </section>
      )}
    </main>
  );
}
