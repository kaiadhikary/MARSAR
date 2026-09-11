"use client";

import { formatScore100 } from "@/lib/cn";
import { riskBand } from "@/lib/risk";
import { RiskBadge } from "@/components/ui/risk-badge";
import { NumberTicker } from "@/components/magic/number-ticker";
import { cn } from "@/lib/cn";

export function RiskScore({ score, size = "md" }: { score?: number | null; size?: "sm" | "md" | "lg" }) {
  const value = formatScore100(score);
  const band = riskBand(score);
  return (
    <div className="flex items-end gap-3">
      <div className={cn("font-medium tracking-tight tabular-nums", size === "lg" ? "text-4xl" : size === "md" ? "text-2xl" : "text-lg")}>
        <NumberTicker value={value} />
        <span className="ml-1 text-sm text-ink-muted">/ 100</span>
      </div>
      <div className="mb-1">
        <RiskBadge band={band} />
      </div>
    </div>
  );
}

export function RiskBar({ label, value }: { label: string; value?: number | null }) {
  if (value === undefined || value === null) {
    return (
      <div className="flex items-center justify-between text-[11px] text-ink-muted">
        <span>{label}</span>
        <span className="font-mono text-ink-faint">Unavailable</span>
      </div>
    );
  }
  const pct = value <= 1 ? value * 100 : value;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[11px] text-ink-muted">
        <span>{label}</span>
        <span className="font-mono tabular-nums text-ink">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-[3px] overflow-hidden bg-white/[0.06]">
        <div
          className="origin-left h-full bg-gradient-to-r from-accent/30 to-accent transition-transform duration-200 ease-out"
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  );
}
