"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  ExportIntegrity,
  FlaggedTransaction,
  PersistedTransaction,
  exportStrReport,
  fetchReportableTransactions,
} from "@/lib/api";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const [txid, setTxid] = useState("");
  const [caseId, setCaseId] = useState("");
  const [note, setNote] = useState("");
  const [recent, setRecent] = useState<PersistedTransaction[]>([]);
  const [flagged, setFlagged] = useState<FlaggedTransaction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [integrity, setIntegrity] = useState<ExportIntegrity | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  useEffect(() => {
    fetchReportableTransactions(40)
      .then((data) => {
        setRecent(data.recent || []);
        setFlagged(data.flagged || []);
        setListError(null);
      })
      .catch(() => {
        setRecent([]);
        setFlagged([]);
        setListError("Cannot load transactions — FastAPI is not running on port 8000.");
      });
  }, []);

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  async function handleExport(e: FormEvent) {
    e.preventDefault();
    if (!txid.trim()) return;
    setLoading(true);
    setError(null);
    setIntegrity(null);
    try {
      const { blob, integrity: meta } = await exportStrReport({
        txid: txid.trim(),
        case_id: caseId.trim() || undefined,
        investigator_note: note.trim() || undefined,
      });
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      setPdfUrl(URL.createObjectURL(blob));
      setIntegrity(meta);
      downloadBlob(blob, `MARSAR-STR-${txid.trim().slice(0, 16)}.html`);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (!status) {
        setError("Cannot reach the API on http://localhost:8000. Start FastAPI (uvicorn) and try again.");
      } else if (status === 404) {
        setError("Transaction not found in SQLite. Ingest it with the worker first.");
      } else if (status === 400) {
        setError("Invalid TXID.");
      } else {
        setError(`Report generation failed (HTTP ${status}).`);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-6">
      <h1 className="mb-2 text-xl font-semibold">Reports</h1>
      <p className="mb-6 max-w-2xl text-sm text-slate-400">
        Enter a persisted TXID to generate an HTML forensic dossier. No PDF, GTK, or WeasyPrint is required.
      </p>

      <form onSubmit={handleExport} className="mb-6 max-w-2xl space-y-3">
        <label className="block text-sm">
          TXID
          <input
            value={txid}
            onChange={(e) => setTxid(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-sm"
            placeholder="64-character transaction id"
          />
        </label>
        <label className="block text-sm">
          Case / investigation ID (optional)
          <input
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          Investigator note (optional)
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            rows={3}
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium hover:bg-blue-500 disabled:opacity-50"
        >
          {loading ? "Generating…" : "Generate HTML dossier"}
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}
      {listError && <p className="mb-4 text-sm text-amber-400">{listError}</p>}

      {integrity && (
        <div className="mb-6 max-w-2xl rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm">
          <h2 className="mb-2 font-semibold">Integrity metadata</h2>
          <dl className="grid grid-cols-[10rem_1fr] gap-2">
            <dt className="text-slate-400">TXID</dt>
            <dd className="break-all font-mono text-xs">{integrity.txid}</dd>
            <dt className="text-slate-400">Risk score</dt>
            <dd>{integrity.risk_score || "Unavailable"}</dd>
            <dt className="text-slate-400">Verdict</dt>
            <dd>{integrity.verdict || "Unavailable"}</dd>
            <dt className="text-slate-400">Evidence SHA-256</dt>
            <dd className="break-all font-mono text-xs">{integrity.evidence_sha256 || "Unavailable"}</dd>
            <dt className="text-slate-400">Generated at</dt>
            <dd>{integrity.generated_at || "Unavailable"}</dd>
          </dl>
        </div>
      )}

      {pdfUrl && (
        <iframe title="STR HTML" src={pdfUrl} className="mb-6 h-[32rem] w-full max-w-4xl rounded border border-slate-800 bg-white" />
      )}

      <section className="mb-8">
        <h2 className="mb-2 text-sm font-semibold">Flagged transactions</h2>
        <p className="mb-2 text-xs text-slate-500">
          Stored in SQLite table <code className="rounded bg-slate-800 px-1">flagged_transactions</code>
          {" "}(verdict SUSPICIOUS or HIGH_RISK).
        </p>
        {flagged.length === 0 ? (
          <p className="text-sm text-slate-500">No flagged transactions yet. Run the worker to ingest mempool activity.</p>
        ) : (
          <ul className="space-y-1 text-xs">
            {flagged.map((tx) => (
              <li key={tx.txid}>
                <button
                  type="button"
                  className="font-mono text-blue-400 hover:underline"
                  onClick={() => setTxid(tx.txid)}
                >
                  {tx.txid}
                </button>
                <span className="ml-2 text-slate-500">
                  {tx.risk_verdict} · {tx.risk_score}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {recent.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold">Recent persisted transactions</h2>
          <ul className="space-y-1 text-xs">
            {recent.map((tx) => (
              <li key={tx.txid}>
                <button
                  type="button"
                  className="font-mono text-blue-400 hover:underline"
                  onClick={() => setTxid(tx.txid)}
                >
                  {tx.txid}
                </button>
                <span className="ml-2 text-slate-500">
                  {tx.risk_verdict} · {tx.risk_score}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
