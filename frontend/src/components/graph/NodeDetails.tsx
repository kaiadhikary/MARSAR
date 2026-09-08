"use client";

// Cluster details & risk breakdown drawer.
import { ClusterInfo, GraphNode } from "@/lib/api";

interface NodeDetailsProps {
  node: GraphNode | null;
  cluster: ClusterInfo | null;
}

export default function NodeDetails({ node, cluster }: NodeDetailsProps) {
  if (!node) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-400">
        Click a node in the graph to see its details here.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-200">
      <h3 className="mb-2 font-semibold text-slate-100">Address</h3>
      <p className="mb-4 break-all font-mono text-xs text-slate-300">{node.id}</p>

      <div className="mb-4 grid grid-cols-2 gap-2">
        <span className="text-slate-400">Role</span>
        <span>{node.is_root ? "Cluster root" : "Cluster member"}</span>

        <span className="text-slate-400">Blacklist status</span>
        <span className={node.is_blacklisted ? "font-semibold text-red-400" : "text-emerald-400"}>
          {node.is_blacklisted ? `Flagged — ${node.blacklist_entity ?? "unknown entity"}` : "Clean"}
        </span>
      </div>

      {cluster && (
        <>
          <h3 className="mb-2 font-semibold text-slate-100">Cluster</h3>
          <div className="grid grid-cols-2 gap-2">
            <span className="text-slate-400">Cluster ID</span>
            <span className="break-all font-mono text-xs">{cluster.cluster_id}</span>

            <span className="text-slate-400">Members</span>
            <span>{cluster.member_count}</span>

            <span className="text-slate-400">Risk score</span>
            <span>{cluster.risk_score}</span>

            <span className="text-slate-400">First seen</span>
            <span>{cluster.first_seen}</span>

            <span className="text-slate-400">Last updated</span>
            <span>{cluster.last_updated}</span>
          </div>
        </>
      )}
    </div>
  );
}
