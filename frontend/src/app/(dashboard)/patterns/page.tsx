"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { MarsarAlert } from "@/lib/types";
import { patternKey } from "@/lib/risk";
import { Identifier } from "@/components/ui/identifier";
import { RiskBadge } from "@/components/ui/risk-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/loading-state";
import { NumberTicker } from "@/components/magic/number-ticker";
import { cn } from "@/lib/cn";

const TYPES = [
  { id: "peeling", label: "Peeling chains" },
  { id: "coinjoin", label: "CoinJoin-like" },
  { id: "anomaly", label: "Anomalous flows" },
  { id: "network", label: "Network correlations" },
] as const;

export default function PatternsPage() {
  return (
    <Suspense fallback={<SkeletonRows />}>
      <Patterns />
    </Suspense>
  );
}

function Patterns() {
  const params = useSearchParams();
  const router = useRouter();
  const initial = params.get("type") || "";
  const [alerts, setAlerts] = useState<MarsarAlert[] | null>(null);
  const [type, setType] = useState(initial);

  useEffect(() => {
    api.alerts(200).then((r) => setAlerts(r.data?.alerts || []));
  }, []);

  const counts = useMemo(() => {
    const list = alerts || [];
    return {
      peeling: list.filter((a) => patternKey(a.primary_focus_area, a.flags) === "peeling").length,
      coinjoin: list.filter((a) => patternKey(a.primary_focus_area, a.flags) === "coinjoin").length,
      anomaly: list.filter((a) => ["anomaly", "ml"].includes(patternKey(a.primary_focus_area, a.flags))).length,
      network: list.filter((a) => patternKey(a.primary_focus_area, a.flags) === "network").length,
    };
  }, [alerts]);

  const rows = (alerts || []).filter((a) => !type || patternKey(a.primary_focus_area, a.flags) === type || (type === "anomaly" && patternKey(a.primary_focus_area, a.flags) === "ml"));

  if (!alerts) {
    return (
      <div>
        <h2 className="text-[15px] font-medium">Pattern intelligence</h2>
        <div className="panel mt-4 rounded-md">
          <SkeletonRows />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-[15px] font-medium tracking-tight">Pattern intelligence</h2>
        <p className="mt-1 text-[12px] text-ink-muted">Detections produced by peeling, mixer, anomaly, and network engines.</p>
      </div>
      <div className="grid gap-px overflow-hidden rounded-md border border-white/[0.08] bg-white/[0.08] sm:grid-cols-2 lg:grid-cols-4">
        {TYPES.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setType(type === t.id ? "" : t.id)}
            className={cn("bg-[#08090b] px-4 py-3 text-left hover:bg-white/[0.03]", type === t.id && "bg-white/[0.04]")}
          >
            <p className="text-[10px] tracking-[0.14em] text-ink-faint">{t.label}</p>
            <p className="mt-2 font-mono text-[22px] tabular-nums">
              <NumberTicker value={counts[t.id]} />
              <span className="ml-2 text-[11px] text-ink-faint">detected</span>
            </p>
          </button>
        ))}
      </div>
      <div className="panel rounded-md">
        {!rows.length ? (
          <EmptyState title="NO PATTERN MATCHES" description="No detections of this class are present in the current corpus." />
        ) : (
          rows.map((a) => (
            <button
              key={a.alert_id}
              type="button"
              onClick={() =>
                router.push(
                  a.target_type === "wallet"
                    ? `/address/${encodeURIComponent(a.target_identifier)}`
                    : `/tx/${encodeURIComponent(a.target_identifier)}`
                )
              }
              className="flex w-full items-center justify-between gap-3 border-b border-white/[0.04] px-4 py-2.5 text-left last:border-0 hover:bg-white/[0.03]"
            >
              <div>
                <p className="text-[11px] text-ink-muted">{a.primary_focus_area}</p>
                <Identifier value={a.target_identifier} />
              </div>
              <RiskBadge score={a.risk_score} />
            </button>
          ))
        )}
      </div>
    </div>
  );
}
