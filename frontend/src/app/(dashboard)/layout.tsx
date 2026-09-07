"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api";

const NAV = [
  { href: "/", label: "Command Center", icon: "⬡" },
  { href: "/investigator", label: "Link Analysis", icon: "◈" },
  { href: "/alerts", label: "Investigative Leads", icon: "⚠" },
  { href: "/reports", label: "STR Reports", icon: "📄" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
    const id = setInterval(() => {
      fetchHealth()
        .then(() => setOnline(true))
        .catch(() => setOnline(false));
    }, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-800 bg-slate-950">
        <div className="border-b border-slate-800 p-5">
          <p className="text-lg font-bold tracking-tight text-slate-100">
            MARSAR
          </p>
          <p className="text-[10px] uppercase tracking-widest text-slate-500">
            Bitcoin Forensic Intelligence
          </p>
          <div className="mt-3 flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                online === null
                  ? "bg-slate-600"
                  : online
                    ? "bg-emerald-500"
                    : "bg-red-500"
              }`}
            />
            <span className="text-[10px] text-slate-500">
              {online === null
                ? "Checking…"
                : online
                  ? "Backend online · Air-gap mode"
                  : "Backend offline"}
            </span>
          </div>
        </div>

        <nav className="flex-1 p-3">
          <ul className="space-y-1">
            {NAV.map(({ href, label, icon }) => {
              const active =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors ${
                      active
                        ? "bg-blue-600/20 text-blue-300"
                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`}
                  >
                    <span className="text-xs opacity-70">{icon}</span>
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t border-slate-800 p-4 text-[10px] leading-relaxed text-slate-600">
          Offline P2P + blockchain correlation · ML anomaly detection ·
          explainable alerts
        </div>
      </aside>

      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  );
}
