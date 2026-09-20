"use client";

import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { GradientButton } from "@/components/magic/gradient-button";
import { Button } from "@/components/ui/button";
import { RiskScore } from "@/components/ui/risk-score";
import type { MarsarAlert } from "@/lib/types";
import { formatDate, truncateId } from "@/lib/cn";
import { typologyFromFlags } from "@/lib/risk";

export function AlertDrawer({ alert, onClose }: { alert: MarsarAlert; onClose: () => void }) {
  const router = useRouter();
  const evidence = (alert.evidence || {}) as Record<string, unknown>;
  const reasons = (evidence.reasons as string[]) || [alert.primary_focus_area];

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" onClick={onClose} />
      <aside className="panel-elevated relative z-10 h-full w-full max-w-md overflow-y-auto border-l p-5 animate-[slide-in-right_180ms_ease-out]">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Alert</p>
            <p className="mt-1 font-mono text-[13px]">{alert.alert_id}</p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-5">
          <RiskScore score={alert.risk_score} />
        </div>
        <Section title="Why this was flagged">
          <ul className="space-y-1.5 text-[13px] text-ink-muted">
            {reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </Section>
        <Section title="Model confidence">
          <p className="font-mono text-sm">{((alert.confidence <= 1 ? alert.confidence * 100 : alert.confidence)).toFixed(1)}%</p>
        </Section>
        <Section title="Typology evidence">
          <p className="text-[13px] text-ink-muted">{typologyFromFlags(alert)}</p>
        </Section>
        <Section title="Network evidence">
          <p className="font-mono text-[12px] text-ink-muted">
            {String(
              ((alert.evidence?.risk_attribution as Record<string, unknown> | undefined)?.network_origin as
                | string
                | undefined) ||
                evidence.src_ip ||
                "—"
            )}
          </p>
        </Section>
        <Section title="Cluster information">
          <p className="font-mono text-[12px]">{String(evidence.cluster_id || "UNCLUSTERED")}</p>
        </Section>
        <Section title="Related transactions">
          <p className="font-mono text-[12px] text-ink-muted">{truncateId(alert.target_identifier, 16, 8)}</p>
          <p className="mt-1 text-[11px] text-ink-faint">{formatDate(alert.created_at)}</p>
        </Section>
        <div className="mt-6 space-y-2">
          <GradientButton
            className="w-full justify-center"
            onClick={() =>
              router.push(
                alert.target_type === "wallet"
                  ? `/address/${encodeURIComponent(alert.target_identifier)}`
                  : `/tx/${encodeURIComponent(alert.target_identifier)}`
              )
            }
          >
            Investigate
          </GradientButton>
          <Button
            className="w-full"
            variant="outline"
            onClick={() =>
              router.push(`/visualizer?q=${encodeURIComponent(alert.target_identifier)}`)
            }
          >
            Open in visualizer
          </Button>
        </div>
      </aside>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-5">
      <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">{title}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}
