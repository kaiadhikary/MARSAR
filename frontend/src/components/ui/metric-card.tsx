"use client";

import { useEffect, useState } from "react";
import { LucideIcon } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { GlassCard } from "@/components/ui/glass-card";
import { cn } from "@/lib/cn";

function useCountUp(target: number, duration = 900) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    const start = performance.now();
    let frame: number;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      setValue(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);
  return value;
}

interface MetricCardProps {
  label: string;
  value: number;
  icon: LucideIcon;
  trend?: string;
  spark?: number[];
  tone?: "violet" | "cyan" | "danger" | "warn" | "safe";
}

export function MetricCard({ label, value, icon: Icon, trend, spark = [], tone = "violet" }: MetricCardProps) {
  const n = useCountUp(value);
  const data = spark.map((v, i) => ({ i, v }));
  const stroke =
    tone === "danger" ? "#c45c5c" : tone === "warn" ? "#c9a227" : tone === "safe" ? "#3d9b74" : tone === "cyan" ? "#3ec8d4" : "#8b6cff";

  return (
    <GlassCard className="group relative overflow-hidden">
      <div
        className={cn(
          "pointer-events-none absolute -right-8 -top-10 h-24 w-24 rounded-full blur-2xl opacity-30 transition-opacity group-hover:opacity-50",
          tone === "danger" && "bg-danger",
          tone === "warn" && "bg-warning",
          tone === "safe" && "bg-safe",
          tone === "cyan" && "bg-accent-cyan",
          tone === "violet" && "bg-accent"
        )}
      />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.16em] text-ink-muted">{label}</p>
          <p className="mt-2 text-[26px] font-medium leading-none tracking-tight">{n.toLocaleString()}</p>
          {trend && <p className="mt-2 text-[11px] text-ink-faint">{trend}</p>}
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-md border border-white/[0.06] bg-white/[0.03] text-ink-muted">
          <Icon className="h-3.5 w-3.5 transition-transform duration-200 group-hover:-translate-y-0.5" />
        </div>
      </div>
      {data.length > 1 && (
        <div className="mt-3 h-10">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`spark-${tone}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke={stroke} fill={`url(#spark-${tone})`} strokeWidth={1.4} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </GlassCard>
  );
}
