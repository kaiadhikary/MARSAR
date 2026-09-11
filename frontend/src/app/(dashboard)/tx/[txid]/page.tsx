"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { MarsarAlert, TraceTx } from "@/lib/types";
import { evidenceFromAlert } from "@/lib/evidence";
import { investigationHistory } from "@/lib/history";
import { TxOverview } from "@/components/investigation/tx-overview";
import { RiskPanel } from "@/components/investigation/risk-panel";
import { WhyFlagged } from "@/components/investigation/why-flagged";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import { Identifier } from "@/components/ui/identifier";
import { RiskBadge } from "@/components/ui/risk-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Button } from "@/components/ui/button";
import { ShimmerButton } from "@/components/magic/shimmer-button";
import { formatScore100 } from "@/lib/cn";
import { cn } from "@/lib/cn";

const TABS = ["Overview", "Transfers", "Graph", "Risk", "Evidence", "Network"] as const;

export default function TransactionPage() {
  return (
    <Suspense fallback={<LoadingState label="RESOLVING TRANSACTION" />}>
      <TxWorkspace />
    </Suspense>
  );
}

function TxWorkspace() {
  const { txid } = useParams<{ txid: string }>();
  const router = useRouter();
  const id = decodeURIComponent(txid);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  const [tx, setTx] = useState<TraceTx | null>(null);
  const [alert, setAlert] = useState<MarsarAlert | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [graph, setGraph] = useState<{ nodes: { data: Record<string, unknown> }[]; edges: { data: Record<string, unknown> }[] } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setTx(null);
    Promise.all([api.traceTx(id), api.alerts(120), api.graph(80)]).then(([trace, alerts, g]) => {
      if (cancelled) return;
      if (!trace.data) {
        setError(trace.error === "not_found" ? "not_found" : "unavailable");
        return;
      }
      setTx(trace.data);
      investigationHistory.push({
        id,
        kind: "transaction",
        label: id,
        href: `/tx/${encodeURIComponent(id)}`,
      });
      const match = alerts.data?.alerts.find((a) => a.target_identifier === id) || null;
      setAlert(match);
      if (g.data) {
        const ids = new Set([id, ...trace.data.inputs.map((i) => i.address || ""), ...trace.data.outputs.map((o) => o.address || "")]);
        setGraph({
          nodes: g.data.elements.nodes.filter((n) => ids.has(String(n.data.id))),
          edges: g.data.elements.edges.filter((e) => ids.has(String(e.data.source)) || ids.has(String(e.data.target))),
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const evidence = useMemo(() => evidenceFromAlert(alert), [alert]);

  async function generate() {
    try {
      const report = await api.exportStrReport(id);
      const prev = JSON.parse(localStorage.getItem("marsar.reports") || "[]");
      localStorage.setItem(
        "marsar.reports",
        JSON.stringify(
          [
            {
              filename: report.filename,
              chain_of_custody_hash: report.chain_of_custody_hash,
              dossier_id: report.dossier_id,
              report_path: report.report_path,
              txid: id,
              at: Date.now(),
            },
            ...prev,
          ].slice(0, 40)
        )
      );
      toast.success("STR generated", { description: report.chain_of_custody_hash.slice(0, 24) });
      router.push("/reports");
    } catch {
      toast.message("Report generation failed — transaction may not be in the evidence store.");
    }
  }

  if (error === "not_found") {
    return (
      <EmptyState
        title="TRANSACTION NOT FOUND"
        description="The supplied transaction could not be resolved in the available dataset."
        action={
          <Button onClick={() => router.push("/explorer")}>Try another transaction</Button>
        }
      />
    );
  }
  if (error === "unavailable") {
    return <EmptyState title="CORPUS UNAVAILABLE" description="The tracing service could not be reached." />;
  }
  if (!tx) return <LoadingState label="RESOLVING TRANSACTION" detail="Loading hop context..." />;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Transaction</p>
          <div className="mt-1">
            <Identifier value={tx.txid} head={16} tail={10} className="text-[15px]" />
          </div>
        </div>
        <div className="flex items-center gap-4">
          {alert ? (
            <>
              <RiskBadge score={alert.risk_score} />
              <span className="font-mono text-[18px] tabular-nums">{formatScore100(alert.risk_score)} / 100</span>
            </>
          ) : (
            <span className="text-[12px] text-ink-faint">Unscored</span>
          )}
          <Button asChild size="sm" variant="outline">
            <Link href={`/visualizer?q=${encodeURIComponent(id)}`}>Open graph</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link href={`/tracer?q=${encodeURIComponent(id)}`}>Trace funds</Link>
          </Button>
          <ShimmerButton onClick={generate}>Generate STR</ShimmerButton>
        </div>
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-white/[0.06]">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn(
              "px-3 py-2 text-[12px] text-ink-muted transition-colors duration-150",
              tab === t && "border-b border-accent text-ink"
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview" && (
        <div className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
          <TxOverview tx={tx} />
          <RiskPanel alert={alert} />
        </div>
      )}
      {tab === "Transfers" && <TxOverview tx={tx} />}
      {tab === "Graph" &&
        (graph?.nodes.length ? (
          <div className="h-[520px]">
            <GraphCanvas elements={graph} riskById={alert ? { [id]: alert.risk_score } : {}} />
          </div>
        ) : (
          <EmptyState title="NO GRAPH CONTEXT" description="Not enough topology is available for this transaction." />
        ))}
      {tab === "Risk" && <RiskPanel alert={alert} />}
      {tab === "Evidence" && <WhyFlagged items={evidence} />}
      {tab === "Network" && (
        <div className="panel rounded-md p-4 text-[12px]">
          <p className="font-mono">{tx.network.src_ip || "Unavailable"}</p>
          <p className="mt-2 text-ink-muted">
            {tx.network.country || "—"} · {tx.network.asn || "—"}
          </p>
          <Button asChild className="mt-4" size="sm">
            <Link href="/network">Open network intelligence</Link>
          </Button>
        </div>
      )}
    </div>
  );
}
