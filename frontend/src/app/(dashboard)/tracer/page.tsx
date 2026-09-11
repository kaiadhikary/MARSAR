"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { MarsarAlert, TraceTx } from "@/lib/types";
import { TraceTimeline, type TraceStep } from "@/components/tracer/trace-timeline";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { SearchBar } from "@/components/layout/search-bar";
import { classifyQuery } from "@/lib/search";
import { investigationHistory } from "@/lib/history";

const HOPS = [1, 2, 3, 5] as const;

export default function TracerPage() {
  return (
    <Suspense fallback={<LoadingState label="TRACING FUNDS" />}>
      <Tracer />
    </Suspense>
  );
}

function Tracer() {
  const params = useSearchParams();
  const router = useRouter();
  const q = params.get("q") || "";
  const [hops, setHops] = useState<number>(3);
  const [steps, setSteps] = useState<TraceStep[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!q) {
      setSteps([]);
      return;
    }
    let cancelled = false;
    setSteps(null);
    setError(null);
    buildTrace(q, hops).then((result) => {
      if (cancelled) return;
      if (result.error) setError(result.error);
      setSteps(result.steps);
      if (result.steps.length) {
        investigationHistory.push({
          id: q,
          kind: classifyQuery(q) === "address" ? "address" : "transaction",
          label: q,
          href: `/tracer?q=${encodeURIComponent(q)}`,
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [q, hops]);

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h2 className="text-[15px] font-medium tracking-tight">Trace funds</h2>
        <p className="mt-1 text-[12px] text-ink-muted">Follow observed hops in the local evidence store. Depth is bounded.</p>
      </div>
      {!q && <SearchBar />}
      {q && (
        <div className="flex flex-wrap gap-1">
          {HOPS.map((h) => (
            <Button key={h} size="sm" variant={hops === h ? "secondary" : "outline"} onClick={() => setHops(h)}>
              {h} hop{h > 1 ? "s" : ""}
            </Button>
          ))}
        </div>
      )}
      {!q && (
        <EmptyState
          title="NO INVESTIGATION SELECTED"
          description="Search a transaction or address to begin a fund-flow trace."
        />
      )}
      {q && steps === null && <LoadingState label="TRACING FUNDS" detail={`Walking ${hops} hop${hops > 1 ? "s" : ""}...`} />}
      {q && error === "not_found" && (
        <EmptyState
          title="TRANSACTION NOT FOUND"
          description="The supplied identifier could not be resolved in the available dataset."
          action={<Button onClick={() => router.push("/explorer")}>Try another transaction</Button>}
        />
      )}
      {q && steps && !steps.length && error !== "not_found" && (
        <EmptyState title="NOT ENOUGH DATA" description="No hop lineage is stored for this identifier." />
      )}
      {q && steps && steps.length > 0 && (
        <div className="panel rounded-md p-4">
          <TraceTimeline steps={steps} />
        </div>
      )}
    </div>
  );
}

async function buildTrace(q: string, maxHops: number): Promise<{ steps: TraceStep[]; error?: string }> {
  const kind = classifyQuery(q);
  const alerts = await api.alerts(200);
  const risk = (id: string) => alerts.data?.alerts.find((a) => a.target_identifier === id)?.risk_score ?? null;
  const pattern = (id: string) => alerts.data?.alerts.find((a) => a.target_identifier === id)?.primary_focus_area ?? null;

  let startTx: TraceTx | null = null;
  if (kind === "address") {
    const wallet = await api.wallet(q);
    if (!wallet.data) return { steps: [], error: wallet.error };
    const first = wallet.data.activity[0];
    if (!first) return { steps: [{ kind: "wallet", id: q, amount: wallet.data.current_balance_btc }] };
    const traced = await api.traceTx(first.txid);
    startTx = traced.data;
    if (!startTx) {
      return {
        steps: wallet.data.activity.slice(0, maxHops).map((a) => ({
          kind: "transaction",
          id: a.txid,
          amount: a.net_flow,
          timestamp: a.timestamp,
          risk: risk(a.txid),
          pattern: pattern(a.txid),
        })),
      };
    }
  } else {
    const traced = await api.traceTx(q);
    if (!traced.data) return { steps: [], error: traced.error };
    startTx = traced.data;
  }

  const steps: TraceStep[] = [];
  const seen = new Set<string>();
  let current: TraceTx | null = startTx;
  let depth = 0;
  while (current && depth < maxHops) {
    if (seen.has(current.txid)) break;
    seen.add(current.txid);
    const inAddr = current.inputs[0]?.address;
    if (inAddr && !steps.find((s) => s.id === inAddr)) {
      steps.push({ kind: "wallet", id: inAddr, amount: current.inputs[0]?.amount, timestamp: current.timestamp });
    }
    steps.push({
      kind: "transaction",
      id: current.txid,
      amount: current.total_btc,
      timestamp: current.timestamp,
      risk: risk(current.txid),
      pattern: pattern(current.txid),
    });
    const outAddr = current.outputs[0]?.address;
    if (outAddr) {
      steps.push({ kind: "wallet", id: outAddr, amount: current.outputs[0]?.amount, timestamp: current.timestamp, risk: risk(outAddr) });
    }
    const nextId = current.forward_lineage[0]?.spent_in_txid;
    if (!nextId) break;
    const next = await api.traceTx(nextId);
    current = next.data;
    depth += 1;
  }
  return { steps };
}
