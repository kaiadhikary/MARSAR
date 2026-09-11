"use client";

import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export function Drawer({
  title,
  kicker,
  children,
  onClose,
  wide,
}: {
  title: string;
  kicker?: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button className="absolute inset-0 bg-black/50" onClick={onClose} aria-label="Close panel" />
      <aside
        className={cn(
          "panel-elevated relative z-10 h-full w-full overflow-y-auto border-l p-5 animate-[slide-in-right_180ms_ease-out] md:max-w-md",
          wide && "md:max-w-lg"
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            {kicker && <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">{kicker}</p>}
            <h2 className="mt-1 font-mono text-[13px]">{title}</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="mt-5">{children}</div>
      </aside>
    </div>
  );
}
