"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import { cn, truncateId } from "@/lib/cn";

export function Identifier({
  value,
  head = 8,
  tail = 4,
  className,
  copy = true,
}: {
  value?: string | null;
  head?: number;
  tail?: number;
  className?: string;
  copy?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  if (!value) return <span className="text-ink-faint">—</span>;

  async function copyId() {
    try {
      await navigator.clipboard.writeText(value as string);
      setCopied(true);
      toast.success("Copied");
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      toast.message("Clipboard unavailable");
    }
  }

  return (
    <span className={cn("inline-flex items-center gap-1.5 font-mono text-[12px] tabular-nums", className)}>
      <span title={value}>{truncateId(value, head, tail)}</span>
      {copy && (
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          copyId();
        }}
        className="rounded-sm p-0.5 text-ink-faint transition-colors duration-150 hover:text-ink"
        aria-label="Copy identifier"
      >
        {copied ? <Check className="h-3 w-3 text-safe" /> : <Copy className="h-3 w-3" />}
      </button>
      )}
    </span>
  );
}
