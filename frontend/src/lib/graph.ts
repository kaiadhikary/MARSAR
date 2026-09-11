import type { GraphElements } from "@/lib/types";

type RawNode = { id: string; label?: string; is_root?: boolean; is_blacklisted?: boolean; [key: string]: unknown };
type RawEdge = { id: string; source: string; target: string; [key: string]: unknown };

function inferNodeType(id: string): string {
  if (id.startsWith("ip_")) return "ip";
  if (id.startsWith("tx_") || id.startsWith("TX:")) return "transaction";
  if (id.startsWith("ENT_") || id.startsWith("cluster")) return "cluster";
  return "wallet";
}

export function toGraphElements(nodes: RawNode[], edges: RawEdge[]): GraphElements {
  return {
    nodes: nodes.map((n) => ({
      data: {
        ...n,
        id: n.id,
        label: n.label || n.id.slice(0, 12),
        type: inferNodeType(n.id),
      },
    })),
    edges: edges.map((e) => ({
      data: {
        ...e,
        id: e.id,
        source: e.source,
        target: e.target,
        relation: String((e as Record<string, unknown>).relation || "LINKED"),
      },
    })),
  };
}

/** Keep a focus node and its N-hop neighborhood. */
export function focusSubgraph(elements: GraphElements, focus: string, hops = 2): GraphElements {
  const needle = focus.trim();
  if (!needle) return elements;

  const nodeIds = new Set(elements.nodes.map((n) => String(n.data.id)));
  const startIds = new Set<string>();
  if (nodeIds.has(needle)) startIds.add(needle);
  if (nodeIds.has(`ip_${needle}`)) startIds.add(`ip_${needle}`);
  for (const n of elements.nodes) {
    const id = String(n.data.id);
    if (id.includes(needle) || String(n.data.label || "").includes(needle)) startIds.add(id);
  }
  if (!startIds.size) return elements;

  const adj = new Map<string, Set<string>>();
  for (const e of elements.edges) {
    const s = String(e.data.source);
    const t = String(e.data.target);
    if (!adj.has(s)) adj.set(s, new Set());
    if (!adj.has(t)) adj.set(t, new Set());
    adj.get(s)!.add(t);
    adj.get(t)!.add(s);
  }

  const keep = new Set<string>();
  const queue: { id: string; depth: number }[] = [...startIds].map((id) => ({ id, depth: 0 }));
  while (queue.length) {
    const { id, depth } = queue.shift()!;
    if (keep.has(id) || depth > hops) continue;
    keep.add(id);
    for (const next of adj.get(id) || []) {
      if (!keep.has(next)) queue.push({ id: next, depth: depth + 1 });
    }
  }

  const nodes = elements.nodes.filter((n) => keep.has(String(n.data.id)));
  const ids = new Set(nodes.map((n) => String(n.data.id)));
  const edges = elements.edges.filter((e) => ids.has(String(e.data.source)) && ids.has(String(e.data.target)));
  return { nodes, edges };
}

export function mergeGraphElements(base: GraphElements, extra: GraphElements): GraphElements {
  const nodeMap = new Map(base.nodes.map((n) => [String(n.data.id), n]));
  for (const n of extra.nodes) nodeMap.set(String(n.data.id), n);
  const edgeMap = new Map(base.edges.map((e) => [String(e.data.id), e]));
  for (const e of extra.edges) edgeMap.set(String(e.data.id), e);
  return { nodes: [...nodeMap.values()], edges: [...edgeMap.values()] };
}
