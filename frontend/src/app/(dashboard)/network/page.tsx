"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { NetworkIntel } from "@/lib/types";
import { Identifier } from "@/components/ui/identifier";
import { EmptyState } from "@/components/ui/empty-state";
import { SkeletonRows } from "@/components/ui/loading-state";
import { NumberTicker } from "@/components/magic/number-ticker";
import { investigationHistory } from "@/lib/history";

export default function NetworkPage() {
  return (
    <Suspense fallback={<SkeletonRows />}>
      <Network />
    </Suspense>
  );
}

function Network() {
  const params = useSearchParams();
  const q = (params.get("q") || "").trim();
  const [data, setData] = useState<NetworkIntel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.network().then((r) => {
      if (!r.data) setError(r.error || "failed");
      setData(r.data);
      if (q) investigationHistory.push({ id: q, kind: "network", label: q, href: `/network?q=${encodeURIComponent(q)}` });
    });
  }, [q]);

  const rows = useMemo(() => {
    const ips = data?.ips || [];
    if (!q) return ips;
    return ips.filter((ip) => ip.ip.includes(q) || ip.asn.toLowerCase().includes(q.toLowerCase()) || ip.country.toLowerCase().includes(q.toLowerCase()));
  }, [data, q]);

  if (data === null && !error) {
    return (
      <div>
        <h2 className="text-[15px] font-medium">Network intelligence</h2>
        <div className="panel mt-4 rounded-md">
          <SkeletonRows />
        </div>
      </div>
    );
  }

  if (!data) {
    return <EmptyState title="NETWORK UNAVAILABLE" description="IP topology could not be derived from the graph store." />;
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[15px] font-medium tracking-tight">Network intelligence</h2>
        <p className="mt-1 text-[12px] text-ink-muted">Observed broadcast and peer IPs from ingested P2P telemetry.</p>
      </div>
      <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-white/[0.08] bg-white/[0.08] md:grid-cols-4">
        <Stat k="Observations" v={data.network_observations} />
        <Stat k="Unique IPs" v={data.unique_ips} />
        <Stat k="Countries" v={data.countries} />
        <Stat k="ASNs" v={data.asns} />
      </div>
      <div className="panel rounded-md">
        {!rows.length ? (
          <EmptyState title="NO NETWORK EVIDENCE" description="No IP observations match this filter." />
        ) : (
          rows.map((ip) => (
            <div key={ip.ip} className="flex items-center justify-between border-b border-white/[0.04] px-4 py-2 last:border-0">
              <div>
                <Identifier value={ip.ip} head={18} tail={0} />
                <p className="mt-1 text-[11px] text-ink-muted">
                  {ip.country} · {ip.asn} · {ip.transactions} linked edges
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function Stat({ k, v }: { k: string; v: number }) {
  return (
    <div className="bg-[#08090b] px-4 py-3">
      <p className="text-[10px] tracking-[0.14em] text-ink-faint">{k}</p>
      <p className="mt-1 font-mono text-[16px] tabular-nums">
        <NumberTicker value={v} />
      </p>
    </div>
  );
}
