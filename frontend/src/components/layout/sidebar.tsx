"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  Activity,
  Bell,
  Boxes,
  Database,
  Fingerprint,
  GitBranch,
  LayoutGrid,
  Network,
  ScrollText,
  Settings,
  Shield,
  Waypoints,
} from "lucide-react";
import { cn } from "@/lib/cn";

const primary = [
  { href: "/", label: "Overview", icon: LayoutGrid },
  { href: "/explorer", label: "Explorer", icon: Fingerprint },
  { href: "/visualizer", label: "Visualizer", icon: GitBranch },
  { href: "/tracer", label: "Tracer", icon: Waypoints },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/transactions", label: "Transactions", icon: Activity },
  { href: "/network", label: "Network", icon: Network },
  { href: "/clusters", label: "Clusters", icon: Boxes },
  { href: "/reports", label: "Reports", icon: ScrollText },
];

const secondary = [
  { href: "/dataset", label: "Dataset", icon: Database },
  { href: "/evidence", label: "Evidence", icon: Shield },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ collapsed, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();

  const item = (href: string, label: string, Icon: (typeof primary)[number]["icon"]) => {
    const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
    return (
      <Link
        key={href}
        href={href}
        onClick={onNavigate}
        className={cn(
          "relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] text-ink-muted transition-colors duration-200 hover:bg-white/[0.04] hover:text-ink",
          active && "text-ink"
        )}
      >
        {active && (
          <motion.span
            layoutId="nav-pill"
            className="absolute inset-0 rounded-md bg-gradient-to-r from-accent/18 to-transparent"
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
          />
        )}
        <Icon className={cn("relative h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5", active && "text-accent-2")} />
        {!collapsed && <span className="relative">{label}</span>}
      </Link>
    );
  };

  return (
    <aside
      className={cn(
        "glass-strong flex h-full flex-col border-r border-white/[0.06] px-3 py-4",
        collapsed ? "w-[72px]" : "w-[232px]"
      )}
    >
      <div className="px-2 pb-6">
        <p className="text-[15px] font-semibold tracking-[0.22em]">MARSAR</p>
        {!collapsed && (
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-ink-faint">Bitcoin Forensics</p>
        )}
      </div>
      <nav className="flex flex-1 flex-col gap-0.5">
        {primary.map((n) => item(n.href, n.label, n.icon))}
        <div className="my-3 h-px bg-white/[0.06]" />
        {secondary.map((n) => item(n.href, n.label, n.icon))}
      </nav>
      <div className="mt-auto space-y-1 px-2 pt-4 text-[11px] text-ink-faint">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-safe shadow-[0_0_8px_rgba(61,155,116,0.9)]" />
          {!collapsed && <span className="tracking-[0.12em]">OFFLINE MODE</span>}
        </div>
        {!collapsed && (
          <>
            <p>System Ready</p>
            <p className="font-mono">v2.0.0</p>
          </>
        )}
      </div>
    </aside>
  );
}
