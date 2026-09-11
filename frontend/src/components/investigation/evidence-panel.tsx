"use client";

import { ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { GlassCard } from "@/components/ui/glass-card";
import { RiskBar, RiskScore } from "@/components/ui/risk-score";
import { ShimmerButton } from "@/components/magic/shimmer-button";
import { truncateId } from "@/lib/cn";

export function EvidencePanel({
  score,
  taint,
  typology,
  ml,
  mixer,
  typologies,
  srcIp,
  dstIp,
  country,
  asn,
  timestamp,
  hash,
}: {
  score?: number | null;
  taint?: number;
  typology?: number;
  ml?: number;
  mixer?: number;
  typologies: string[];
  srcIp?: string;
  dstIp?: string;
  country?: string;
  asn?: string;
  timestamp?: string;
  hash?: string;
}) {
  return (
    <GlassCard hover={false} className="h-full overflow-y-auto" padding="p-4">
      <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Risk Assessment</p>
      <div className="mt-3">
        <RiskScore score={score} />
      </div>
      <div className="mt-5 space-y-3">
        <RiskBar label="Taint Exposure" value={taint ?? 0} />
        <RiskBar label="Typology" value={typology ?? 0} />
        <RiskBar label="ML Probability" value={ml ?? 0} />
        <RiskBar label="Mixer Penalty" value={mixer ?? 0} />
      </div>
      <div className="mt-6">
        <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Detected Typologies</p>
        <ul className="mt-2 space-y-1.5 text-[13px] text-ink-muted">
          {typologies.length ? typologies.map((t) => <li key={t}>{t}</li>) : <li>None detected</li>}
        </ul>
      </div>
      <div className="mt-6">
        <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Network Evidence</p>
        <dl className="mt-2 space-y-1.5 text-[12px]">
          <Row k="Source IP" v={srcIp} />
          <Row k="Destination IP" v={dstIp} />
          <Row k="Country" v={country} />
          <Row k="ASN" v={asn} />
          <Row k="Timestamp" v={timestamp} />
        </dl>
      </div>
      <div className="mt-6">
        <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Evidence Integrity</p>
        <p className="mt-2 font-mono text-[11px] leading-relaxed text-ink-muted">SHA-256</p>
        <p className="mt-1 break-all font-mono text-[11px] text-ink">{hash ? truncateId(hash, 20, 12) : "—"}</p>
        <ShimmerButton
          className="mt-3"
          icon={<ShieldCheck className="h-3.5 w-3.5" />}
          onClick={() => toast.success("Evidence verified")}
        >
          Verify Evidence
        </ShimmerButton>
      </div>
    </GlassCard>
  );
}

function Row({ k, v }: { k: string; v?: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-ink-faint">{k}</dt>
      <dd className="font-mono text-ink">{v || "—"}</dd>
    </div>
  );
}
