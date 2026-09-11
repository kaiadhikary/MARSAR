"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bell, GitBranch, LayoutGrid, Waypoints } from "lucide-react";
import { cn } from "@/lib/cn";

const ITEMS = [
  { href: "/", label: "Home", icon: LayoutGrid },
  { href: "/explorer", label: "Explorer", icon: Activity },
  { href: "/visualizer", label: "Graph", icon: GitBranch },
  { href: "/tracer", label: "Tracer", icon: Waypoints },
  { href: "/alerts", label: "Alerts", icon: Bell },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-30 flex border-t border-white/[0.06] bg-[#08090b]/95 pb-[env(safe-area-inset-bottom)] lg:hidden">
      {ITEMS.map((n) => {
        const active = n.href === "/" ? pathname === "/" : pathname.startsWith(n.href);
        return (
          <Link
            key={n.href}
            href={n.href}
            className={cn(
              "flex flex-1 flex-col items-center gap-1 py-2 text-[11px] tracking-[0.08em] text-ink-faint",
              active && "text-ink"
            )}
          >
            <n.icon className="h-4 w-4" />
            {n.label}
          </Link>
        );
      })}
    </nav>
  );
}
