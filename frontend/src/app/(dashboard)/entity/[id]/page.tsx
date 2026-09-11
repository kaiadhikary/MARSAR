"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ClusterRow, MarsarAlert } from "@/lib/types";
import { Identifier } from "@/components/ui/identifier";
import { RiskBadge } from "@/components/ui/risk-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { Button } from "@/components/ui/button";
import { formatScore100 } from "@/lib/cn";
import { investigationHistory } from "@/lib/history";
import { cn } from "@/lib/cn";

const TABS = ["Addresses", "Transactions", "Graph", "Risk", "Patterns", "Network"] as const;

export default function EntityPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const clusterId = decodeURIComponent(id);
  const [cluster, setCluster] = useState<ClusterRow | null>(null);
  const [alerts, setAlerts] = useState<MarsarAlert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Addresses");

  useEffect(() => {
    Promise.all([api.clusters(), api.alerts(200)]).then(([c, a]) => {
      const found = c.data?.clusters.find((x) => x.cluster_id === clusterId) || null;
      if (!found) {
        setError(c.error === "unavailable" ? "unavailable" : "not_found");
        return;
      }
      setCluster(found);
      investigationHistory.push({
        id: clusterId,
        kind: "entity",
        label: clusterId,
        href: `/entity/${encodeURIComponent(clusterId)}`,
      });
      const addr = new Set(found.addresses);
      setAlerts((a.data?.alerts || []).filter((x) => addr.has(x.target_identifier) || x.target_identifier === clusterId));
    });
  }, [clusterId]);

  if (error === "not_found") {
    return (
      <EmptyState
        title="ENTITY NOT FOUND"
        description="No cluster matches this identifier in the local corpus."
        action={<Button onClick={() => router.push("/clusters")}>Browse entities</Button>}
      />
    );
  }
  if (error === "unavailable") return <EmptyState title="CORPUS UNAVAILABLE" description="Clustering service is offline." />;
  if (!cluster) return <LoadingState label="RESOLVING ENTITY" />;

  const maxRisk = Math.max(0, ...alerts.map((a) => a.risk_score), cluster.confidence || 0);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Entity</p>
          <h1 className="mt-1 font-mono text-[18px]">{cluster.cluster_id}</h1>
          <p className="mt-2 text-[12px] text-ink-muted">
            {cluster.wallet_count} addresses · {alerts.length} related alerts
          </p>
        </div>
        <div className="flex items-center gap-3">
          <RiskBadge score={maxRisk || cluster.confidence} />
          <span className="font-mono text-[18px] tabular-nums">{formatScore100(maxRisk || cluster.confidence)} / 100</span>
        </div>
      </div>
      <div className="flex gap-1 overflow-x-auto border-b border-white/[0.06]">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn("px-3 py-2 text-[12px] text-ink-muted", tab === t && "border-b border-accent text-ink")}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "Addresses" && (
        <div className="panel rounded-md">
          {cluster.addresses.map((addr) => (
            <Link
              key={addr}
              href={`/address/${encodeURIComponent(addr)}`}
              className="flex items-center justify-between border-b border-white/[0.04] px-4 py-2 last:border-0 hover:bg-white/[0.03]"
            >
              <Identifier value={addr} />
              <span className="text-[11px] text-ink-faint">Inspect</span>
            </Link>
          ))}
        </div>
      )}
      {tab === "Transactions" && (
        <div className="panel rounded-md">
          {alerts.filter((a) => a.target_type === "txid").length ? (
            alerts
              .filter((a) => a.target_type === "txid")
              .map((a) => (
                <Link
                  key={a.alert_id}
                  href={`/tx/${encodeURIComponent(a.target_identifier)}`}
                  className="flex items-center justify-between border-b border-white/[0.04] px-4 py-2 last:border-0 hover:bg-white/[0.03]"
                >
                  <Identifier value={a.target_identifier} />
                  <RiskBadge score={a.risk_score} />
                </Link>
              ))
          ) : (
            <p className="px-4 py-8 text-center text-[12px] text-ink-muted">No scored transactions are linked to this entity.</p>
          )}
        </div>
      )}
      {tab === "Graph" && (
        <EmptyState
          title="OPEN IN VISUALIZER"
          description="Inspect this cluster in the full investigation graph."
          action={
            <Button asChild>
              <Link href={`/visualizer?q=${encodeURIComponent(cluster.addresses[0] || cluster.cluster_id)}`}>Open graph</Link>
            </Button>
          }
        />
      )}
      {tab === "Risk" && (
        <p className="text-[12px] text-ink-muted">
          Cluster confidence {formatScore100(cluster.confidence)} / 100. Peak linked alert {alerts.length ? formatScore100(maxRisk) : "Unavailable"}.
        </p>
      )}
      {tab === "Patterns" && (
        <ul className="text-[12px] text-ink-muted">
          {Array.from(new Set(alerts.map((a) => a.primary_focus_area))).map((p) => (
            <li key={p} className="border-b border-white/[0.04] py-2">
              {p}
            </li>
          ))}
          {!alerts.length && <li>No pattern evidence attached to this cluster.</li>}
        </ul>
      )}
      {tab === "Network" && (
        <p className="font-mono text-[12px]">{cluster.primary_ip || "Unavailable"}</p>
      )}
    </div>
  );
}
