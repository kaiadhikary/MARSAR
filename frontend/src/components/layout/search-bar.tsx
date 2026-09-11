"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, X } from "lucide-react";
import { api } from "@/lib/api";
import { investigationHistory, type HistoryItem } from "@/lib/history";
import { classifyQuery, investigationHref, type SearchKind } from "@/lib/search";
import { truncateId } from "@/lib/cn";
import { cn } from "@/lib/cn";

interface Suggestion {
  kind: SearchKind;
  label: string;
  href: string;
  detail?: string;
}

export function SearchBar({ compact, className }: { compact?: boolean; className?: string }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [corpus, setCorpus] = useState<Suggestion[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  useEffect(() => {
    const load = () => setHistory(investigationHistory.list());
    load();
    window.addEventListener("marsar:history", load);
    const onSlash = (e: KeyboardEvent) => {
      if (e.key === "/" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onSlash);
    return () => {
      window.removeEventListener("marsar:history", load);
      window.removeEventListener("keydown", onSlash);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      Promise.all([api.alerts(40), api.clusters()]).then(([alerts, clusters]) => {
      if (cancelled) return;
      const items: Suggestion[] = [];
      for (const a of alerts.data?.alerts || []) {
        items.push({
          kind: a.target_type === "wallet" ? "address" : "transaction",
          label: a.target_identifier,
          href: investigationHref(a.target_identifier),
          detail: a.primary_focus_area,
        });
      }
      for (const a of (alerts.data?.alerts || []).filter((x) => x.target_type === "txid").slice(0, 20)) {
        items.push({
          kind: "transaction",
          label: a.target_identifier,
          href: `/tx/${encodeURIComponent(a.target_identifier)}`,
          detail: a.primary_focus_area,
        });
      }
      for (const c of clusters.data?.clusters || []) {
        items.push({
          kind: "entity",
          label: c.cluster_id,
          href: `/entity/${encodeURIComponent(c.cluster_id)}`,
          detail: `${c.wallet_count} addresses`,
        });
      }
      setCorpus(items);
    });
    }, 400);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  const suggestions = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) {
      return history.slice(0, 6).map((h) => ({ kind: h.kind, label: h.label, href: h.href, detail: "Recent" }));
    }
    const classified = classifyQuery(q);
    const direct: Suggestion = {
      kind: classified,
      label: q.trim(),
      href: investigationHref(q),
      detail: classified === "query" ? "Search corpus" : classified.toUpperCase(),
    };
    const matches = corpus.filter((c) => c.label.toLowerCase().includes(s)).slice(0, 8);
    return [direct, ...matches.filter((m) => m.label !== q.trim())];
  }, [q, corpus, history]);

  function go(item?: Suggestion) {
    const target = item || suggestions[0];
    if (!target) {
      setOpen(true);
      return;
    }
    investigationHistory.push({
      id: target.label,
      kind: target.kind,
      label: target.label,
      href: target.href,
    });
    router.push(target.href);
    setOpen(false);
    setQ("");
  }

  return (
    <div ref={rootRef} className={cn("relative w-full", compact ? "max-w-xl" : "mx-auto max-w-2xl", className)}>
      <div
        className={cn(
          "flex items-center gap-2 border border-white/[0.12] bg-surface/80",
          compact ? "h-10 rounded-md px-3" : "h-14 rounded-full px-5"
        )}
      >
        <Search className={cn("shrink-0 text-ink-faint", compact ? "h-3.5 w-3.5" : "h-4 w-4")} />
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              go();
            }
            if (e.key === "Escape") {
              setOpen(false);
              inputRef.current?.blur();
            }
          }}
          placeholder="Search transaction ID, address, entity, IP..."
          className={cn(
            "w-full bg-transparent outline-none placeholder:text-ink-faint",
            compact ? "h-10 text-[14px]" : "h-14 text-[16px]"
          )}
        />
        {q && (
          <button type="button" onClick={() => setQ("")} className="text-ink-faint hover:text-ink">
            <X className="h-3.5 w-3.5" />
          </button>
        )}
        <kbd className="hidden rounded-sm border border-white/[0.08] px-1.5 py-0.5 font-mono text-[11px] text-ink-faint sm:inline">
          /
        </kbd>
      </div>
      {open && (q || suggestions.length > 0) && (
        <div className="panel-elevated absolute z-40 mt-2 w-full overflow-hidden rounded-xl">
          {!suggestions.length && q && (
            <p className="px-3 py-4 text-[13px] text-ink-muted">No matching identifiers in the local corpus.</p>
          )}
          {suggestions.map((s) => (
              <button
                key={`${s.kind}-${s.label}`}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => go(s)}
                className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left transition-colors duration-150 hover:bg-white/[0.04]"
              >
                <span>
                  <span className="block text-[11px] tracking-[0.14em] text-ink-faint">{s.kind.toUpperCase()}</span>
                  <span className="font-mono text-[13px]">{truncateId(s.label, 14, 6)}</span>
                </span>
                {s.detail && <span className="text-[12px] text-ink-faint">{s.detail}</span>}
              </button>
            ))}
        </div>
      )}
    </div>
  );
}
