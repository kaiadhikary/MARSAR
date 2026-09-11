"use client";

import { GitBranch, Maximize2, Waypoints } from "lucide-react";
import { GradientButton } from "@/components/magic/gradient-button";
import { ShimmerButton } from "@/components/magic/shimmer-button";
import { Button } from "@/components/ui/button";
import { RiskScore } from "@/components/ui/risk-score";
import { truncateId } from "@/lib/cn";

export function InvestigationHeader({
  subject,
  kind,
  score,
  onTrace,
  onExpand,
  onDossier,
  dossierLoading,
}: {
  subject: string;
  kind: string;
  score?: number | null;
  onTrace: () => void;
  onExpand: () => void;
  onDossier: () => void;
  dossierLoading?: boolean;
}) {
  return (
    <div className="glass flex flex-wrap items-center gap-4 rounded-lg px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">{kind}</p>
        <p className="mt-0.5 truncate font-mono text-[13px]">{truncateId(subject, 18, 8)}</p>
      </div>
      <RiskScore score={score} size="sm" />
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={onTrace}>
          <Waypoints className="h-3.5 w-3.5" />
          Trace
        </Button>
        <Button variant="outline" size="sm" onClick={onExpand}>
          <Maximize2 className="h-3.5 w-3.5" />
          Expand
        </Button>
        <GradientButton onClick={onDossier} loading={dossierLoading} icon={<GitBranch className="h-3.5 w-3.5" />}>
          Generate Dossier
        </GradientButton>
      </div>
    </div>
  );
}

export { ShimmerButton };
