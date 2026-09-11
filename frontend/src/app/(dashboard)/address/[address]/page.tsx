"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { WalletTrace } from "@/lib/types";
import { Identifier } from "@/components/ui/identifier";
import { RiskBadge } from "@/components/ui/risk-badge";
import { DataTable, TableRow, Td } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { formatBtc, relativeTime } from "@/lib/cn";
import { investigationHistory } from "@/lib/history";
import { Button } from "@/components/ui/button";

export default function AddressPage() {
  const { address } = useParams<{ address: string }>();
  const router = useRouter();
  const id = decodeURIComponent(address);
  const [data, setData] = useState<WalletTrace | null>(null);
  const [risk, setRisk] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.wallet(id), api.alerts(120)]).then(([w, a]) => {
      if (!w.data) {
        setError(w.error === "not_found" ? "not_found" : w.error || "failed");
        setData(null);
        return;
      }
      setData(w.data);
      investigationHistory.push({ id, kind: "address", label: id, href: `/address/${encodeURIComponent(id)}` });
      const hit = a.data?.alerts.find((x) => x.target_identifier === id);
      setRisk(hit?.risk_score ?? null);
    });
  }, [id]);

  if (error && error !== "failed") {
    return (
      <EmptyState
        title="ADDRESS NOT FOUND"
        description="This wallet is not present in the ingested corpus."
        action={<Button onClick={() => router.push("/explorer")}>Try another identifier</Button>}
      />
    );
  }
  if (!data) return <LoadingState label="RESOLVING ADDRESS" />;

  const incoming = data.activity.filter((a) => a.role === "RECEIVER").length;
  const outgoing = data.activity.filter((a) => a.role === "SENDER").length;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Address</p>
          <Identifier value={data.wallet_address} head={16} tail={10} className="mt-1 text-[15px]" />
          <p className="mt-2 text-[12px] text-ink-muted">
            Entity{" "}
            {data.cluster_id !== "UNCLUSTERED" ? (
              <Link className="font-mono text-ink hover:underline" href={`/entity/${encodeURIComponent(data.cluster_id)}`}>
                {data.cluster_id}
              </Link>
            ) : (
              "UNCLUSTERED"
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {risk != null ? <RiskBadge score={risk} /> : <span className="text-[12px] text-ink-faint">Unscored</span>}
          <Button asChild size="sm" variant="outline">
            <Link href={`/visualizer?q=${encodeURIComponent(id)}`}>Open graph</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link href={`/tracer?q=${encodeURIComponent(id)}`}>Trace funds</Link>
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-white/[0.08] bg-white/[0.08] md:grid-cols-4">
        <Stat k="Balance" v={formatBtc(data.current_balance_btc)} />
        <Stat k="Transactions" v={String(data.transactions_count)} />
        <Stat k="Incoming" v={String(incoming)} />
        <Stat k="Outgoing" v={String(outgoing)} />
      </div>
      <div className="panel overflow-hidden rounded-md">
        <DataTable columns={["TXID", "Role", "Net", "IP", "Country", "Time"]}>
          {data.activity.map((a) => (
            <TableRow key={`${a.txid}-${a.timestamp}`} onClick={() => router.push(`/tx/${encodeURIComponent(a.txid)}`)}>
              <Td>
                <Identifier value={a.txid} />
              </Td>
              <Td>{a.role}</Td>
              <Td mono>{formatBtc(a.net_flow)}</Td>
              <Td mono>{a.ip_origin || "—"}</Td>
              <Td>{a.country || "—"}</Td>
              <Td mono>{relativeTime(a.timestamp)}</Td>
            </TableRow>
          ))}
        </DataTable>
      </div>
    </div>
  );
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div className="bg-[#08090b] px-4 py-3">
      <p className="text-[10px] tracking-[0.14em] text-ink-faint">{k}</p>
      <p className="mt-1 font-mono text-[13px]">{v}</p>
    </div>
  );
}
