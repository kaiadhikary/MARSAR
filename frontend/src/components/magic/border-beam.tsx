import { cn } from "@/lib/cn";

export function BorderBeam({
  children,
  active,
  className,
  tone = "cyan",
}: {
  children: React.ReactNode;
  active?: boolean;
  className?: string;
  tone?: "cyan" | "danger";
}) {
  return (
    <div className={cn("relative rounded-md p-[1px]", className)}>
      {active && (
        <span
          className={cn(
            "pointer-events-none absolute inset-[-40%] animate-border-spin opacity-80",
            tone === "danger"
              ? "bg-[conic-gradient(from_90deg,transparent_0%,#e24b4b_16%,transparent_42%)]"
              : "bg-[conic-gradient(from_90deg,transparent_0%,#3ec8ff_14%,#6d7cff_28%,transparent_46%)]"
          )}
        />
      )}
      <div className="relative rounded-[5px] bg-surface">{children}</div>
    </div>
  );
}
