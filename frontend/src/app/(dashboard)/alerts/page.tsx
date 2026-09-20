"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { MarsarAlert } from "@/lib/types";
import { formatScore100, relativeTime } from "@/lib/cn";
import { alertMatchesFocus, riskBand, typologyFromFlags } from "@/lib/risk";
import { AlertDrawer } from "@/components/alerts/alert-drawer";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/ui/risk-badge";
import { Identifier } from "@/components/ui/identifier";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/loading-state";
import { cn } from "@/lib/cn";

const SEVERITY = ["All", "Critical", "High", "Medium", "Low"] as const;
const FOCUS = ["All", "ML", "Taint", "Anomaly", "Peeling", "CoinJoin", "Network"] as const;

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<MarsarAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [sev, setSev] = useState<(typeof SEVERITY)[number]>("All");
  const [focus, setFocus] = useState<(typeof FOCUS)[number]>("All");
  const [selected, setSelected] = useState<MarsarAlert | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    api.alertSummary().then((r) => {
      if (r.data?.counts) setCounts(r.data.counts);
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.alerts(5000, focus).then((r) => {
      if (cancelled) return;
      if (!r.data) setError(r.error || "failed");
      else setError(null);
      setAlerts(r.data?.alerts || []);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [focus]);

  const rows = useMemo(() => {
    return alerts.filter((a) => {
      const band = riskBand(a.risk_score);
      if (sev !== "All" && band !== sev.toLowerCase()) return false;
      return alertMatchesFocus(a, focus);
    });
  }, [alerts, sev, focus]);

  const severityCounts = useMemo(() => {
    const next = { All: alerts.length, Critical: 0, High: 0, Medium: 0, Low: 0 };
    for (const a of alerts) {
      const band = riskBand(a.risk_score);
      if (band === "critical") next.Critical += 1;
      else if (band === "high") next.High += 1;
      else if (band === "medium") next.Medium += 1;
      else next.Low += 1;
    }
    return next;
  }, [alerts]);

  function focusCount(label: (typeof FOCUS)[number]) {
    if (label === "All") return counts.all ?? alerts.length;
    return counts[label.toLowerCase()];
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[15px] font-medium tracking-tight">Alerts</h2>
        <p className="mt-1 text-[12px] text-ink-muted">Ranked forensic findings from the local scoring pass.</p>
      </div>
      <div className="flex flex-wrap gap-1">
        {SEVERITY.map((f) => (
          <Button
            key={f}
            size="sm"
            variant={sev === f ? "secondary" : "outline"}
            onClick={() => setSev(f)}
            className={cn(sev === f && "border-white/20")}
          >
            {f}
            <span className="font-mono text-[10px] text-ink-faint">{severityCounts[f]}</span>
          </Button>
        ))}
      </div>
      <div className="flex flex-wrap gap-1">
        {FOCUS.map((f) => (
          <Button
            key={f}
            size="sm"
            variant={focus === f ? "secondary" : "outline"}
            onClick={() => setFocus(f)}
            className={cn("text-ink", focus === f && "border-white/20")}
          >
            {f}
            {focusCount(f) != null && (
              <span className="font-mono text-[10px] text-ink-faint">{focusCount(f)}</span>
            )}
          </Button>
        ))}
      </div>
      <div className="panel rounded-md">
        {loading && !alerts.length ? (
          <SkeletonRows />
        ) : !rows.length ? (
          <EmptyState
            title={sev !== "All" ? `NO ${sev.toUpperCase()} ALERTS` : "NO MATCHING ALERTS"}
            description={
              sev !== "All"
                ? `No ${sev.toLowerCase()}-severity findings in the ${focus === "All" ? "current" : focus} set. Composite scores on this corpus mostly land in Medium/Low.`
                : `No alerts currently match the ${focus} engine filter.`
            }
          />
        ) : (
          rows.map((a, i) => (
            <button
              key={a.alert_id}
              type="button"
              onClick={() => setSelected(a)}
              style={{ animationDelay: `${Math.min(i, 12) * 20}ms` }}
              className="flex w-full animate-[fade-up_180ms_ease-out] items-center justify-between gap-3 border-b border-white/[0.04] px-4 py-2.5 text-left last:border-0 hover:bg-white/[0.03]"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <RiskBadge score={a.risk_score} />
                  <Identifier value={a.target_identifier} />
                </div>
                <p className="mt-1 truncate text-[12px] text-ink-muted">
                  {typologyFromFlags(a)} · {relativeTime(a.created_at)}
                </p>
              </div>
              <span className="font-mono text-[12px] tabular-nums text-ink-muted">{formatScore100(a.risk_score)}</span>
            </button>
          ))
        )}
      </div>
      {error === "unavailable" && (
        <p className="text-[12px] text-warning">Alert service unreachable.</p>
      )}
      {selected && <AlertDrawer alert={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
