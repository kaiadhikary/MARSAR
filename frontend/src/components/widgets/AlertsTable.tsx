"use client";

import { Fragment } from "react";
import { Alert } from "@/lib/api";
import { formatTimestamp, riskColor } from "@/lib/graph-utils";
import EvidencePanel from "./EvidencePanel";

interface AlertsTableProps {
  alerts: Alert[];
  expandedId: string | null;
  onToggle: (id: string) => void;
}

export default function AlertsTable({
  alerts,
  expandedId,
  onToggle,
}: AlertsTableProps) {
  if (alerts.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-700 p-8 text-center text-sm text-slate-500">
        No investigative alerts yet. Ingest data and run the detection pipeline
        to generate ranked leads.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-700">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-700 bg-slate-900/80 text-xs uppercase tracking-wider text-slate-400">
          <tr>
            <th className="px-4 py-3">Rank</th>
            <th className="px-4 py-3">Target</th>
            <th className="px-4 py-3">Focus Area</th>
            <th className="px-4 py-3">Risk</th>
            <th className="px-4 py-3">Confidence</th>
            <th className="px-4 py-3">Flags</th>
            <th className="px-4 py-3">Created</th>
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {alerts.map((alert, idx) => (
            <Fragment key={alert.alert_id}>
              <tr
                className="border-b border-slate-800 hover:bg-slate-900/50"
              >
                <td className="px-4 py-3 font-mono text-slate-400">
                  #{idx + 1}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
                    {alert.target_type}
                  </span>
                  <p className="mt-1 max-w-[200px] truncate font-mono text-xs text-slate-200">
                    {alert.target_identifier}
                  </p>
                </td>
                <td className="px-4 py-3 text-slate-300">
                  {alert.primary_focus_area}
                </td>
                <td className={`px-4 py-3 font-semibold ${riskColor(alert.risk_score)}`}>
                  {(alert.risk_score * 100).toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-slate-300">
                  {(alert.confidence * 100).toFixed(1)}%
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    {alert.flags.peeling_chain && (
                      <MiniFlag title="Peeling">P</MiniFlag>
                    )}
                    {alert.flags.mixer_coinjoin && (
                      <MiniFlag title="Mixer">M</MiniFlag>
                    )}
                    {alert.flags.anomaly_score > 0.3 && (
                      <MiniFlag title="Anomaly">A</MiniFlag>
                    )}
                    {alert.flags.taint_score > 0.2 && (
                      <MiniFlag title="Taint">T</MiniFlag>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {formatTimestamp(alert.created_at)}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => onToggle(alert.alert_id)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    {expandedId === alert.alert_id ? "Hide" : "Evidence"}
                  </button>
                </td>
              </tr>
              {expandedId === alert.alert_id && (
                <tr>
                  <td colSpan={8} className="bg-slate-950/50 px-4 py-4">
                    <EvidencePanel alert={alert} />
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MiniFlag({
  children,
  title,
}: {
  children: React.ReactNode;
  title: string;
}) {
  return (
    <span
      title={title}
      className="flex h-5 w-5 items-center justify-center rounded bg-slate-800 text-[10px] font-bold text-slate-300"
    >
      {children}
    </span>
  );
}
