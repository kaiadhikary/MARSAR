// Axios client for the MARSAR FastAPI backend.
import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export const BACKEND_ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, "");

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
});

export const rootApi = axios.create({
  baseURL: BACKEND_ORIGIN,
  timeout: 30_000,
});

// ── Graph / topology ────────────────────────────────────────────────────────

export type NodeType = "wallet" | "transaction" | "ip";

export interface TopologyNodeData {
  id: string;
  label: string;
  type: NodeType;
  cluster?: string;
  btc?: number;
  fee?: number;
  country?: string;
  ip?: string;
  asn?: string;
}

export interface TopologyEdgeData {
  id: string;
  source: string;
  target: string;
  relation?: string;
  amount?: number;
}

export interface GraphTopologyResponse {
  elements: {
    nodes: { data: TopologyNodeData }[];
    edges: { data: TopologyEdgeData }[];
  };
}

export interface GraphNode {
  id: string;
  label: string;
  type: NodeType;
  is_root: boolean;
  is_blacklisted: boolean;
  blacklist_entity: string | null;
  cluster?: string;
  country?: string;
  btc?: number;
  fee?: number;
  ip?: string;
  asn?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation?: string;
  amount?: number;
}

export interface ClusterSummary {
  cluster_id: string;
  primary_ip: string;
  confidence: number;
  wallet_count: number;
  addresses: string[];
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

export interface ComplianceScreen {
  address: string;
  is_sanctioned_seed: boolean;
  seed_category: string | null;
  cluster_id: string;
  propagated_taint_score: number;
  compliance_verdict: "BLOCKED" | "CLEAR";
}

export interface InvestigatorResult {
  address: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  wallet: WalletTrace | null;
  compliance: ComplianceScreen | null;
  cluster: ClusterSummary | null;
}

// ── Alerts ──────────────────────────────────────────────────────────────────

export interface AlertFlags {
  peeling_chain: boolean;
  mixer_coinjoin: boolean;
  anomaly_score: number;
  taint_score: number;
}

export interface Alert {
  alert_id: string;
  target_type: string;
  target_identifier: string;
  risk_score: number;
  confidence: number;
  primary_focus_area: string;
  flags: AlertFlags;
  evidence: Record<string, unknown>;
  created_at: number;
}

export interface RankedAlertsResponse {
  total: number;
  alerts: Alert[];
}

export interface StrReportInfo {
  report_path: string;
  filename: string;
  chain_of_custody_hash: string;
  dossier_id: string;
}

export interface StrMarkdownResponse {
  txid: string;
  report_markdown: string;
}

// ── System health ───────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  storage_mode: string;
  record_counts: {
    transactions: number;
    unique_entity_clusters: number;
    investigative_alerts: number;
    watchlist_seeds: number;
  };
}

export interface SystemStatus {
  system: string;
  version: string;
  mode: string;
  database_connected: boolean;
}

export interface IllicitSeed {
  address: string;
  category: string;
  severity: number;
  added_at?: number;
}

// ── API calls ───────────────────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await rootApi.get<HealthResponse>("/health");
  return res.data;
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await rootApi.get<SystemStatus>("/");
  return res.data;
}

export async function fetchGraphTopology(
  limitTx = 200
): Promise<GraphTopologyResponse> {
  const res = await api.get<GraphTopologyResponse>("/graph/topology", {
    params: { limit_tx: limitTx },
  });
  return res.data;
}

export async function fetchClusters(): Promise<{
  total_clusters: number;
  clusters: ClusterSummary[];
}> {
  const res = await api.get("/graph/clusters");
  return res.data;
}

export async function traceWallet(address: string): Promise<WalletTrace> {
  const res = await api.get<WalletTrace>(
    `/trace/wallet/${encodeURIComponent(address)}`
  );
  return res.data;
}

export async function screenAddress(
  address: string
): Promise<ComplianceScreen> {
  const res = await api.get<ComplianceScreen>(
    `/compliance/check/${encodeURIComponent(address)}`
  );
  return res.data;
}

export async function fetchIllicitSeeds(): Promise<{
  total_seeds: number;
  seeds: IllicitSeed[];
}> {
  const res = await api.get("/compliance/seeds");
  return res.data;
}

export async function fetchRankedAlerts(
  limit = 50,
  focusArea?: string
): Promise<RankedAlertsResponse> {
  const res = await api.get<RankedAlertsResponse>("/alerts/ranked", {
    params: { limit, focus_area: focusArea || undefined },
  });
  return res.data;
}

export async function fetchAlertDetail(alertId: string): Promise<Alert> {
  const res = await api.get<Alert>(`/alerts/${encodeURIComponent(alertId)}`);
  return res.data;
}

export async function recomputeAlerts(): Promise<{
  status: string;
  generated_alert_count: number;
}> {
  const res = await api.post("/alerts/recompute");
  return res.data;
}

export async function runPipeline(): Promise<{
  status: string;
  clusters_identified: number;
  alerts_generated: number;
}> {
  const res = await rootApi.post("/api/v1/pipeline/run");
  return res.data;
}

export async function ingestFile(file: File): Promise<{
  status: string;
  file_processed: string;
  format: string;
  transactions_ingested: number;
}> {
  const form = new FormData();
  form.append("file", file);
  const res = await rootApi.post("/api/v1/ingest/file", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function generateStrHtml(txid: string): Promise<StrReportInfo> {
  const res = await api.get<StrReportInfo>(
    `/alerts/${encodeURIComponent(txid)}/report/html`
  );
  return res.data;
}

export async function generateStrMarkdown(
  txid: string
): Promise<StrMarkdownResponse> {
  const res = await api.get<StrMarkdownResponse>(
    `/alerts/${encodeURIComponent(txid)}/report/markdown`
  );
  return res.data;
}

export async function rebuildClusters(): Promise<{
  status: string;
  cluster_count: number;
  message: string;
}> {
  const res = await api.post("/graph/clusters/rebuild");
  return res.data;
}

/** Build investigator view from existing topology, trace, and compliance APIs. */
export async function fetchInvestigatorData(
  address: string,
  hops = 3
): Promise<InvestigatorResult> {
  const [topology, clustersRes, seedsRes, wallet, compliance] =
    await Promise.all([
      fetchGraphTopology(300),
      fetchClusters(),
      fetchIllicitSeeds(),
      traceWallet(address).catch(() => null),
      screenAddress(address).catch(() => null),
    ]);

  const { flattenTopology, extractAddressSubgraph, applyBlacklistFlags, findClusterForAddress } =
    await import("./graph-utils");

  const { nodes: allNodes, edges: allEdges } = flattenTopology(topology);
  let { nodes, edges } = extractAddressSubgraph(allNodes, allEdges, address, hops);

  // Address may exist in DB but not in recent topology slice — show it as a lone node
  if (nodes.length === 0 && wallet) {
    nodes = [
      {
        id: address,
        label: `W: ${address.slice(0, 8)}…`,
        type: "wallet",
        is_root: true,
        is_blacklisted: compliance?.is_sanctioned_seed ?? false,
        blacklist_entity: compliance?.seed_category ?? null,
        cluster: wallet.cluster_id,
      },
    ];
    edges = [];
  }

  nodes = applyBlacklistFlags(nodes, seedsRes.seeds);
  const rootNode = nodes.find((n) => n.id === address);
  if (rootNode) rootNode.is_root = true;

  return {
    address,
    nodes,
    edges,
    wallet,
    compliance,
    cluster: findClusterForAddress(clustersRes.clusters, address),
  };
}
