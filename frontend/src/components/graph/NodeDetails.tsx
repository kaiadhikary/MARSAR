"use client";

import { ClusterSummary, ComplianceScreen, GraphNode, WalletTrace } from "@/lib/api";
import { formatBtc, formatTimestamp } from "@/lib/graph-utils";
import RiskGauge from "@/components/widgets/RiskGauge";

interface NodeDetailsProps {
  node: GraphNode | null;
  cluster: ClusterSummary | null;
  wallet: WalletTrace | null;
  compliance: ComplianceScreen | null;
}

export default function NodeDetails({
  node,
  cluster,
  wallet,
  compliance,
}: NodeDetailsProps) {
  if (!node) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-400">
          Click a node in the graph to inspect network, wallet, or transaction
          evidence.
        </div>
        {compliance && <ComplianceCard compliance={compliance} />}
        {wallet && <WalletCard wallet={wallet} />}
      </div>
    );
  }

  const typeLabel = {
    wallet: "Wallet Address",
    transaction: "Transaction (TXID)",
    ip: "Network IP Peer",
  }[node.type];

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-200">
        <div className="mb-3 flex items-center gap-2">
          <TypeBadge type={node.type} />
          {node.is_root && (
            <span className="rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
              SEARCH TARGET
            </span>
          )}
        </div>

        <h3 className="mb-1 text-xs font-semibold uppercase text-slate-400">
          {typeLabel}
        </h3>
        <p className="mb-4 break-all font-mono text-xs text-slate-300">
          {node.id}
        </p>

        <dl className="grid grid-cols-2 gap-2 text-xs">
          {node.type === "wallet" && (
            <>
              <dt className="text-slate-500">Cluster</dt>
              <dd className="font-mono text-slate-300">
                {node.cluster ?? "UNCLUSTERED"}
              </dd>
              <dt className="text-slate-500">Watchlist</dt>
              <dd
                className={
                  node.is_blacklisted
                    ? "font-semibold text-red-400"
                    : "text-emerald-400"
                }
              >
                {node.is_blacklisted
                  ? node.blacklist_entity ?? "Flagged"
                  : "Clean"}
              </dd>
            </>
          )}
          {node.type === "transaction" && (
            <>
              <dt className="text-slate-500">Volume (BTC)</dt>
              <dd>{node.btc != null ? formatBtc(node.btc) : "—"}</dd>
              <dt className="text-slate-500">Miner Fee</dt>
              <dd>{node.fee ?? "—"}</dd>
              <dt className="text-slate-500">Geo</dt>
              <dd>{node.country ?? "UNKNOWN"}</dd>
            </>
          )}
          {node.type === "ip" && (
            <>
              <dt className="text-slate-500">IP</dt>
              <dd className="font-mono">{node.ip ?? node.id.replace("ip_", "")}</dd>
              <dt className="text-slate-500">Country</dt>
              <dd>{node.country ?? "UNKNOWN"}</dd>
              <dt className="text-slate-500">ASN</dt>
              <dd className="font-mono text-[10px]">{node.asn ?? "—"}</dd>
            </>
          )}
        </dl>
      </div>

      {cluster && <ClusterCard cluster={cluster} />}
      {compliance && node.type === "wallet" && (
        <ComplianceCard compliance={compliance} />
      )}
      {wallet && node.type === "wallet" && <WalletCard wallet={wallet} />}
    </div>
  );
}

function TypeBadge({ type }: { type: GraphNode["type"] }) {
  const styles = {
    wallet: "bg-blue-500/20 text-blue-300",
    transaction: "bg-violet-500/20 text-violet-300",
    ip: "bg-cyan-500/20 text-cyan-300",
  };
  return (
    <span
      className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${styles[type]}`}
    >
      {type}
    </span>
  );
}

function ClusterCard({ cluster }: { cluster: ClusterSummary }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm">
      <h3 className="mb-2 text-xs font-semibold uppercase text-slate-400">
        Entity Cluster (CIOH)
      </h3>
      <dl className="grid grid-cols-2 gap-2 text-xs">
        <dt className="text-slate-500">Cluster ID</dt>
        <dd className="break-all font-mono text-slate-300">{cluster.cluster_id}</dd>
        <dt className="text-slate-500">Members</dt>
        <dd>{cluster.wallet_count}</dd>
        <dt className="text-slate-500">Primary IP</dt>
        <dd className="font-mono">{cluster.primary_ip ?? "—"}</dd>
        <dt className="text-slate-500">Confidence</dt>
        <dd>{(cluster.confidence * 100).toFixed(1)}%</dd>
      </dl>
    </div>
  );
}

function ComplianceCard({ compliance }: { compliance: ComplianceScreen }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm">
      <h3 className="mb-3 text-xs font-semibold uppercase text-slate-400">
        Compliance Screening
      </h3>
      <RiskGauge score={compliance.propagated_taint_score} label="Taint Score" />
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <dt className="text-slate-500">Verdict</dt>
        <dd
          className={
            compliance.compliance_verdict === "BLOCKED"
              ? "font-bold text-red-400"
              : "text-emerald-400"
          }
        >
          {compliance.compliance_verdict}
        </dd>
        <dt className="text-slate-500">Sanctioned Seed</dt>
        <dd>{compliance.is_sanctioned_seed ? "Yes" : "No"}</dd>
        {compliance.seed_category && (
          <>
            <dt className="text-slate-500">Category</dt>
            <dd>{compliance.seed_category}</dd>
          </>
        )}
      </dl>
    </div>
  );
}

function WalletCard({ wallet }: { wallet: WalletTrace }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm">
      <h3 className="mb-2 text-xs font-semibold uppercase text-slate-400">
        Wallet Flow Summary
      </h3>
      <dl className="grid grid-cols-2 gap-2 text-xs">
        <dt className="text-slate-500">Received</dt>
        <dd>{formatBtc(wallet.total_received_btc)} BTC</dd>
        <dt className="text-slate-500">Sent</dt>
        <dd>{formatBtc(wallet.total_sent_btc)} BTC</dd>
        <dt className="text-slate-500">Balance</dt>
        <dd>{formatBtc(wallet.current_balance_btc)} BTC</dd>
        <dt className="text-slate-500">Transactions</dt>
        <dd>{wallet.transactions_count}</dd>
      </dl>
      {wallet.activity.length > 0 && (
        <div className="mt-3 max-h-32 overflow-auto">
          <p className="mb-1 text-[10px] uppercase text-slate-500">
            Recent Activity
          </p>
          {wallet.activity.slice(0, 5).map((a) => (
            <div
              key={a.txid}
              className="border-b border-slate-800 py-1 text-[10px] text-slate-400"
            >
              <span
                className={
                  a.role === "SENDER" ? "text-amber-400" : "text-emerald-400"
                }
              >
                {a.role}
              </span>{" "}
              · {a.txid.slice(0, 12)}… · {formatTimestamp(a.timestamp)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
