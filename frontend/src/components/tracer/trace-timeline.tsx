"use client";

import Link from "next/link";
import { formatBtc, formatDate } from "@/lib/cn";
import { Identifier } from "@/components/ui/identifier";
import { RiskBadge } from "@/components/ui/risk-badge";
import { cn } from "@/lib/cn";

export interface TraceStep {
  kind: "wallet" | "transaction";
  id: string;
  amount?: number | null;
  timestamp?: number | null;
  risk?: number | null;
  pattern?: string | null;
}

export function TraceTimeline({ steps }: { steps: TraceStep[] }) {
  if (!steps.length) return null;
  return (
    <ol className="relative space-y-0">
      {steps.map((step, i) => {
        const href = step.kind === "wallet" ? `/address/${encodeURIComponent(step.id)}` : `/tx/${encodeURIComponent(step.id)}`;
        return (
          <li key={`${step.kind}-${step.id}-${i}`} className="relative pl-6">
            {i < steps.length - 1 && (
              <span className="absolute left-[7px] top-5 h-[calc(100%-8px)] w-px bg-gradient-to-b from-accent/50 to-white/[0.06]" />
            )}
            <span className={cn("absolute left-0 top-2 h-3.5 w-3.5 rounded-full border border-accent/60 bg-[#08090b]", step.risk && step.risk >= 0.7 && "border-danger")} />
            <Link href={href} className="block rounded-sm px-2 py-2 transition-colors duration-150 hover:bg-white/[0.03]">
              <p className="text-[10px] tracking-[0.14em] text-ink-faint">{step.kind.toUpperCase()}</p>
              <Identifier value={step.id} />
              <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-ink-muted">
                {step.amount != null && <span className="font-mono">{formatBtc(step.amount)}</span>}
                {step.timestamp ? <span className="font-mono">{formatDate(step.timestamp)}</span> : null}
                {step.risk != null && <RiskBadge score={step.risk} />}
                {step.pattern && <span>{step.pattern}</span>}
              </div>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}
