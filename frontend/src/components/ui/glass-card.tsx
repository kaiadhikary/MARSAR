import { cn } from "@/lib/cn";

export function GlassCard({
  className,
  hover = false,
  padding = "p-4",
  children,
  onClick,
}: {
  className?: string;
  hover?: boolean;
  padding?: string;
  children: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "panel rounded-md",
        hover && "cursor-pointer transition-colors duration-150 hover:bg-white/[0.03]",
        padding,
        className
      )}
    >
      {children}
    </div>
  );
}
