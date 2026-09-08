// Axios client pointing to the MARSAR FastAPI backend.
import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export const TOKEN_STORAGE_KEY = "marsar_access_token";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export interface GraphNode {
  id: string;
  label: string;
  is_root: boolean;
  is_blacklisted: boolean;
  blacklist_entity: string | null;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
}

export interface ClusterInfo {
  cluster_id: string;
  root_address: string;
  member_count: number;
  risk_score: number;
  first_seen: string;
  last_updated: string;
}

export interface GraphExpandResponse {
  status: string;
  address: string;
  hops: number;
  cluster: ClusterInfo | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface PersistedTransaction {
  txid: string;
  cluster_id: string | null;
  risk_score: number;
  risk_verdict: string;
  ml_probability: number;
  taint_score: number;
  typology_score: number;
  mixer_penalty_score: number;
  is_coinjoin: number;
  blacklist_hit: number;
  typology_flags: string;
  fee_rate: number;
  shannon_entropy: number;
  created_at: string;
}

export interface ExportIntegrity {
  txid: string;
  risk_score: string;
  verdict: string;
  evidence_sha256: string;
  generated_at: string;
}

export async function fetchAddressGraph(
  address: string,
  hops: number = 3
): Promise<GraphExpandResponse> {
  const res = await api.get<GraphExpandResponse>(
    `/graph/expand/${encodeURIComponent(address)}`,
    { params: { hops } }
  );
  return res.data;
}

export async function loginAnalyst(passkey: string): Promise<string> {
  const res = await api.post<{ access_token: string }>("/auth/login", {
    passkey,
  });
  const token = res.data.access_token;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  }
  return token;
}

export function logoutAnalyst(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export interface FlaggedTransaction {
  txid: string;
  risk_score: number;
  risk_verdict: string;
  flags: string;
  blacklist_hit: number;
  is_coinjoin: number;
  cluster_id: string | null;
  flagged_at: string;
}

export async function fetchReportableTransactions(limit: number = 50): Promise<{
  recent: PersistedTransaction[];
  suspicious: PersistedTransaction[];
  flagged: FlaggedTransaction[];
}> {
  const res = await api.get("/compliance/transactions", { params: { limit } });
  return res.data;
}

export async function fetchFlaggedTransactions(limit: number = 100): Promise<FlaggedTransaction[]> {
  const res = await api.get("/compliance/flagged", { params: { limit } });
  return res.data.flagged || [];
}

export async function exportStrReport(payload: {
  txid: string;
  case_id?: string;
  investigator_note?: string;
}): Promise<{ blob: Blob; integrity: ExportIntegrity }> {
  const res = await api.post("/export-str", payload, {
    responseType: "blob",
    timeout: 120_000,
  });
  const headers = res.headers;
  return {
    blob: res.data as Blob,
    integrity: {
      txid: String(headers["x-txid"] || payload.txid),
      risk_score: String(headers["x-risk-score"] || ""),
      verdict: String(headers["x-verdict"] || ""),
      evidence_sha256: String(headers["x-evidence-sha256"] || ""),
      generated_at: String(headers["x-generated-at"] || ""),
    },
  };
}
