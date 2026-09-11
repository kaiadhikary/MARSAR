"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { TransactionRow } from "@/lib/types";
import { formatBtc, relativeTime } from "@/lib/cn";
import { RiskBadge } from "@/components/ui/risk-badge";
import { DataTable, TableRow, Td } from "@/components/ui/data-table";
import { SkeletonRows } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { Identifier } from "@/components/ui/identifier";
import { investigationHistory } from "@/lib/history";

export default function ExplorerPage() {
  return (
    <Suspense fallback={<SkeletonRows />}>
      <ExplorerTable />
    </Suspense>
  );
}

function ExplorerTable() {
  const router = useRouter();
  const params = useSearchParams();
  const initial = params.get("q") || "";
  const [rows, setRows] = useState<TransactionRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState(initial);

  useEffect(() => {
    api.transactions().then((r) => {
      if (!r.data) setError(r.error === "unavailable" ? "unavailable" : "failed");
      setRows(r.data?.transactions || []);
    });
  }, []);

  const filtered = useMemo(() => {
    if (!rows) return [];
    const s = q.trim().toLowerCase();
    if (!s) return rows;
    return rows.filter(
      (t) =>
        t.txid.toLowerCase().includes(s) ||
        (t.typology || "").toLowerCase().includes(s) ||
        t.src_ip.toLowerCase().includes(s)
    );
  }, [rows, q]);

  if (rows === null) {
    return (
      <div>
        <Header q={q} setQ={setQ} />
        <div className="panel mt-4 rounded-md">
          <SkeletonRows />
        </div>
      </div>
    );
  }

  if (error === "unavailable") {
    return (
      <EmptyState
        title="CORPUS UNAVAILABLE"
        description="The transaction index could not be reached. Start the local MARSAR API and retry."
      />
    );
  }

  return (
    <div>
      <Header q={q} setQ={setQ} />
      <div className="panel mt-4 overflow-hidden rounded-md">
        {!filtered.length ? (
          <EmptyState title="NO MATCHING TRANSACTIONS" description="No records in the ingested corpus match this filter." />
        ) : (
          <DataTable columns={["Risk", "Transaction", "Time", "From", "To", "Amount", "Fee", "Block", "Pattern"]}>
            {filtered.map((t) => (
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
                <Td>
                  <RiskBadge score={t.risk_score} />
                </Td>
                <Td>
                  <Identifier value={t.txid} />
                </Td>
                <Td mono>{t.timestamp ? relativeTime(t.timestamp) : "—"}</Td>
                <Td mono>{t.src_ip || "—"}</Td>
                <Td mono>{t.dst_ip || "—"}</Td>
                <Td mono>{t.amount ? formatBtc(t.amount) : "—"}</Td>
                <Td mono>{t.fee || "—"}</Td>
                <Td mono>—</Td>
                <Td>{t.typology || "—"}</Td>
              </TableRow>
            ))}
          </DataTable>
        )}
      </div>
    </div>
  );
}

function Header({ q, setQ }: { q: string; setQ: (v: string) => void }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-[15px] font-medium tracking-tight">Explorer</h2>
        <p className="mt-1 text-[12px] text-ink-muted">Dense transaction index from the local forensic corpus.</p>
      </div>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Filter TXID / typology"
        className="h-8 w-full max-w-xs rounded-sm border border-white/[0.08] bg-transparent px-2 font-mono text-[12px] outline-none focus:border-accent/40"
      />
    </div>
  );
}
