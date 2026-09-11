"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/ui/risk-badge";
import { Identifier } from "@/components/ui/identifier";
import { investigationHref, classifyQuery } from "@/lib/search";
import { formatScore100 } from "@/lib/cn";

export function GraphNodePanel({
  data,
  onIsolate,
}: {
  data: Record<string, unknown>;
  onIsolate?: () => void;
}) {
  const id = String(data.id || "");
  const type = String(data.type || "node");
  const score = typeof data.riskScore === "number" ? data.riskScore : null;
  const href = investigationHref(id.replace(/^ip_/, ""), classifyQuery(id.replace(/^ip_/, "")) === "query" ? (type === "wallet" ? "address" : type === "ip" ? "network" : "transaction") : undefined);

  return (
    <div className="space-y-4 text-[12px]">
      <div>
        <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">{type}</p>
        <div className="mt-1">
          <Identifier value={id.replace(/^ip_/, "")} head={14} tail={8} />
        </div>
      </div>
      {score != null && (
        <div className="flex items-center justify-between">
          <RiskBadge score={score} />
          <span className="font-mono tabular-nums">{formatScore100(score)} / 100</span>
        </div>
      )}
      <dl className="space-y-1.5 text-ink-muted">
        {Object.entries(data)
          .filter(([k, v]) => !["id", "label", "type", "riskScore", "riskBand"].includes(k) && v != null && String(v).length < 80)
          .slice(0, 8)
          .map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3">
              <dt className="text-ink-faint">{k}</dt>
              <dd className="font-mono text-ink">{String(v)}</dd>
            </div>
          ))}
      </dl>
      <div className="flex gap-2">
        <Button asChild size="sm">
          <Link href={href}>Inspect</Link>
        </Button>
        {onIsolate && (
          <Button size="sm" variant="outline" onClick={onIsolate}>
            Isolate
          </Button>
        )}
      </div>
    </div>
  );
}
