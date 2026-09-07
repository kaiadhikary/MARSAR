"use client";

import { riskBg, riskColor } from "@/lib/graph-utils";

interface RiskGaugeProps {
  score: number;
  label?: string;
  size?: "sm" | "md";
}

export default function RiskGauge({
  score,
  label = "Risk Score",
  size = "md",
}: RiskGaugeProps) {
  const pct = Math.min(100, Math.max(0, score * 100));
  const barH = size === "sm" ? "h-1.5" : "h-2.5";

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-xs text-slate-400">{label}</span>
        <span className={`text-sm font-semibold ${riskColor(score)}`}>
          {(score * 100).toFixed(1)}%
        </span>
      </div>
      <div className={`w-full overflow-hidden rounded-full bg-slate-800 ${barH}`}>
        <div
          className={`${barH} rounded-full transition-all ${riskBg(score)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
