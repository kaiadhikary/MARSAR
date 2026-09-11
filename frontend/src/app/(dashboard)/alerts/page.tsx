"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { MarsarAlert } from "@/lib/types";
import { formatScore100, relativeTime } from "@/lib/cn";
import { patternKey, riskBand, typologyFromFlags } from "@/lib/risk";
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
  const [alerts, setAlerts] = useState<MarsarAlert[] | null>(null);
  const [sev, setSev] = useState<(typeof SEVERITY)[number]>("All");
  const [focus, setFocus] = useState<(typeof FOCUS)[number]>("All");
  const [selected, setSelected] = useState<MarsarAlert | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.alerts(200).then((r) => {
      if (!r.data) setError(r.error || "failed");
      setAlerts(r.data?.alerts || []);
    });
  }, []);

  const rows = useMemo(() => {
    if (!alerts) return [];
    return alerts.filter((a) => {
      const band = riskBand(a.risk_score);
      if (sev !== "All" && band !== sev.toLowerCase()) return false;
      if (focus === "All") return true;
      const key = patternKey(a.primary_focus_area, a.flags);
      return key === focus.toLowerCase() || (focus === "CoinJoin" && key === "coinjoin");
    });
  }, [alerts, sev, focus]);

  if (alerts === null) {
    return (
      <div>
        <h2 className="text-[15px] font-medium">Alerts</h2>
        <div className="panel mt-4 rounded-md">
          <SkeletonRows />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[15px] font-medium tracking-tight">Alerts</h2>
        <p className="mt-1 text-[12px] text-ink-muted">Ranked forensic findings from the local scoring pass.</p>
      </div>
      <div className="flex flex-wrap gap-1">
        {SEVERITY.map((f) => (
          <Button key={f} size="sm" variant={sev === f ? "secondary" : "outline"} onClick={() => setSev(f)}>
            {f}
          </Button>
        ))}
      </div>
      <div className="flex flex-wrap gap-1">
        {FOCUS.map((f) => (
          <Button key={f} size="sm" variant={focus === f ? "secondary" : "ghost"} onClick={() => setFocus(f)}>
            {f}
          </Button>
        ))}
      </div>
      <div className="panel rounded-md">
        {!rows.length ? (
          <EmptyState
            title="NO ACTIVE ALERTS"
            description="No suspicious transactions currently match your selected filters."
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
