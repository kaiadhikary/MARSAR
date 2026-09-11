"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { TopNav } from "@/components/layout/top-nav";
import { MobileNav } from "@/components/layout/mobile-nav";
import { cn } from "@/lib/cn";

const LINKS = [
  { href: "/explorer", label: "Explorer" },
  { href: "/visualizer", label: "Visualizer" },
  { href: "/tracer", label: "Tracer" },
  { href: "/alerts", label: "Alerts" },
  { href: "/patterns", label: "Patterns" },
  { href: "/reports", label: "Reports" },
  { href: "/network", label: "Network" },
  { href: "/clusters", label: "Entities" },
  { href: "/dataset", label: "Dataset" },
  { href: "/settings", label: "System" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const graphMode = pathname.startsWith("/visualizer") || pathname.startsWith("/investigator");

  return (
    <div className="marsar-bg relative min-h-screen">
      <div className="relative flex min-h-screen flex-col">
        <TopNav onMenu={() => setMobileOpen(true)} />
        {mobileOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <button className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
            <div className="panel-elevated relative h-full w-[220px] p-4">
              <p className="mb-4 text-[13px] font-semibold tracking-[0.2em]">MARSAR</p>
              <nav className="flex flex-col gap-1">
                {LINKS.map((n) => (
                  <Link
                    key={n.href}
                    href={n.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "rounded-sm px-2 py-2 text-[13px] text-ink-muted",
                      pathname.startsWith(n.href) && "bg-white/[0.05] text-ink"
                    )}
                  >
                    {n.label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        )}
        <main className={cn(graphMode ? "flex min-h-0 flex-1 flex-col p-3 pb-16 lg:p-4 lg:pb-4" : "px-4 pb-20 pt-5 lg:px-6 lg:pb-10")}>
          {children}
        </main>
        <MobileNav />
      </div>
    </div>
  );
}
