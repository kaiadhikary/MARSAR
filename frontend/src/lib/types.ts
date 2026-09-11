export type DataSource = "api" | "offline";
export type ApiError = "not_found" | "unavailable" | "failed";

export interface ApiResult<T> {
  data: T | null;
  source: DataSource;
  error?: ApiError;
  status?: number;
}

export interface HealthPayload {
  status: string;
  storage_mode?: string;
  record_counts?: {
    transactions: number;
    unique_entity_clusters: number;
    investigative_alerts: number;
    watchlist_seeds: number;
  };
}

export interface AlertFlags {
  peeling_chain?: boolean;
  mixer_coinjoin?: boolean;
  anomaly_score?: number;
  taint_score?: number;
}

export interface MarsarAlert {
  alert_id: string;
  target_type: string;
  target_identifier: string;
  risk_score: number;
  confidence: number;
  primary_focus_area: string;
  flags?: AlertFlags;
  evidence?: Record<string, unknown>;
  created_at: number | string;
}

export interface OverviewPayload {
  transactions_analyzed: number;
  high_risk: number;
  suspicious: number;
  clusters: number;
  network_observations: number;
  countries?: number;
  alerts?: number;
  risk_timeline: { day: string; high: number; suspicious: number; safe: number }[];
}

export interface TransactionRow {
  txid: string;
  timestamp: number;
  inputs: number;
  outputs: number;
  amount: number;
  fee: number;
  risk_score: number | null;
  typology: string | null;
  confidence: number | null;
  alert_id: string | null;
  src_ip: string;
  dst_ip: string;
  country: string;
  asn: string;
}

export interface ClusterRow {
  cluster_id: string;
  primary_ip: string;
  confidence: number;
  wallet_count: number;
  addresses: string[];
  volume?: number;
  risk_score?: number;
  typologies?: string[];
  last_activity?: number;
}

export interface GraphElements {
  nodes: { data: Record<string, unknown> }[];
  edges: { data: Record<string, unknown> }[];
}

export interface NetworkIntel {
  network_observations: number;
  unique_ips: number;
  countries: number;
  asns: number;
  suspicious_connections: number;
  timeline: { day: string; observations: number }[];
  ips: {
    ip: string;
    country: string;
    asn: string;
    transactions: number;
    risk_score: number | null;
    last_seen: number;
  }[];
}

export interface ReportFile {
  filename: string;
  path?: string;
  generated: number;
  size?: number;
  status: string;
  subject?: string;
  risk?: number;
  evidence_hash?: string;
}

export interface AuthStatus {
  airgap_active: boolean;
  network_listeners_disabled: boolean;
  require_auth: boolean;
  tamper_evident_hashing: string;
}

export interface TraceTx {
  txid: string;
  timestamp: number;
  total_btc: number;
  network: { src_ip: string; country: string; asn: string };
  inputs: { address?: string; amount?: number }[];
  outputs: { address?: string; amount?: number }[];
  backward_lineage: { funding_txid: string; via_address: string }[];
  forward_lineage: { spent_in_txid: string; from_address: string }[];
}

export interface WalletTrace {
  wallet_address: string;
  cluster_id: string;
  primary_ip: string;
  total_received_btc: number;
  total_sent_btc: number;
  current_balance_btc: number;
  transactions_count: number;
  activity: {
    txid: string;
    timestamp: number;
    role: string;
    net_flow: number;
    ip_origin: string;
    country: string;
  }[];
}

export interface ComplianceTx {
  txid: string;
  cluster_id?: string | null;
  risk_score?: number | null;
  risk_verdict?: string;
  ml_probability?: number | null;
  taint_score?: number | null;
  typology_score?: number | null;
  mixer_penalty_score?: number | null;
  is_coinjoin?: boolean | number | null;
  typology_flags?: string | null;
  fee_rate?: number | null;
  shannon_entropy?: number | null;
  created_at?: number | null;
}

export interface HtmlReport {
  filename: string;
  chain_of_custody_hash: string;
  dossier_id: string;
  report_path: string;
}
