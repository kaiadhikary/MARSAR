"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Download, RefreshCw } from "lucide-react";
import { SearchBar } from "@/components/layout/search-bar";
import { RiskBadge } from "@/components/ui/risk-badge";
import { Identifier } from "@/components/ui/identifier";
import { investigationHistory, type HistoryItem } from "@/lib/history";
import { api } from "@/lib/api";
import type { MarsarAlert, TransactionRow } from "@/lib/types";
import { formatBtc, formatScore100, relativeTime } from "@/lib/cn";
import { Button } from "@/components/ui/button";
import { DataTable, TableRow, Td } from "@/components/ui/data-table";
import { SkeletonRows } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";

const PAGE_SIZE = 12;
type TransferFilter = "all" | "high" | "flagged";

export default function HomePage() {
  const router = useRouter();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [alerts, setAlerts] = useState<MarsarAlert[]>([]);
  const [transactions, setTransactions] = useState<TransactionRow[]>([]);
  const [offline, setOffline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [txPage, setTxPage] = useState(0);
  const [filter, setFilter] = useState<TransferFilter>("all");

  function loadLive() {
    setLoading(true);
    Promise.all([api.health(), api.alerts(40), api.transactions()]).then(([healthRes, alertRes, txRes]) => {
      const apiDown = healthRes.source === "offline" || healthRes.error === "unavailable";
      setOffline(apiDown);
      setAlerts(alertRes.data?.alerts || []);
      setTransactions(txRes.data?.transactions || []);
      setLoading(false);
    });
  }

  useEffect(() => {
    const loadHistory = () => setHistory(investigationHistory.list());
    loadHistory();
    window.addEventListener("marsar:history", loadHistory);
    loadLive();
    return () => window.removeEventListener("marsar:history", loadHistory);
  }, []);

  const filteredTx = useMemo(() => {
    return transactions.filter((t) => {
      if (filter === "high") return (t.risk_score ?? 0) >= 0.7 || (t.risk_score ?? 0) >= 70;
      if (filter === "flagged") return Boolean(t.alert_id);
      return true;
    });
  }, [transactions, filter]);

  const txPages = Math.max(1, Math.ceil(filteredTx.length / PAGE_SIZE));
  const pageRows = filteredTx.slice(txPage * PAGE_SIZE, txPage * PAGE_SIZE + PAGE_SIZE);

  useEffect(() => {
    setTxPage(0);
  }, [filter]);

  return (
    <div className="mx-auto max-w-[1280px] pt-4">
      <h1 className="text-center text-[20px] font-bold uppercase tracking-[0.34em] sm:text-[22px]">MARSAR</h1>
      <div className="mt-4">
        <SearchBar />
      </div>
      {offline && (
        <p className="mt-3 text-center text-[13px] text-warning">Backend unreachable · investigation corpus unavailable</p>
      )}

      <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.28fr)]">
        <section className="min-w-0 space-y-6">
          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-[16px] font-semibold tracking-tight">Top alerts</h2>
              <Link href="/alerts" className="text-[13px] text-ink-muted hover:text-ink">
                Open alerts
              </Link>
            </div>
            <div className="panel overflow-hidden rounded-xl">
              {loading ? (
                <SkeletonRows rows={6} />
              ) : !alerts.length ? (
                <p className="px-4 py-8 text-center text-[13px] text-ink-muted">No ranked alerts in the local corpus.</p>
              ) : (
                alerts.slice(0, 8).map((a) => (
                  <Link
                    key={a.alert_id}
                    href={
                      a.target_type === "wallet"
                        ? `/address/${encodeURIComponent(a.target_identifier)}`
                        : `/tx/${encodeURIComponent(a.target_identifier)}`
                    }
                    className="flex items-center justify-between gap-3 border-b border-white/[0.04] px-4 py-2.5 last:border-0 hover:bg-white/[0.03]"
                  >
                    <div className="min-w-0">
                      <p className="text-[11px] tracking-[0.12em] text-ink-faint">{(a.primary_focus_area || a.target_type).toUpperCase()}</p>
                      <Identifier value={a.target_identifier} copy={false} />
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <RiskBadge score={a.risk_score} />
                      <span className="hidden font-mono text-[11px] tabular-nums text-ink-muted sm:inline">{formatScore100(a.risk_score)}</span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>

          <div>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-[16px] font-semibold tracking-tight">Recent investigations</h2>
              <Link href="/explorer" className="text-[13px] text-ink-muted hover:text-ink">
                Open explorer
              </Link>
            </div>
            <div className="panel overflow-hidden rounded-xl">
              {!history.length ? (
                <p className="px-4 py-6 text-center text-[13px] text-ink-muted">Search a transaction or address to start a case file.</p>
              ) : (
                history.slice(0, 6).map((item) => (
                  <Link
                    key={`${item.kind}-${item.id}-${item.at}`}
                    href={item.href}
                    className="flex items-center justify-between gap-3 border-b border-white/[0.04] px-4 py-2.5 last:border-0 hover:bg-white/[0.03]"
                  >
                    <div className="min-w-0">
                      <p className="text-[11px] tracking-[0.12em] text-ink-faint">{item.kind.toUpperCase()}</p>
                      <Identifier value={item.label} copy={false} />
                    </div>
                    <span className="hidden font-mono text-[11px] text-ink-faint sm:inline">{relativeTime(item.at)}</span>
                  </Link>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-[16px] font-semibold tracking-tight">All transfers</h2>
            <div className="flex items-center gap-1">
              <Button type="button" variant="ghost" size="icon" className="h-8 w-8" onClick={loadLive} aria-label="Refresh transfers">
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
              <span className="px-1 font-mono text-[11px] text-ink-faint">
                {filteredTx.length ? txPage + 1 : 0} / {filteredTx.length ? txPages : 0}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                disabled={txPage <= 0}
                onClick={() => setTxPage((p) => Math.max(0, p - 1))}
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                disabled={txPage >= txPages - 1}
                onClick={() => setTxPage((p) => Math.min(txPages - 1, p + 1))}
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Link href="/explorer" className="inline-flex h-8 w-8 items-center justify-center text-ink-muted hover:text-ink" aria-label="Open explorer">
                <Download className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
          <div className="mb-3 flex flex-wrap gap-1">
            {(
              [
                ["all", "All"],
                ["high", "High risk"],
                ["flagged", "Flagged"],
              ] as const
            ).map(([id, label]) => (
              <Button key={id} type="button" size="sm" variant={filter === id ? "secondary" : "outline"} onClick={() => setFilter(id)}>
                {label}
              </Button>
            ))}
          </div>
          <div className="panel overflow-hidden rounded-xl">
            {loading ? (
              <SkeletonRows rows={10} />
            ) : !pageRows.length ? (
              <EmptyState title="NO TRANSFERS" description="No transactions in the ingested corpus match this filter." />
            ) : (
              <DataTable columns={["Time", "From", "To", "Value", "Pattern", "Risk"]}>
                {pageRows.map((t) => (
                  <TableRow
                    key={t.txid}
                    onClick={() => {
                      investigationHistory.push({
                        id: t.txid,
                        kind: "transaction",
                        label: t.txid,
                        href: `/tx/${encodeURIComponent(t.txid)}`,
                        risk: t.risk_score,
                      });
                      router.push(`/tx/${encodeURIComponent(t.txid)}`);
                    }}
                  >
                    <Td mono>{t.timestamp ? relativeTime(t.timestamp) : "Now"}</Td>
                    <Td>
                      <Identifier value={t.src_ip || t.txid} head={6} tail={3} />
                    </Td>
                    <Td>
                      <Identifier value={t.dst_ip || t.country || ""} head={6} tail={3} />
                    </Td>
                    <Td mono>{t.amount ? formatBtc(t.amount) : "—"}</Td>
                    <Td>{t.typology || "—"}</Td>
                    <Td>
                      <div className="flex items-center gap-2">
                        <RiskBadge score={t.risk_score} />
                        <span className="font-mono text-[11px] tabular-nums">{t.risk_score != null ? formatScore100(t.risk_score) : "—"}</span>
                      </div>
                    </Td>
                  </TableRow>
                ))}
              </DataTable>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
