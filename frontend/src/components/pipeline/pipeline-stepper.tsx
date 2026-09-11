"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/cn";

export const PIPELINE_STEPS = [
  "Dataset Ingestion",
  "Normalization",
  "Network Correlation",
  "GeoIP Enrichment",
  "Graph Construction",
  "AI/ML Analysis",
  "Report Generation",
];

export const INGEST_STEPS = [
  "Parsing",
  "Normalization",
  "Correlation",
  "GeoIP Enrichment",
  "Graph Construction",
  "AI/ML Analysis",
  "Risk Scoring",
];

export function PipelineStepper({
  steps = PIPELINE_STEPS,
  active = 2,
  completeThrough,
}: {
  steps?: string[];
  active?: number;
  completeThrough?: number;
}) {
  const doneAt = completeThrough ?? Math.max(0, active - 1);
  return (
    <ol className="space-y-0">
      {steps.map((step, i) => {
        const done = i <= doneAt && i !== active;
        const current = i === active;
        return (
          <li key={step} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-5 w-5 items-center justify-center rounded-full border text-[10px]",
                  done && "border-safe/40 bg-safe/15 text-safe",
                  current && "border-transparent",
                  !done && !current && "border-white/10 text-ink-faint"
                )}
              >
                {done ? (
                  <Check className="h-3 w-3" />
                ) : current ? (
                  <span className="relative flex h-5 w-5 items-center justify-center">
                    <span className="absolute inset-0 rounded-full bg-accent/30" />
                    <span className="relative h-2 w-2 rounded-full bg-white" />
                  </span>
                ) : (
                  <span className="h-1 w-1 rounded-full bg-white/20" />
                )}
              </div>
              {i < steps.length - 1 && (
                <div className={cn("my-1 w-px flex-1 min-h-[14px]", done ? "bg-safe/30" : "bg-white/8")} />
              )}
            </div>
            <div className={cn("pb-3 text-[13px]", current ? "text-ink" : done ? "text-ink-muted" : "text-ink-faint")}>
              {step}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
