"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

export function ShimmerButton({
  children,
  className,
  loading,
  icon,
  disabled,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  loading?: boolean;
  icon?: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
}) {
  return (
    <motion.button
      type="button"
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.98 }}
      disabled={disabled || loading}
      onClick={onClick}
      className={cn(
        "group relative inline-flex h-9 items-center gap-2 overflow-hidden rounded-md px-[1px] text-[13px] font-medium text-white disabled:opacity-50",
        className
      )}
    >
      <span className="absolute inset-[-40%] animate-border-spin bg-[conic-gradient(from_90deg,transparent_0%,#8b6cff_18%,#3ec8d4_32%,transparent_48%)] opacity-70 transition-opacity group-hover:opacity-100" />
      <span className="relative flex h-[34px] items-center gap-2 rounded-[5px] bg-[#0b0f16] px-3.5">
        <span className="pointer-events-none absolute inset-0 overflow-hidden rounded-[5px]">
          <span className="absolute inset-y-0 w-1/2 -translate-x-full bg-gradient-to-r from-transparent via-white/10 to-transparent group-hover:animate-shimmer" />
        </span>
        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon}
        <span className="relative">{children}</span>
      </span>
    </motion.button>
  );
}
