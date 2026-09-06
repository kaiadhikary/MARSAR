// Axios client pointing to the MARSAR FastAPI backend.
import axios from "axios";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10_000,
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
