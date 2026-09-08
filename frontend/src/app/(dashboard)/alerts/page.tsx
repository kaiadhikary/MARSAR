"use client";

import { useEffect, useState } from "react";
import { FlaggedTransaction, fetchFlaggedTransactions } from "@/lib/api";

export default function AlertsPage() {
  const [flagged, setFlagged] = useState<FlaggedTransaction[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchFlaggedTransactions(100)
      .then(setFlagged)
      .catch(() => setError("Could not load flagged transactions from the API."));
  }, []);

  return (
    <main className="p-6">
      <h1 className="mb-2 text-xl font-semibold">Flagged transactions</h1>
      <p className="mb-6 max-w-2xl text-sm text-slate-400">
        Engine 5 marks each ingested TX as LICIT, SUSPICIOUS, or HIGH_RISK.
        SUSPICIOUS and HIGH_RISK rows are copied into{" "}
        <code className="rounded bg-slate-800 px-1">flagged_transactions</code>.
      </p>

      {error && <p className="mb-4 text-sm text-red-400">{error}</p>}

      {flagged.length === 0 && !error ? (
        <p className="text-sm text-slate-500">No flagged transactions stored yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-2 pr-3">Verdict</th>
                <th className="py-2 pr-3">Score</th>
                <th className="py-2 pr-3">TXID</th>
                <th className="py-2 pr-3">Flags</th>
                <th className="py-2">Flagged at</th>
              </tr>
            </thead>
            <tbody>
              {flagged.map((tx) => (
                <tr key={tx.txid} className="border-t border-slate-800">
                  <td className="py-2 pr-3 font-semibold">{tx.risk_verdict}</td>
                  <td className="py-2 pr-3">{tx.risk_score}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{tx.txid}</td>
                  <td className="py-2 pr-3 text-xs text-slate-400">{tx.flags || "—"}</td>
                  <td className="py-2 text-xs text-slate-400">{tx.flagged_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
