"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import type { ClusterRow } from "@/lib/types";
import { Identifier } from "@/components/ui/identifier";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/loading-state";
import { NumberTicker } from "@/components/magic/number-ticker";

export default function ClustersPage() {
  const router = useRouter();
  const [clusters, setClusters] = useState<ClusterRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rebuilding, setRebuilding] = useState(false);

  useEffect(() => {
    api.clusters().then((r) => {
      if (!r.data) setError(r.error || "failed");
      setClusters(r.data?.clusters || []);
    });
  }, []);

  if (clusters === null) {
    return (
      <div>
        <h2 className="text-[15px] font-medium">Entities</h2>
        <div className="panel mt-4 rounded-md">
          <SkeletonRows />
        </div>
      </div>
    );
  }

  if (error === "unavailable") {
    return <EmptyState title="CLUSTERING UNAVAILABLE" description="Entity clusters could not be loaded from the local engine." />;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-[15px] font-medium tracking-tight">Entities</h2>
          <p className="mt-1 text-[12px] text-ink-muted">CIOH and IP co-location clusters.</p>
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={rebuilding}
          onClick={async () => {
            setRebuilding(true);
            try {
              const res = await api.rebuildClusters();
              toast.success(`Rebuilt ${res.cluster_count} clusters`);
              const r = await api.clusters();
              setClusters(r.data?.clusters || []);
            } catch {
              toast.error("Cluster rebuild failed — confirm the API is running.");
            } finally {
              setRebuilding(false);
            }
          }}
        >
          {rebuilding ? "Rebuilding…" : "Rebuild clusters"}
        </Button>
      </div>
      <p className="font-mono text-[12px] text-ink-muted">
        <NumberTicker value={clusters.length} /> clusters
      </p>
      <div className="panel rounded-md">
        {!clusters.length ? (
          <EmptyState title="NO ENTITIES" description="Run analysis after ingesting a dataset to build clusters." />
        ) : (
          clusters.map((c) => (
            <button
              key={c.cluster_id}
              type="button"
              onClick={() => router.push(`/entity/${encodeURIComponent(c.cluster_id)}`)}
              className="flex w-full items-center justify-between gap-3 border-b border-white/[0.04] px-4 py-2.5 text-left last:border-0 hover:bg-white/[0.03]"
            >
              <div>
                <p className="font-mono text-[13px]">{c.cluster_id}</p>
                <p className="mt-1 text-[11px] text-ink-muted">
                  {c.wallet_count} addresses · {c.primary_ip || "No IP"}
                </p>
              </div>
              <Identifier value={c.addresses[0] || ""} />
            </button>
          ))
        )}
      </div>
    </div>
  );
}
