import { cn } from "@/lib/cn";

export function Panel({
  children,
  className,
  padding = "p-0",
}: {
  children: React.ReactNode;
  className?: string;
  padding?: string;
}) {
  return <div className={cn("panel rounded-md", padding, className)}>{children}</div>;
}

export function Kicker({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">{children}</p>;
}
