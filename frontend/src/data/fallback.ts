import type {
  ClusterRow,
  GraphElements,
  MarsarAlert,
  NetworkIntel,
  OverviewPayload,
  ReportFile,
  TransactionRow,
} from "@/lib/types";

/** Isolated mock layer used only when the offline backend is unreachable. */
export const FALLBACK_ALERTS: MarsarAlert[] = [
  {
    alert_id: "ALT-24018",
    target_type: "txid",
    target_identifier: "bc1q7f82k9a1d4e0c3b2a19876543210fedcba98",
    risk_score: 0.948,
    confidence: 0.948,
    primary_focus_area: "Peeling Chain",
    flags: { peeling_chain: true, mixer_coinjoin: false, anomaly_score: 0.81, taint_score: 0.72 },
    evidence: {
      reasons: ["Peeling chain", "Rapid velocity", "Taint exposure"],
      src_ip: "185.220.101.34",
      dst_ip: "51.15.64.12",
      country: "NL",
      asn: "AS12876",
      cluster_id: "cluster-024",
      sha256: "7c9e6679c6c1b0f8c4a2d3e1b9a8f0c6d4e2a1b3c5d7e9f0a1b2c3d4e5f60718",
    },
    created_at: Math.floor(Date.now() / 1000) - 120,
  },
  {
    alert_id: "ALT-24011",
    target_type: "txid",
    target_identifier: "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",
    risk_score: 0.882,
    confidence: 0.91,
    primary_focus_area: "CoinJoin",
    flags: { peeling_chain: false, mixer_coinjoin: true, anomaly_score: 0.77, taint_score: 0.64 },
    evidence: {
      reasons: ["CoinJoin", "Equal denomination outputs"],
      cluster_id: "cluster-011",
      country: "DE",
      src_ip: "45.33.32.156",
      sha256: "2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3",
    },
    created_at: Math.floor(Date.now() / 1000) - 860,
  },
  {
    alert_id: "ALT-23994",
    target_type: "wallet",
    target_identifier: "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
    risk_score: 0.61,
    confidence: 0.79,
    primary_focus_area: "Rapid Velocity",
    flags: { peeling_chain: false, mixer_coinjoin: false, anomaly_score: 0.68, taint_score: 0.22 },
    evidence: { reasons: ["Rapid velocity"], cluster_id: "cluster-009", country: "US" },
    created_at: Math.floor(Date.now() / 1000) - 5400,
  },
  {
    alert_id: "ALT-23980",
    target_type: "txid",
    target_identifier: "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
    risk_score: 0.27,
    confidence: 0.64,
    primary_focus_area: "Baseline",
    flags: { peeling_chain: false, mixer_coinjoin: false, anomaly_score: 0.18, taint_score: 0.04 },
    evidence: { reasons: ["Single-hop spend"], cluster_id: "cluster-002", country: "SG" },
    created_at: Math.floor(Date.now() / 1000) - 18000,
  },
];

export const FALLBACK_OVERVIEW: OverviewPayload = {
  transactions_analyzed: 1_284_291,
  high_risk: 184,
  suspicious: 612,
  clusters: 96,
  network_observations: 4021,
  countries: 38,
  alerts: 796,
  risk_timeline: Array.from({ length: 14 }).map((_, i) => ({
    day: `D${i + 1}`,
    high: 8 + ((i * 5) % 14),
    suspicious: 18 + ((i * 7) % 22),
    safe: 40 + ((i * 3) % 18),
  })),
};

export const FALLBACK_TX: TransactionRow[] = FALLBACK_ALERTS.map((a, i) => ({
  txid: a.target_identifier,
  timestamp: Number(a.created_at),
  inputs: 2 + i,
  outputs: 3 + (i % 2),
  amount: 1.24 + i * 0.31,
  fee: 0.00012 + i * 0.00004,
  risk_score: a.risk_score,
  typology: a.primary_focus_area,
  confidence: a.confidence,
  alert_id: a.alert_id,
  src_ip: String(a.evidence?.src_ip || "185.220.101.34"),
  dst_ip: String(a.evidence?.dst_ip || "51.15.64.12"),
  country: String(a.evidence?.country || "NL"),
  asn: "AS12876",
}));

export const FALLBACK_CLUSTERS: ClusterRow[] = [
  {
    cluster_id: "cluster-024",
    primary_ip: "185.220.101.34",
    confidence: 0.94,
    wallet_count: 42,
    addresses: ["bc1q7f82…", "bc1qxy2k…"],
    volume: 86.2,
    risk_score: 0.91,
    typologies: ["Peeling Chain"],
    last_activity: Math.floor(Date.now() / 1000) - 240,
  },
  {
    cluster_id: "cluster-011",
    primary_ip: "45.33.32.156",
    confidence: 0.88,
    wallet_count: 118,
    addresses: ["3J98t1…"],
    volume: 214.6,
    risk_score: 0.84,
    typologies: ["CoinJoin"],
    last_activity: Math.floor(Date.now() / 1000) - 1800,
  },
  {
    cluster_id: "cluster-009",
    primary_ip: "104.16.132.229",
    confidence: 0.71,
    wallet_count: 1204,
    addresses: ["bc1qar0…"],
    volume: 9810,
    risk_score: 0.29,
    typologies: ["Exchange deposit"],
    last_activity: Math.floor(Date.now() / 1000) - 7200,
  },
];

export const FALLBACK_GRAPH: GraphElements = {
  nodes: [
    { data: { id: "ip_185.220.101.34", label: "185.220.101.34", type: "ip", country: "NL", asn: "AS12876" } },
    { data: { id: "tx_peel", label: "TX 7f82…", type: "transaction", btc: 2.41 } },
    { data: { id: "w_in", label: "bc1q7f82…", type: "wallet", cluster: "cluster-024" } },
    { data: { id: "w_out", label: "bc1qxy2k…", type: "wallet", cluster: "cluster-024" } },
    { data: { id: "cl_024", label: "cluster-024", type: "cluster" } },
    { data: { id: "asn_12876", label: "AS12876", type: "asn" } },
    { data: { id: "cc_nl", label: "NL", type: "country" } },
  ],
  edges: [
    { data: { id: "e1", source: "ip_185.220.101.34", target: "tx_peel", relation: "OBSERVED" } },
    { data: { id: "e2", source: "w_in", target: "tx_peel", relation: "INPUT_TO" } },
    { data: { id: "e3", source: "tx_peel", target: "w_out", relation: "OUTPUT_TO" } },
    { data: { id: "e4", source: "w_in", target: "cl_024", relation: "MEMBER_OF" } },
    { data: { id: "e5", source: "w_out", target: "cl_024", relation: "MEMBER_OF" } },
    { data: { id: "e6", source: "ip_185.220.101.34", target: "asn_12876", relation: "ASSOCIATED_WITH" } },
    { data: { id: "e7", source: "asn_12876", target: "cc_nl", relation: "ASSOCIATED_WITH" } },
  ],
};

export const FALLBACK_NETWORK: NetworkIntel = {
  network_observations: 4021,
  unique_ips: 864,
  countries: 38,
  asns: 112,
  suspicious_connections: 47,
  timeline: Array.from({ length: 14 }).map((_, i) => ({
    day: `D${i + 1}`,
    observations: 180 + ((i * 37) % 90),
  })),
  ips: [
    { ip: "185.220.101.34", country: "NL", asn: "AS12876", transactions: 28, risk_score: 0.82, last_seen: Math.floor(Date.now() / 1000) - 180 },
    { ip: "45.33.32.156", country: "DE", asn: "AS63949", transactions: 14, risk_score: 0.66, last_seen: Math.floor(Date.now() / 1000) - 900 },
    { ip: "104.16.132.229", country: "US", asn: "AS13335", transactions: 91, risk_score: 0.21, last_seen: Math.floor(Date.now() / 1000) - 60 },
  ],
};

export const FALLBACK_REPORTS: ReportFile[] = [
  {
    filename: "MARSAR-STR-bc1q7f82k9a1d.html",
    generated: Math.floor(Date.now() / 1000) - 3600,
    status: "VERIFIED",
    subject: "bc1q7f82…7f82",
    risk: 0.948,
    evidence_hash: "7c9e6679c6c1b0f8c4a2d3e1b9a8f0c6d4e2a1b3c5d7e9f0a1b2c3d4e5f60718",
  },
  {
    filename: "MARSAR-STR-3J98t1WpEZ73.html",
    generated: Math.floor(Date.now() / 1000) - 86000,
    status: "READY",
    subject: "3J98t1…WNLy",
    risk: 0.882,
    evidence_hash: "2c624232cdd221771294dfbb310aca000a0df6ac8b66b696d90ef06fdefb64a3",
  },
];
