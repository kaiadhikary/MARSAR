"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Command } from "cmdk";
import {
  Activity,
  Bell,
  Database,
  GitBranch,
  Search,
  Settings,
  Shield,
  Trash2,
  Waypoints,
} from "lucide-react";
import { classifyQuery, investigationHref, visualizerHref } from "@/lib/search";
import { investigationHistory } from "@/lib/history";
import { truncateId } from "@/lib/cn";

const COMMANDS = [
  { id: "tx", label: "Search transaction", href: "/explorer", icon: Search },
  { id: "wallet", label: "Search address", href: "/explorer", icon: Search },
  { id: "visualizer", label: "Open Visualizer", href: "/visualizer", icon: GitBranch },
  { id: "tracer", label: "Open Tracer", href: "/tracer", icon: Waypoints },
  { id: "alerts", label: "View Alerts", href: "/alerts", icon: Bell },
  { id: "patterns", label: "View Patterns", href: "/patterns", icon: Shield },
  { id: "reports", label: "Open Reports", href: "/reports", icon: Activity },
  { id: "dataset", label: "Import Dataset", href: "/dataset", icon: Database },
  { id: "settings", label: "System status", href: "/settings", icon: Settings },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const router = useRouter();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("keydown", onKey);
    window.addEventListener("marsar:open-command", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("marsar:open-command", onOpen);
    };
  }, []);

  const classified = classifyQuery(q);
  const items = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return COMMANDS;
    return COMMANDS.filter((c) => c.label.toLowerCase().includes(s));
  }, [q]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/55 pt-[16vh]">
      <button className="absolute inset-0 cursor-default" onClick={() => setOpen(false)} aria-label="Close" />
      <Command className="panel-elevated relative z-10 w-[min(560px,92vw)] overflow-hidden rounded-md" shouldFilter={false}>
        <div className="flex items-center gap-2 border-b border-white/[0.06] px-3">
          <Search className="h-4 w-4 text-ink-faint" />
          <Command.Input
            autoFocus
            value={q}
            onValueChange={setQ}
            placeholder="Search identifier or command..."
            className="h-11 w-full bg-transparent text-sm outline-none placeholder:text-ink-faint"
            onKeyDown={(e) => {
              if (e.key === "Enter" && q.trim() && classified !== "query") {
                e.preventDefault();
                const href = investigationHref(q);
                investigationHistory.push({ id: q.trim(), kind: classified, label: q.trim(), href });
                router.push(href);
                setOpen(false);
                setQ("");
              }
            }}
          />
        </div>
        <Command.List className="max-h-80 overflow-auto p-1.5">
          {q.trim() && (
            <>
              <Command.Item
                value={`investigate ${q}`}
                onSelect={() => {
                  const href = investigationHref(q);
                  investigationHistory.push({ id: q.trim(), kind: classified, label: q.trim(), href });
                  router.push(href);
                  setOpen(false);
                  setQ("");
                }}
                className="flex cursor-pointer items-center justify-between rounded-sm px-3 py-2 text-[13px] text-ink aria-selected:bg-white/[0.05]"
              >
                <span>Investigate {truncateId(q.trim(), 16, 8)}</span>
                <span className="text-[10px] tracking-[0.12em] text-ink-faint">{classified.toUpperCase()}</span>
              </Command.Item>
              <Command.Item
                value={`visualize ${q}`}
                onSelect={() => {
                  const href = visualizerHref(q);
                  investigationHistory.push({ id: q.trim(), kind: classified, label: q.trim(), href });
                  router.push(href);
                  setOpen(false);
                  setQ("");
                }}
                className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-[13px] text-ink-muted aria-selected:bg-white/[0.05] aria-selected:text-ink"
              >
                <GitBranch className="h-3.5 w-3.5" />
                Visualize {truncateId(q.trim(), 16, 8)}
              </Command.Item>
            </>
          )}
          <Command.Empty className="px-3 py-8 text-center text-[13px] text-ink-muted">No matches.</Command.Empty>
          {items.map((c) => (
            <Command.Item
              key={c.id}
              value={c.label}
              onSelect={() => {
                router.push(c.href);
                setOpen(false);
                setQ("");
              }}
              className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-[13px] text-ink-muted aria-selected:bg-white/[0.05] aria-selected:text-ink"
            >
              <c.icon className="h-3.5 w-3.5" />
              {c.label}
            </Command.Item>
          ))}
          <Command.Item
            value="Clear investigation"
            onSelect={() => {
              investigationHistory.clear();
              setOpen(false);
            }}
            className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-[13px] text-ink-muted aria-selected:bg-white/[0.05] aria-selected:text-ink"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear investigation history
          </Command.Item>
        </Command.List>
      </Command>
    </div>
  );
}

export function openCommandPalette() {
  window.dispatchEvent(new Event("marsar:open-command"));
}
