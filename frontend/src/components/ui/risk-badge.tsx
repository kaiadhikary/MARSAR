import { cn } from "@/lib/cn";
import { riskBand, riskLabel, type RiskBand } from "@/lib/risk";

export function RiskBadge({ score, band, className }: { score?: number | null; band?: RiskBand; className?: string }) {
  const resolved = band || riskBand(score);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[10px] font-medium tracking-[0.14em]",
        resolved === "critical" && "text-danger",
        resolved === "high" && "text-orange",
        resolved === "medium" && "text-warning",
        resolved === "low" && "text-ink-muted",
        className
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          resolved === "critical" && "bg-danger shadow-[0_0_8px_rgba(226,75,75,0.7)]",
          resolved === "high" && "bg-orange shadow-[0_0_7px_rgba(224,122,47,0.55)]",
          resolved === "medium" && "bg-warning",
          resolved === "low" && "bg-safe/70"
        )}
      />
      {riskLabel(resolved)}
    </span>
  );
}
