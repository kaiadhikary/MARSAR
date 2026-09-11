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

export function patternKey(focus?: string | null, flags?: { peeling_chain?: boolean; mixer_coinjoin?: boolean }) {
  const t = (focus || "").toLowerCase();
  if (flags?.peeling_chain || t.includes("peel")) return "peeling";
  if (flags?.mixer_coinjoin || t.includes("coinjoin") || t.includes("mix")) return "coinjoin";
  if (t.includes("taint") || t.includes("illicit")) return "taint";
  if (t.includes("network") || t.includes("geo")) return "network";
  if (t.includes("ml") || t.includes("classif")) return "ml";
  return "anomaly";
}
