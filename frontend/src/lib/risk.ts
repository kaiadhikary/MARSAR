export type RiskBand = "critical" | "high" | "medium" | "low";

export function normalizedScore(score?: number | null) {
  if (score === undefined || score === null || Number.isNaN(score)) return null;
  return score <= 1 ? score : score / 100;
}

export function riskBand(score?: number | null): RiskBand {
  const v = normalizedScore(score) ?? 0;
  if (v >= 0.85) return "critical";
  if (v >= 0.7) return "high";
  if (v >= 0.35) return "medium";
  return "low";
}

export function riskLabel(band: RiskBand) {
  if (band === "critical") return "CRITICAL";
  if (band === "high") return "HIGH";
  if (band === "medium") return "MEDIUM";
  return "LOW";
}

export function typologyFromFlags(alert: {
  primary_focus_area?: string;
  flags?: {
    peeling_chain?: boolean;
    mixer_coinjoin?: boolean;
  };
  evidence?: { typologies?: string[]; reasons?: string[] };
}) {
  if (alert.primary_focus_area) return alert.primary_focus_area;
  const types: string[] = [];
  if (alert.flags?.peeling_chain) types.push("Peeling Chain");
  if (alert.flags?.mixer_coinjoin) types.push("CoinJoin");
  return types[0] || alert.evidence?.typologies?.[0] || "Anomaly";
}

export type FocusCategory = "ml" | "taint" | "anomaly" | "peeling" | "coinjoin" | "network";

export function patternKey(focus?: string | null, flags?: { peeling_chain?: boolean; mixer_coinjoin?: boolean }) {
  const t = (focus || "").toLowerCase();
  if (flags?.peeling_chain || t.includes("peel")) return "peeling";
  if (flags?.mixer_coinjoin || t.includes("coinjoin") || t.includes("mix")) return "coinjoin";
  if (t.includes("taint") || t.includes("illicit")) return "taint";
  if (t.includes("network") || t.includes("geo")) return "network";
  if (t.includes("ml") || t.includes("classif")) return "ml";
  if (t.includes("anomaly")) return "anomaly";
  return "anomaly";
}

/** Match alerts by engine signals, not only the single primary_focus_area label. */
export function alertMatchesFocus(
  alert: {
    primary_focus_area?: string;
    flags?: {
      peeling_chain?: boolean;
      mixer_coinjoin?: boolean;
      anomaly_score?: number;
      taint_score?: number;
      ml_score?: number | null;
      network_score?: number | null;
    };
    evidence?: Record<string, unknown>;
  },
  focus: string
): boolean {
  if (!focus || focus === "All") return true;

  const category = focus.toLowerCase() as FocusCategory;
  const key = patternKey(alert.primary_focus_area, alert.flags);
  const attr = (alert.evidence?.risk_attribution || {}) as Record<string, unknown>;
  const components = (attr.risk_components || {}) as Record<string, number | null | undefined>;
  const ml =
    alert.flags?.ml_score ??
    components.ml ??
    (attr.ml_classifier_probability as number | undefined);
  const taint =
    components.taint ??
    (attr.seed_taint_score as number | undefined) ??
    (attr.propagated_taint_score as number | undefined) ??
    alert.flags?.taint_score;
  const anomaly =
    components.anomaly ??
    (attr.unsupervised_anomaly_score as number | undefined) ??
    alert.flags?.anomaly_score;
  const network = alert.flags?.network_score ?? components.network ?? 0;
  const peelEvidence = attr.peeling_chain_evidence || attr.peeling_transaction_evidence;
  const mixerEvidence = attr.mixer_evidence;

  switch (category) {
    case "ml":
      return key === "ml" || (ml ?? 0) >= 0.5;
    case "taint":
      return key === "taint" || (taint ?? 0) >= 0.35;
    case "anomaly":
      return key === "anomaly" || (anomaly ?? 0) >= 0.35;
    case "peeling":
      return key === "peeling" || Boolean(alert.flags?.peeling_chain) || Boolean(peelEvidence);
    case "coinjoin":
      return key === "coinjoin" || Boolean(alert.flags?.mixer_coinjoin) || Boolean(mixerEvidence);
    case "network":
      return key === "network" || (network ?? 0) > 0;
    default:
      return key === category;
  }
}
