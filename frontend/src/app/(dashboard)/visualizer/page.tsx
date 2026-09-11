"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { GraphElements, MarsarAlert } from "@/lib/types";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import { GraphNodePanel } from "@/components/graph/graph-node-panel";
import { SearchBar } from "@/components/layout/search-bar";
import { Drawer } from "@/components/ui/drawer";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { classifyQuery, visualizerHref } from "@/lib/search";
import { toGraphElements } from "@/lib/graph";
import { investigationHistory } from "@/lib/history";

export default function VisualizerPage() {
  return (
    <Suspense fallback={<LoadingState label="LOADING TRANSACTION TOPOLOGY" />}>
      <Visualizer />
    </Suspense>
  );
}

function Visualizer() {
  const params = useSearchParams();
  const router = useRouter();
  const q = (params.get("q") || "").trim();
  const [graph, setGraph] = useState<GraphElements | null>(null);
  const [alerts, setAlerts] = useState<MarsarAlert[]>([]);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState("Loading transaction topology...");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (focus?: string) => {
    setPhase(focus ? `Focusing on ${focus.slice(0, 18)}…` : "Loading transaction topology...");
    setError(null);
    const [g, a] = await Promise.all([api.loadGraph(focus, 150), api.alerts(250)]);
    if (!g.data) {
      setError(g.error || "failed");
      setGraph(null);
      return;
    }
    setGraph(g.data);
    setAlerts(a.data?.alerts || []);
    if (focus) {
      investigationHistory.push({
        id: focus,
        kind: classifyQuery(focus) === "address" ? "address" : "transaction",
        label: focus,
        href: visualizerHref(focus),
      });
    }
  }, []);

  useEffect(() => {
    load(q);
  }, [q, load]);

  const riskById = useMemo(() => {
    const map: Record<string, number> = {};
    for (const a of alerts) {
      map[a.target_identifier] = a.risk_score;
      if (a.target_type === "wallet") {
        map[`ip_${a.target_identifier}`] = a.risk_score;
      }
    }
    return map;
  }, [alerts]);

  async function expandSelected() {
    if (!selected) return;
    const id = String(selected.id || "").replace(/^ip_/, "");
    const type = String(selected.type || "");
    if (type !== "wallet" && type !== "ip" && !id.startsWith("benign_") && !id.startsWith("merchant_")) return;
    setRefreshing(true);
    setPhase(`Expanding ${id.slice(0, 14)}…`);
    const expanded = await api.expandAddress(id, 3);
    if (expanded.data?.nodes?.length && graph) {
      const extra = toGraphElements(expanded.data.nodes, expanded.data.edges);
      const nodeMap = new Map(graph.nodes.map((n) => [String(n.data.id), n]));
      for (const n of extra.nodes) nodeMap.set(String(n.data.id), n);
      const edgeMap = new Map(graph.edges.map((e) => [String(e.data.id), e]));
      for (const e of extra.edges) edgeMap.set(String(e.data.id), e);
      setGraph({ nodes: [...nodeMap.values()], edges: [...edgeMap.values()] });
    }
    setRefreshing(false);
  }

  async function refresh() {
    setRefreshing(true);
    await load(q);
    setRefreshing(false);
  }

  if (error === "unavailable") {
    return (
      <EmptyState
        title="GRAPH UNAVAILABLE"
        description="Topology could not be loaded. Start the backend API on port 8000, then retry."
        action={<Button onClick={() => refresh()}>Retry</Button>}
      />
    );
  }

  if (!graph) return <LoadingState label="CONSTRUCTING GRAPH" detail={phase} />;

  if (!graph.nodes.length) {
    return (
      <div className="space-y-4">
        <SearchBar compact />
        <EmptyState
          title="NO GRAPH DATA"
          description="Ingest a dataset and run the pipeline, then search a transaction or address."
          action={<Button onClick={() => router.push("/dataset")}>Import dataset</Button>}
        />
      </div>
    );
  }

  const focusLabel = q ? ` · focus ${q.slice(0, 16)}` : "";

  return (
    <div className="flex min-h-[calc(100vh-72px)] flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Visualizer</p>
          <p className="text-[12px] text-ink-muted">
            {graph.nodes.length} nodes · {graph.edges.length} edges{focusLabel}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={refresh} disabled={refreshing}>
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>
      <SearchBar compact />
      <div className="min-h-0 flex-1">
        <GraphCanvas
          elements={graph}
          riskById={riskById}
          onSelect={setSelected}
          onExpand={expandSelected}
        />
      </div>
      {selected && (
        <Drawer kicker="Selected node" title={String(selected.label || selected.id)} onClose={() => setSelected(null)}>
          <GraphNodePanel data={selected} onIsolate={expandSelected} />
        </Drawer>
      )}
    </div>
  );
}
