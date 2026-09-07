"use client";

import { Alert } from "@/lib/api";
import RiskGauge from "./RiskGauge";

interface EvidencePanelProps {
  alert: Alert;
}

export default function EvidencePanel({ alert }: EvidencePanelProps) {
  const evidence = alert.evidence ?? {};

  return (
    <div className="space-y-4 rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm">
      <div className="grid gap-4 sm:grid-cols-2">
        <RiskGauge score={alert.risk_score} label="Composite Risk" />
        <RiskGauge score={alert.confidence} label="Model Confidence" />
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Detection Flags
        </h4>
        <div className="flex flex-wrap gap-2">
          {alert.flags.peeling_chain && (
            <FlagBadge label="Peeling Chain" color="red" />
          )}
          {alert.flags.mixer_coinjoin && (
            <FlagBadge label="Mixer / CoinJoin" color="violet" />
          )}
          {alert.flags.anomaly_score > 0.3 && (
            <FlagBadge
              label={`Anomaly ${(alert.flags.anomaly_score * 100).toFixed(0)}%`}
              color="amber"
            />
          )}
          {alert.flags.taint_score > 0.2 && (
            <FlagBadge
              label={`Taint ${(alert.flags.taint_score * 100).toFixed(0)}%`}
              color="red"
            />
          )}
          {!alert.flags.peeling_chain &&
            !alert.flags.mixer_coinjoin &&
            alert.flags.anomaly_score <= 0.3 &&
            alert.flags.taint_score <= 0.2 && (
              <span className="text-slate-500">Heuristic / ML composite signal</span>
            )}
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Explainability Evidence
        </h4>
        <pre className="max-h-48 overflow-auto rounded-md bg-slate-950 p-3 font-mono text-xs text-slate-300">
          {JSON.stringify(evidence, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function FlagBadge({
  label,
  color,
}: {
  label: string;
  color: "red" | "amber" | "violet";
}) {
  const colors = {
    red: "bg-red-500/15 text-red-300 border-red-500/30",
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/30",
    violet: "bg-violet-500/15 text-violet-300 border-violet-500/30",
  };
  return (
    <span
      className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${colors[color]}`}
    >
      {label}
    </span>
  );
}
