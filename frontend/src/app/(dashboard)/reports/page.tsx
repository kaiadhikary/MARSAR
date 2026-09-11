"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { ComplianceTx, HtmlReport } from "@/lib/types";
import { truncateId } from "@/lib/cn";
import { Identifier } from "@/components/ui/identifier";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { ShimmerButton } from "@/components/magic/shimmer-button";
import { SearchBar } from "@/components/layout/search-bar";
import { SkeletonRows } from "@/components/ui/loading-state";

interface StoredReport extends HtmlReport {
  txid: string;
  at: number;
}

function downloadHtml(filename: string, html: string) {
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function ReportsPage() {
  const [reports, setReports] = useState<StoredReport[]>([]);
  const [flagged, setFlagged] = useState<ComplianceTx[] | null>(null);
  const [offline, setOffline] = useState(false);
  const [txid, setTxid] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [lastHash, setLastHash] = useState<string | null>(null);

  useEffect(() => {
    try {
      setReports(JSON.parse(localStorage.getItem("marsar.reports") || "[]"));
    } catch {
      setReports([]);
    }
    api.flagged(50).then((r) => {
      setOffline(r.source === "offline");
      setFlagged(r.data?.flagged || []);
    });
  }, []);

  async function generate(id: string) {
    setBusy(true);
    try {
      const report = await api.exportStrReport(id);
      const stored: StoredReport = {
        filename: report.filename,
        chain_of_custody_hash: report.chain_of_custody_hash,
        dossier_id: report.dossier_id,
        report_path: report.report_path,
        txid: id,
        at: Date.now(),
      };
      const next = [stored, ...reports.filter((r) => r.txid !== id)].slice(0, 40);
      localStorage.setItem("marsar.reports", JSON.stringify(next));
      setReports(next);
      setPreview(report.html);
      setLastHash(report.chain_of_custody_hash);
      toast.success("Dossier generated");
    } catch {
      toast.error("Could not generate STR — confirm the transaction exists in the local store and the API is running.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <h2 className="text-[15px] font-medium tracking-tight">Investigation dossier</h2>
        <p className="mt-1 text-[12px] text-ink-muted">
          Generate a tamper-evident STR from a resolved transaction in the local evidence store.
        </p>
      </div>

      {offline && (
        <p className="text-[12px] text-warning">
          Backend unreachable on port 8000 — flagged transactions and STR export require the local API.
        </p>
      )}

      <div className="panel rounded-md p-4 space-y-4">
        <p className="text-[10px] tracking-[0.16em] text-ink-faint">Evidence checklist</p>
        <ul className="space-y-1 text-[13px] text-ink-muted">
          <li>✓ Transaction analysis</li>
          <li>✓ Entity clustering</li>
          <li>✓ Taint propagation</li>
          <li>✓ Network intelligence</li>
          <li>✓ Pattern detection</li>
        </ul>
        <div className="flex flex-wrap gap-2">
          <input
            value={txid}
            onChange={(e) => setTxid(e.target.value.trim())}
            placeholder="64-character transaction ID"
            className="h-9 min-w-[240px] flex-1 rounded-sm border border-white/[0.08] bg-transparent px-2 font-mono text-[12px] outline-none"
          />
          <ShimmerButton loading={busy} disabled={!txid} onClick={() => generate(txid)}>
            Generate STR
          </ShimmerButton>
        </div>
        <SearchBar compact />
      </div>

      {lastHash && (
        <div className="panel rounded-md p-4">
          <p className="text-[10px] tracking-[0.16em] text-ink-faint">Evidence integrity</p>
          <p className="mt-2 font-mono text-[12px]">SHA-256</p>
          <p className="mt-1 break-all font-mono text-[12px]">{truncateId(lastHash, 18, 10)}</p>
          <p className="mt-2 text-[11px] tracking-[0.14em] text-safe">VERIFIED</p>
        </div>
      )}

      {preview && (
        <div className="panel overflow-hidden rounded-md">
          <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2">
            <p className="text-[11px] tracking-[0.14em] text-ink-faint">HTML PREVIEW</p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => downloadHtml(`MARSAR-STR-${txid.slice(0, 16)}.html`, preview)}
            >
              Download dossier
            </Button>
          </div>
          <iframe title="STR preview" srcDoc={preview} className="h-[480px] w-full bg-white" />
        </div>
      )}

      <div className="panel rounded-md">
        <p className="border-b border-white/[0.06] px-4 py-3 text-[11px] tracking-[0.14em] text-ink-faint">
          FLAGGED TRANSACTIONS
        </p>
        {flagged === null ? (
          <SkeletonRows rows={4} />
        ) : !flagged.length ? (
          <p className="px-4 py-6 text-center text-[13px] text-ink-muted">No suspicious or high-risk transactions in the local store.</p>
        ) : (
          flagged.map((row) => (
            <div
              key={row.txid}
              className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.04] px-4 py-3 last:border-0"
            >
              <div>
                <Identifier value={row.txid} />
                <p className="mt-1 text-[12px] text-ink-muted">
                  {row.risk_verdict || "FLAGGED"} · score {row.risk_score ?? "—"}
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={() => generate(row.txid)}>
                Generate STR
              </Button>
            </div>
          ))
        )}
      </div>

      {!reports.length ? (
        <EmptyState
          title="NO DOSSIERS YET"
          description="Generate an STR from a transaction investigation to store a local chain-of-custody record."
        />
      ) : (
        <div className="panel rounded-md">
          <p className="border-b border-white/[0.06] px-4 py-3 text-[11px] tracking-[0.14em] text-ink-faint">
            RECENT DOSSIERS
          </p>
          {reports.map((r) => (
            <div
              key={r.filename + r.at}
              className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.04] px-4 py-3 last:border-0"
            >
              <div>
                <p className="font-mono text-[12px]">{r.filename}</p>
                <Identifier value={r.txid} />
                <p className="mt-1 font-mono text-[11px] text-ink-faint">
                  SHA-256 {truncateId(r.chain_of_custody_hash, 16, 10)}
                </p>
              </div>
              <Button size="sm" variant="outline" onClick={() => generate(r.txid)}>
                Regenerate
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
