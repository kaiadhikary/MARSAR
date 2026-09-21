import type {
  ApiError,
  ApiResult,
  AuthStatus,
  ClusterRow,
  ComplianceTx,
  GraphElements,
  HealthPayload,
  HtmlReport,
  MarsarAlert,
  NetworkIntel,
  OverviewPayload,
  TraceTx,
  TransactionRow,
  WalletTrace,
} from "@/lib/types";
import { classifyQuery } from "@/lib/search";
import { focusSubgraph, mergeGraphElements, toGraphElements } from "@/lib/graph";

const BASE = process.env.NEXT_PUBLIC_API_ORIGIN || "";

async function request<T>(path: string, init?: RequestInit, retries = 2): Promise<ApiResult<T>> {
  let lastError: ApiError = "unavailable";
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20_000);
    try {
      const res = await fetch(`${BASE}${path}`, {
        ...init,
        signal: controller.signal,
        headers: { Accept: "application/json", ...(init?.headers || {}) },
        cache: "no-store",
      });
      if (res.status === 404) return { data: null, source: "api", error: "not_found", status: 404 };
      if (!res.ok) {
        lastError = "failed";
        if (attempt < retries && res.status >= 500) continue;
        return { data: null, source: "api", error: "failed", status: res.status };
      }
      return { data: (await res.json()) as T, source: "api", status: res.status };
    } catch {
      lastError = "unavailable";
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, 350 * (attempt + 1)));
        continue;
      }
    } finally {
      clearTimeout(timer);
    }
  }
  return { data: null, source: "offline", error: lastError };
}

async function postJson<T>(path: string, body?: BodyInit, headers?: HeadersInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body, headers });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

function mapComplianceTx(row: ComplianceTx, extra?: Partial<TransactionRow>): TransactionRow {
  return {
    txid: row.txid,
    timestamp: row.timestamp || row.created_at || extra?.timestamp || 0,
    inputs: row.inputs ?? extra?.inputs ?? 0,
    outputs: row.outputs ?? extra?.outputs ?? 0,
    amount: row.amount ?? extra?.amount ?? 0,
    fee: row.fee ?? row.fee_rate ?? extra?.fee ?? 0,
    risk_score: row.risk_score ?? extra?.risk_score ?? null,
    typology: row.typology_flags ?? extra?.typology ?? (row.is_coinjoin ? "CoinJoin" : null),
    confidence: row.ml_probability ?? extra?.confidence ?? null,
    alert_id: row.alert_id ?? extra?.alert_id ?? null,
    src_ip: row.src_ip || extra?.src_ip || "",
    dst_ip: row.dst_ip || extra?.dst_ip || "",
    country: row.country || extra?.country || "",
    asn: row.asn || extra?.asn || "",
  };
}

export const api = {
  health: () => request<HealthPayload>("/health"),

  alerts: (limit = 5000, category?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (category && category !== "All") params.set("category", category.toLowerCase());
    return request<{ total: number; alerts: MarsarAlert[] }>(`/api/v1/alerts/ranked?${params}`);
  },

  alertSummary: () =>
    request<{ total: number; counts: Record<string, number> }>("/api/v1/alerts/summary"),

  alert: (id: string) => request<MarsarAlert>(`/api/v1/alerts/${encodeURIComponent(id)}`),

  async transactions(): Promise<ApiResult<{ total: number; transactions: TransactionRow[] }>> {
    const [compliance, alerts, tracesHint] = await Promise.all([
      request<{ recent: ComplianceTx[]; suspicious: ComplianceTx[]; flagged: ComplianceTx[] }>(
        "/api/v1/compliance/transactions?limit=500"
      ),
      request<{ total: number; alerts: MarsarAlert[] }>("/api/v1/alerts/ranked?limit=500"),
      request<{ elements: GraphElements }>("/api/v1/graph/topology?limit_tx=80"),
    ]);

    if (!compliance.data && !alerts.data) {
      return { data: null, source: compliance.source, error: (compliance.error || alerts.error) as ApiError };
    }

    const alertByTx = new Map(
      (alerts.data?.alerts || [])
        .filter((a) => a.target_type === "txid")
        .map((a) => [a.target_identifier, a])
    );
    const graphTx = new Map<string, Record<string, unknown>>();
    for (const node of tracesHint.data?.elements.nodes || []) {
      if (node.data.type === "transaction") graphTx.set(String(node.data.id), node.data);
    }

    const rows = (compliance.data?.recent || []).map((row) => {
      const alert = alertByTx.get(row.txid);
      const node = graphTx.get(row.txid);
      return mapComplianceTx(row, {
        alert_id: alert?.alert_id || null,
        amount: typeof node?.btc === "number" ? node.btc : 0,
        fee: typeof node?.fee === "number" ? node.fee : row.fee_rate || 0,
        country: String(node?.country || ""),
        risk_score: row.risk_score ?? alert?.risk_score ?? null,
        typology: row.typology_flags || alert?.primary_focus_area || null,
      });
    });

    if (!rows.length && alerts.data) {
      return {
        data: {
          total: alerts.data.alerts.length,
          transactions: alerts.data.alerts
            .filter((a) => a.target_type === "txid")
            .map((a) => ({
              txid: a.target_identifier,
              timestamp: typeof a.created_at === "number" ? a.created_at : 0,
              inputs: 0,
              outputs: 0,
              amount: 0,
              fee: 0,
              risk_score: a.risk_score,
              typology: a.primary_focus_area,
              confidence: a.confidence,
              alert_id: a.alert_id,
              src_ip: "",
              dst_ip: "",
              country: "",
              asn: "",
            })),
        },
        source: "api",
      };
    }

    return { data: { total: rows.length, transactions: rows }, source: "api" };
  },

  clusters: () => request<{ total_clusters: number; clusters: ClusterRow[] }>("/api/v1/graph/clusters"),

  graph: (limit = 80) => request<{ elements: GraphElements }>(`/api/v1/graph/topology?limit_tx=${limit}`),

  expandAddress: (address: string, hops = 3) =>
    request<{
      status?: string;
      address: string;
      hops: number;
      cluster: ClusterRow | null;
      nodes: { id: string; label: string; is_root?: boolean; is_blacklisted?: boolean }[];
      edges: { id: string; source: string; target: string }[];
    }>(`/api/v1/graph/expand/${encodeURIComponent(address)}?hops=${hops}`),

  rebuildClusters: () =>
    postJson<{ status: string; cluster_count: number; message: string }>("/api/v1/graph/clusters/rebuild"),

  async loadGraph(focus?: string, limit = 120): Promise<ApiResult<GraphElements>> {
    const kind = focus ? classifyQuery(focus) : "query";

    if (focus && kind === "address") {
      const expanded = await api.expandAddress(focus, 3);
      if (expanded.data?.nodes?.length) {
        return { data: toGraphElements(expanded.data.nodes, expanded.data.edges), source: "api" };
      }
    }

    const graph = await request<{ elements: GraphElements }>(`/api/v1/graph/topology?limit_tx=${limit}`);
    if (!graph.data) return { data: null, source: graph.source, error: graph.error };

    let elements = graph.data.elements;
    if (!focus) return { data: elements, source: "api" };

    if (kind === "transaction" || kind === "network" || kind === "query") {
      elements = focusSubgraph(elements, focus, kind === "transaction" ? 2 : 1);
    } else if (kind === "entity") {
      elements = focusSubgraph(elements, focus.replace(/^entity\s*#?/i, "").trim(), 1);
    } else if (kind === "address") {
      const expanded = await api.expandAddress(focus, 3);
      if (expanded.data?.nodes?.length) {
        elements = mergeGraphElements(elements, toGraphElements(expanded.data.nodes, expanded.data.edges));
      } else {
        elements = focusSubgraph(elements, focus, 1);
      }
    }

    return { data: elements, source: "api" };
  },

  async network(): Promise<ApiResult<NetworkIntel>> {
    const graph = await request<{ elements: GraphElements }>("/api/v1/graph/topology?limit_tx=200");
    if (!graph.data) return { data: null, source: graph.source, error: graph.error };
    const ips = graph.data.elements.nodes
      .filter((n) => n.data.type === "ip")
      .map((n) => ({
        ip: String(n.data.ip || String(n.data.id).replace(/^ip_/, "")),
        country: String(n.data.country || "—"),
        asn: String(n.data.asn || "—"),
        transactions: graph.data!.elements.edges.filter(
          (e) => e.data.source === n.data.id || e.data.target === n.data.id
        ).length,
        risk_score: null as number | null,
        last_seen: 0,
      }));
    const countries = new Set(ips.map((i) => i.country).filter((c) => c && c !== "—"));
    const asns = new Set(ips.map((i) => i.asn).filter((a) => a && a !== "—"));
    return {
      data: {
        network_observations: graph.data.elements.edges.filter((e) => String(e.data.relation || "").includes("BROADCAST") || String(e.data.relation || "").includes("OBSERVED")).length,
        unique_ips: ips.length,
        countries: countries.size,
        asns: asns.size,
        suspicious_connections: 0,
        timeline: [],
        ips,
      },
      source: "api",
    };
  },

  async overview(): Promise<ApiResult<OverviewPayload>> {
    const [health, alerts] = await Promise.all([api.health(), api.alerts(200)]);
    if (!health.data && !alerts.data) {
      return { data: null, source: health.source, error: health.error || alerts.error };
    }
    const list = alerts.data?.alerts || [];
    const high = list.filter((a) => a.risk_score >= 0.7).length;
    const suspicious = list.filter((a) => a.risk_score >= 0.35 && a.risk_score < 0.7).length;
    return {
      data: {
        transactions_analyzed: health.data?.record_counts?.transactions ?? 0,
        high_risk: high,
        suspicious,
        clusters: health.data?.record_counts?.unique_entity_clusters ?? 0,
        network_observations: 0,
        alerts: health.data?.record_counts?.investigative_alerts ?? list.length,
        risk_timeline: [],
      },
      source: health.source,
      error: health.error,
    };
  },

  authStatus: () => request<AuthStatus>("/api/v1/auth/status"),

  traceTx: (txid: string) => request<TraceTx>(`/api/v1/trace/tx/${encodeURIComponent(txid)}`),

  wallet: (address: string) => request<WalletTrace>(`/api/v1/trace/wallet/${encodeURIComponent(address)}`),

  ingestFile: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return postJson<{ status: string; file_processed: string; transactions_ingested: number }>(
      "/api/v1/ingest/file",
      form
    );
  },

  runPipeline: () =>
    postJson<{ status: string; clusters_identified: number; alerts_generated: number }>("/api/v1/pipeline/run"),

  flagged: (limit = 100) =>
    request<{ flagged: ComplianceTx[] }>(`/api/v1/compliance/flagged?limit=${limit}`),

  generateHtmlReport: async (txid: string) => {
    const res = await fetch(`${BASE}/api/v1/alerts/${encodeURIComponent(txid)}/report/html`);
    if (!res.ok) throw new Error("Report generation failed");
    return (await res.json()) as HtmlReport;
  },

  exportStrReport: async (txid: string, caseId?: string, investigatorNote?: string) => {
    const res = await fetch(`${BASE}/api/v1/export-str`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/html" },
      body: JSON.stringify({
        txid,
        case_id: caseId || undefined,
        investigator_note: investigatorNote || undefined,
      }),
    });
    if (!res.ok) {
      const detail = await res.text();
      throw new Error(detail || `Report export failed (${res.status})`);
    }
    const html = await res.text();
    const hash = res.headers.get("X-Evidence-SHA256") || "";
    const filename = `MARSAR-STR-${txid.slice(0, 16)}.html`;
    return {
      html,
      filename,
      chain_of_custody_hash: hash,
      dossier_id: `MARSAR-${txid.slice(0, 16)}`,
      report_path: filename,
      verdict: res.headers.get("X-Verdict"),
      risk_score: res.headers.get("X-Risk-Score"),
    } satisfies HtmlReport & { html: string; verdict?: string | null; risk_score?: string | null };
  },
};

