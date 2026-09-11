"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import type { EvidenceItem } from "@/lib/evidence";
import { Button } from "@/components/ui/button";
import { Kicker } from "@/components/ui/panel";

export function WhyFlagged({ items }: { items: EvidenceItem[] }) {
  const [open, setOpen] = useState<string | null>(items[0]?.id || null);
  if (!items.length) {
    return (
      <div className="panel rounded-md p-4">
        <Kicker>Why this is flagged</Kicker>
        <p className="mt-3 text-[13px] text-ink-muted">Not enough evidence in the local corpus to explain this identifier.</p>
      </div>
    );
  }

  return (
    <div className="panel rounded-md">
      <div className="border-b border-white/[0.06] px-4 py-3">
        <Kicker>Why this transaction is flagged</Kicker>
      </div>
      <ul>
        {items.map((item) => {
          const expanded = open === item.id;
          return (
            <li key={item.id} className="border-b border-white/[0.04] last:border-0">
              <button
                type="button"
                onClick={() => setOpen(expanded ? null : item.id)}
                className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors duration-150 hover:bg-white/[0.03]"
              >
                <span className="font-mono text-[11px] text-ink-faint">{item.index}</span>
                <span className="flex-1">
                  <span className="block text-[12px] tracking-[0.08em]">{item.title}</span>
                  <span
                    className={cn(
                      "grid transition-[grid-template-rows,opacity] duration-200 ease-out",
                      expanded ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                    )}
                  >
                    <span className="overflow-hidden">
                      <span className="mt-1 block text-[12px] text-ink-muted">{item.detail}</span>
                    </span>
                  </span>
                </span>
              </button>
              {expanded && item.href && (
                <div className="px-4 pb-3 pl-12">
                  <Button asChild size="sm" variant="outline">
                    <Link href={item.href}>{item.action || "Inspect"}</Link>
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
