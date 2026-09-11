import type { MarsarAlert } from "@/lib/types";
import { patternKey } from "@/lib/risk";

export interface EvidenceItem {
  id: string;
  index: string;
  title: string;
  detail: string;
  href?: string;
  action?: string;
}

export function evidenceFromAlert(alert?: MarsarAlert | null): EvidenceItem[] {
  if (!alert) return [];
  const items: EvidenceItem[] = [];
  const attr = (alert.evidence?.risk_attribution || {}) as Record<string, unknown>;
  const txid = alert.target_identifier;
  let n = 1;

  const push = (title: string, detail: string, href?: string, action?: string) => {
    items.push({
      id: `${alert.alert_id}-${n}`,
      index: String(n).padStart(2, "0"),
      title,
      detail,
      href,
      action,
    });
    n += 1;
  };

  if (alert.flags?.peeling_chain || patternKey(alert.primary_focus_area, alert.flags) === "peeling") {
    const peel = attr.peeling_chain_evidence as { hop_count?: number; hops?: unknown[] } | undefined;
    const hops = peel?.hop_count ?? peel?.hops?.length;
    push(
      "PEELING CHAIN",
      hops ? `${hops}-hop sequential flow detected` : "Sequential peel structure detected in this flow.",
      `/visualizer?q=${encodeURIComponent(txid)}`,
      "View on graph"
    );
  }

  if (alert.flags?.taint_score && alert.flags.taint_score > 0.2) {
    push(
      "TAINT EXPOSURE",
      `Connected to a flagged seed · taint ${(alert.flags.taint_score <= 1 ? alert.flags.taint_score * 100 : alert.flags.taint_score).toFixed(0)}`,
      `/tracer?q=${encodeURIComponent(txid)}`,
      "Trace connection"
    );
  }

  if (alert.flags?.anomaly_score && alert.flags.anomaly_score > 0.35) {
    const feature = String(attr.primary_anomalous_feature || "Unusual transaction characteristics");
    push("ANOMALY", feature, `/tx/${encodeURIComponent(txid)}`, "View features");
  }

  if (alert.flags?.mixer_coinjoin) {
    push(
      "COINJOIN-LIKE STRUCTURE",
      "Equal-denomination or mixer-like outputs observed.",
      `/patterns?type=coinjoin`,
      "Open pattern"
    );
  }

  const origin = String(attr.network_origin || "");
  if (origin) {
    push("NETWORK CORRELATION", origin, `/network`, "Inspect network");
  }

  if (!items.length) {
    push(
      alert.primary_focus_area || "FLAGGED ACTIVITY",
      String((alert.evidence as { alert_summary?: string } | undefined)?.alert_summary || "Composite risk exceeded investigative threshold."),
      `/tx/${encodeURIComponent(txid)}`,
      "Open investigation"
    );
  }

  return items;
}

export function attributionScores(alert?: MarsarAlert | null) {
  const attr = (alert?.evidence?.risk_attribution || {}) as Record<string, unknown>;
  const components = (attr.risk_components || {}) as Record<string, number | null>;
  return {
    ml: components.ml ?? (typeof attr.ml_classifier_probability === "number" ? attr.ml_classifier_probability : alert?.flags?.anomaly_score),
    anomaly: components.anomaly ?? (typeof attr.unsupervised_anomaly_score === "number" ? attr.unsupervised_anomaly_score : alert?.flags?.anomaly_score),
    taint: components.taint ?? (typeof attr.seed_taint_score === "number" ? attr.seed_taint_score : alert?.flags?.taint_score),
    network: components.network ?? null,
    demixing: components.demixing ?? null,
  };
}
