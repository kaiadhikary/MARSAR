"use client";

import { cn } from "@/lib/cn";
import { ChevronRight } from "lucide-react";

export function DataTable({
  columns,
  children,
  className,
}: {
  columns: string[];
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[720px] border-collapse text-left">
        <thead>
          <tr className="border-b border-white/[0.06] text-[10px] uppercase tracking-[0.16em] text-ink-faint">
            {columns.map((c) => (
              <th key={c} className="px-3 py-2 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function TableRow({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className="group cursor-pointer border-b border-white/[0.04] odd:bg-white/[0.015] transition-colors duration-150 hover:bg-white/[0.04]"
    >
      {children}
    </tr>
  );
}

export function Td({ children, mono, className }: { children: React.ReactNode; mono?: boolean; className?: string }) {
  return (
    <td className={cn("px-3 py-2 text-[12px] text-ink-muted", mono && "font-mono text-[11px] tabular-nums text-ink", className)}>
      {children}
    </td>
  );
}

export function RowAction() {
  return (
    <ChevronRight className="h-3.5 w-3.5 text-ink-faint transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-ink" />
  );
}
