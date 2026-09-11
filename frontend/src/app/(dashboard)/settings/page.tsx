"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AuthStatus } from "@/lib/types";

export default function SettingsPage() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [health, setHealth] = useState("checking…");
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    Promise.all([api.authStatus(), api.health()]).then(([auth, h]) => {
      setStatus(auth.data);
      setConnected(h.source === "api" && !!h.data);
      if (h.data) {
        const counts = h.data.record_counts;
        setHealth(
          `${h.data.status} · ${counts?.transactions ?? 0} tx · ${counts?.investigative_alerts ?? 0} alerts`
        );
      } else {
        setHealth("unreachable (start the local API on :8000)");
      }
    });
  }, []);

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h2 className="text-[15px] font-medium tracking-tight">System</h2>
        <p className="mt-1 text-[12px] text-ink-muted">Local engine status. No account is required to investigate.</p>
      </div>
      <div className="panel rounded-md px-4 text-[13px]">
        <Row k="Backend" v={connected ? "Connected" : "Disconnected"} />
        <Row k="Health" v={health} />
        <Row k="Air-gap" v={status?.airgap_active ? "Active" : "Unknown"} />
        <Row k="Auth required" v={status?.require_auth ? "Yes" : "No"} />
        <Row k="Evidence hashing" v={status?.tamper_evident_hashing || "SHA-256"} />
        <Row k="API proxy" v="/api/v1 → MARSAR_API_URL" />
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between border-b border-white/[0.04] py-2.5 last:border-0">
      <span className="text-ink-muted">{k}</span>
      <span className="font-mono text-[12px]">{v}</span>
    </div>
  );
}
