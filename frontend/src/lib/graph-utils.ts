import {
  GraphEdge,
  GraphNode,
  GraphTopologyResponse,
  IllicitSeed,
  ClusterSummary,
} from "./api";

/** Extract flat node/edge arrays from the Cytoscape-style topology response. */
export function flattenTopology(topology: GraphTopologyResponse): {
  nodes: GraphNode[];
  edges: GraphEdge[];
} {
  const nodes: GraphNode[] = topology.elements.nodes.map(({ data }) => ({
    id: data.id,
    label: data.label,
    type: data.type,
    is_root: false,
    is_blacklisted: false,
    blacklist_entity: null,
    cluster: data.cluster,
    country: data.country,
    btc: data.btc,
    fee: data.fee,
    ip: data.ip,
    asn: data.asn,
  }));

  const edges: GraphEdge[] = topology.elements.edges.map(({ data }) => ({
    id: data.id,
    source: data.source,
    target: data.target,
    relation: data.relation,
    amount: data.amount,
  }));

  return { nodes, edges };
}

/** BFS subgraph around a wallet address (includes connected txs and IPs). */
export function extractAddressSubgraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  address: string,
  maxHops = 3
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const adjacency = new Map<string, Set<string>>();

  for (const edge of edges) {
    if (!adjacency.has(edge.source)) adjacency.set(edge.source, new Set());
    if (!adjacency.has(edge.target)) adjacency.set(edge.target, new Set());
    adjacency.get(edge.source)!.add(edge.target);
    adjacency.get(edge.target)!.add(edge.source);
  }

  const visited = new Set<string>();
  const queue: [string, number][] = [[address, 0]];
  visited.add(address);

  while (queue.length > 0) {
    const [current, depth] = queue.shift()!;
    if (depth >= maxHops) continue;

    for (const neighbor of adjacency.get(current) ?? []) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([neighbor, depth + 1]);
      }
    }
  }

  // If address isn't in topology, return empty — caller may show wallet-only info
  if (!nodeMap.has(address) && visited.size <= 1) {
    return { nodes: [], edges: [] };
  }

  const subNodes = nodes
    .filter((n) => visited.has(n.id))
    .map((n) => ({ ...n, is_root: n.id === address }));

  const subEdges = edges.filter(
    (e) => visited.has(e.source) && visited.has(e.target)
  );

  return { nodes: subNodes, edges: subEdges };
}

/** Mark wallet nodes that match the illicit seed watchlist. */
export function applyBlacklistFlags(
  nodes: GraphNode[],
  seeds: IllicitSeed[]
): GraphNode[] {
  const seedMap = new Map(seeds.map((s) => [s.address, s.category]));
  return nodes.map((n) => {
    if (n.type !== "wallet") return n;
    const category = seedMap.get(n.id);
    if (!category) return n;
    return {
      ...n,
      is_blacklisted: true,
      blacklist_entity: category,
    };
  });
}

/** Find cluster metadata for an address from the clusters list. */
export function findClusterForAddress(
  clusters: ClusterSummary[],
  address: string
): ClusterSummary | null {
  return clusters.find((c) => c.addresses.includes(address)) ?? null;
}

export function riskColor(score: number): string {
  if (score >= 0.7) return "text-red-400";
  if (score >= 0.45) return "text-amber-400";
  return "text-emerald-400";
}

export function riskBg(score: number): string {
  if (score >= 0.7) return "bg-red-500";
  if (score >= 0.45) return "bg-amber-500";
  return "bg-emerald-500";
}

export function formatTimestamp(ts: number): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

export function formatBtc(value: number): string {
  return value.toFixed(8);
}
