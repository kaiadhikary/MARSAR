import type { TraceTx } from "@/lib/types";
import { formatBtc, formatDate } from "@/lib/cn";
import { Identifier } from "@/components/ui/identifier";
import { Kicker } from "@/components/ui/panel";
import Link from "next/link";

export function TxOverview({ tx }: { tx: TraceTx }) {
  return (
    <div className="panel rounded-md p-4">
      <Kicker>Transaction details</Kicker>
      <dl className="mt-3 grid gap-2 text-[12px] sm:grid-cols-2">
        <Row k="TXID" v={<Identifier value={tx.txid} head={12} tail={8} />} />
        <Row k="Timestamp" v={<span className="font-mono">{formatDate(tx.timestamp)}</span>} />
        <Row k="Amount" v={<span className="font-mono">{formatBtc(tx.total_btc)}</span>} />
        <Row k="Inputs / outputs" v={<span className="font-mono">{tx.inputs.length} / {tx.outputs.length}</span>} />
        <Row k="Source IP" v={<span className="font-mono">{tx.network.src_ip || "Unavailable"}</span>} />
        <Row k="Network" v={<span className="font-mono">{[tx.network.country, tx.network.asn].filter(Boolean).join(" · ") || "Unavailable"}</span>} />
      </dl>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <Kicker>Inputs</Kicker>
          <ul className="mt-2 space-y-1">
            {tx.inputs.length ? tx.inputs.map((i, idx) => (
              <li key={`${i.address}-${idx}`} className="flex justify-between gap-2 text-[12px]">
                {i.address ? (
                  <Link href={`/address/${encodeURIComponent(i.address)}`} className="font-mono text-ink hover:underline">
                    <Identifier value={i.address} />
                  </Link>
                ) : (
                  <span className="text-ink-faint">—</span>
                )}
                <span className="font-mono text-ink-muted">{formatBtc(i.amount)}</span>
              </li>
            )) : <li className="text-[12px] text-ink-faint">Unavailable</li>}
          </ul>
        </div>
        <div>
          <Kicker>Outputs</Kicker>
          <ul className="mt-2 space-y-1">
            {tx.outputs.length ? tx.outputs.map((o, idx) => (
              <li key={`${o.address}-${idx}`} className="flex justify-between gap-2 text-[12px]">
                {o.address ? (
                  <Link href={`/address/${encodeURIComponent(o.address)}`} className="font-mono text-ink hover:underline">
                    <Identifier value={o.address} />
                  </Link>
                ) : (
                  <span className="text-ink-faint">—</span>
                )}
                <span className="font-mono text-ink-muted">{formatBtc(o.amount)}</span>
              </li>
            )) : <li className="text-[12px] text-ink-faint">Unavailable</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-white/[0.04] py-1.5">
      <dt className="text-ink-faint">{k}</dt>
      <dd>{v}</dd>
    </div>
  );
}
