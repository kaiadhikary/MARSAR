import { cn } from "@/lib/cn";

export function LoadingState({
  label = "RESOLVING EVIDENCE",
  detail,
  className,
}: {
  label?: string;
  detail?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-3 py-16", className)}>
      <p className="text-[11px] tracking-[0.18em] text-ink-muted">{label}</p>
      <div className="h-px w-48 overflow-hidden bg-white/[0.06]">
        <div className="h-full w-1/3 animate-shimmer bg-gradient-to-r from-transparent via-accent to-transparent" />
      </div>
      {detail && <p className="font-mono text-[11px] text-ink-faint">{detail}</p>}
    </div>
  );
}

export function SkeletonRows({ rows = 8 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/[0.04]">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex h-9 items-center gap-3 px-3">
          <div className="h-2 w-12 overflow-hidden bg-white/[0.04]">
            <div className="h-full w-1/2 animate-shimmer bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
          </div>
          <div className="h-2 flex-1 overflow-hidden bg-white/[0.04]">
            <div className="h-full w-1/2 animate-shimmer bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
          </div>
        </div>
      ))}
    </div>
  );
}
