import type { MarsarAlert } from "@/lib/types";
import { attributionScores } from "@/lib/evidence";
import { BorderBeam } from "@/components/magic/border-beam";
import { RiskBar, RiskScore } from "@/components/ui/risk-score";
import { Kicker } from "@/components/ui/panel";
import { riskBand } from "@/lib/risk";

export function RiskPanel({ alert }: { alert?: MarsarAlert | null }) {
  const scores = attributionScores(alert);
  const band = riskBand(alert?.risk_score);
  const critical = band === "critical";

  return (
    <BorderBeam active={critical} tone="danger">
      <div className="p-4">
        <Kicker>Risk score</Kicker>
        <div className="mt-3">
          <RiskScore score={alert?.risk_score} />
        </div>
        <div className="mt-5 space-y-3">
          <RiskBar label="ML probability" value={scores.ml} />
          <RiskBar label="Anomaly" value={scores.anomaly} />
          <RiskBar label="Taint exposure" value={scores.taint} />
          <RiskBar label="Network risk" value={scores.network} />
        </div>
      </div>
    </BorderBeam>
  );
}
