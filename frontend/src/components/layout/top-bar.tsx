"use client";

import { useEffect, useState } from "react";
import { Bell, Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";

export function TopBar({
  title,
  onSearch,
  onMenu,
}: {
  title: string;
  onSearch: () => void;
  onMenu?: () => void;
}) {
  const [apiLive, setApiLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = () => {
      api.health().then((r) => {
        if (!cancelled) setApiLive(r.source === "api" && r.data?.status === "healthy");
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
    <header className="sticky top-0 z-30 px-4 pt-3 lg:px-6">
      <div className="glass flex h-12 items-center gap-3 rounded-lg px-3">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenu}>
          <Menu className="h-4 w-4" />
        </Button>
        <h1 className="hidden min-w-[140px] text-[13px] font-medium tracking-tight text-ink sm:block">{title}</h1>
        <button
          onClick={onSearch}
          className={cn(
            "mx-auto flex h-8 w-full max-w-md items-center gap-2 rounded-md border border-white/[0.06] bg-black/20 px-3 text-[13px] text-ink-faint transition-colors hover:border-white/[0.12] hover:text-ink-muted"
          )}
        >
          <Search className="h-3.5 w-3.5" />
          <span className="flex-1 text-left">Search transaction, wallet, IP, cluster...</span>
          <kbd className="hidden rounded border border-white/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-ink-faint sm:inline">
            ⌘K
          </kbd>
        </button>
        <div className="ml-auto flex items-center gap-2">
          <span className="hidden items-center gap-1.5 rounded-md border border-white/[0.06] px-2 py-1 text-[10px] tracking-[0.12em] text-ink-muted md:flex">
            API
            <span className="font-mono text-ink">:8000</span>
          </span>
          <span
            className={cn(
              "hidden items-center gap-1.5 text-[10px] tracking-[0.12em] sm:flex",
              apiLive ? "text-safe" : "text-warning"
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", apiLive ? "bg-safe" : "bg-warning")} />
            {apiLive ? "API LIVE" : "API OFF"}
          </span>
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-4 w-4" />
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-accent" />
          </Button>
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-cyan text-[10px] font-medium">
            AY
          </div>
        </div>
      </div>
    </header>
  );
}
