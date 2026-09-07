"use client";

import { useState } from "react";
import { ingestFile, runPipeline } from "@/lib/api";

interface FileIngestPanelProps {
  onComplete?: () => void;
}

export default function FileIngestPanel({ onComplete }: FileIngestPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleIngest() {
    if (!file) return;
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const result = await ingestFile(file);
      setMessage(
        `Ingested ${result.transactions_ingested} transactions from ${result.file_processed} (${result.format}).`
      );
      onComplete?.();
    } catch {
      setError("Ingest failed. Ensure the backend is running and the file is CSV, JSON, or XML.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePipeline() {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const result = await runPipeline();
      setMessage(
        `Pipeline complete: ${result.clusters_identified} clusters, ${result.alerts_generated} alerts generated.`
      );
      onComplete?.();
    } catch {
      setError("Pipeline failed. Check backend logs and ensure data is ingested first.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-5">
      <h3 className="mb-1 text-sm font-semibold text-slate-100">
        Bulk Metadata Ingestion
      </h3>
      <p className="mb-4 text-xs text-slate-500">
        Upload synthetic CSV, JSON, or XML with timestamp, IP/port, TXID, wallet
        addresses, amounts, fees, and script types.
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <label className="cursor-pointer rounded-md border border-dashed border-slate-600 px-4 py-2 text-xs text-slate-300 hover:border-slate-500">
          {file ? file.name : "Choose file…"}
          <input
            type="file"
            accept=".csv,.json,.xml"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <button
          onClick={handleIngest}
          disabled={!file || loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-xs font-medium hover:bg-blue-500 disabled:opacity-40"
        >
          Ingest
        </button>
        <button
          onClick={handlePipeline}
          disabled={loading}
          className="rounded-md border border-slate-600 px-4 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-40"
        >
          Run Detection Pipeline
        </button>
      </div>

      {message && (
        <p className="mt-3 text-xs text-emerald-400">{message}</p>
      )}
      {error && <p className="mt-3 text-xs text-red-400">{error}</p>}
    </div>
  );
}
