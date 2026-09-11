"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu } from "lucide-react";
import { SearchBar } from "@/components/layout/search-bar";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/explorer", label: "Explorer" },
  { href: "/visualizer", label: "Visualizer" },
  { href: "/tracer", label: "Tracer" },
  { href: "/alerts", label: "Alerts" },
  { href: "/patterns", label: "Patterns" },
  { href: "/reports", label: "Reports" },
];

const MORE = [
  { href: "/network", label: "Network" },
  { href: "/clusters", label: "Entities" },
  { href: "/dataset", label: "Dataset" },
  { href: "/settings", label: "System" },
];

export function TopNav({ onMenu }: { onMenu?: () => void }) {
  const pathname = usePathname();
  const [live, setLive] = useState(false);
  const [more, setMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      api.health().then((r) => {
        if (!cancelled) setLive(r.source === "api" && r.data?.status === "healthy");
      });
    };
    check();
    const id = window.setInterval(check, 15_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-[#08090b]/90 backdrop-blur-md">
      <div className="flex h-14 items-center gap-4 px-3 lg:px-4">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenu}>
          <Menu className="h-4 w-4" />
        </Button>
        <Link href="/" className="shrink-0 text-[15px] font-bold uppercase tracking-[0.22em]">
          MARSAR
        </Link>
        <nav className="hidden items-center gap-1 lg:flex">
          {NAV.map((n) => {
            const active = pathname === n.href || pathname.startsWith(`${n.href}/`);
            return (
              <Link
                key={n.href}
                href={n.href}
                className={cn(
                  "rounded-sm px-2.5 py-1 text-[13px] font-medium uppercase tracking-[0.12em] text-ink-muted transition-colors duration-150 hover:text-ink",
                  active && "bg-white/[0.05] text-ink"
                )}
              >
                {n.label}
              </Link>
            );
          })}
          <div className="relative">
            <button
              type="button"
              onClick={() => setMore((v) => !v)}
              className="rounded-sm px-2.5 py-1 text-[13px] font-medium uppercase tracking-[0.12em] text-ink-muted hover:text-ink"
            >
              More
            </button>
            {more && (
              <div className="panel-elevated absolute left-0 top-8 z-40 min-w-[140px] rounded-md py-1">
                {MORE.map((n) => (
                  <Link
                    key={n.href}
                    href={n.href}
                    onClick={() => setMore(false)}
                    className="block px-3 py-1.5 text-[12px] text-ink-muted hover:bg-white/[0.04] hover:text-ink"
                  >
                    {n.label}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </nav>
        <div className="mx-auto hidden min-w-0 flex-1 justify-center md:flex">
          <SearchBar compact />
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className={cn("flex items-center gap-1.5 text-[11px] tracking-[0.14em]", live ? "text-safe" : "text-warning")}>
            <span className={cn("h-1.5 w-1.5 rounded-full", live ? "bg-safe" : "bg-warning")} />
            {live ? "ONLINE" : "OFFLINE"}
          </span>
        </div>
      </div>
      <div className="border-t border-white/[0.04] px-3 py-2 md:hidden">
        <SearchBar compact />
      </div>
    </header>
  );
}
