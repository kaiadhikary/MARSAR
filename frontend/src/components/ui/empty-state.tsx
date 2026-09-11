import { Inbox } from "lucide-react";
import { cn } from "@/lib/cn";

export function EmptyState({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-16 text-center", className)}>
      <Inbox className="mb-4 h-4 w-4 text-ink-faint" />
      <h3 className="text-[11px] font-medium tracking-[0.16em] text-ink">{title}</h3>
      {description && <p className="mt-2 max-w-sm text-[13px] text-ink-muted">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
