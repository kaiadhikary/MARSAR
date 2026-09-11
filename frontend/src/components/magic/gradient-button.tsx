"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

export function GradientButton({
  children,
  className,
  loading,
  icon,
  showArrow = true,
  tone = "primary",
  disabled,
  onClick,
  type = "button",
}: {
  children: ReactNode;
  className?: string;
  loading?: boolean;
  icon?: ReactNode;
  showArrow?: boolean;
  tone?: "primary" | "cyan";
  disabled?: boolean;
  onClick?: () => void;
  type?: "button" | "submit";
}) {
  return (
    <motion.button
      type={type}
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.98 }}
      disabled={disabled || loading}
      onClick={onClick}
      className={cn(
        "group relative inline-flex h-9 items-center gap-2 overflow-hidden rounded-md px-3.5 text-[13px] font-medium text-white",
        "shadow-[0_0_0_1px_rgba(255,255,255,0.08),0_8px_24px_-12px_rgba(109,92,255,0.55)]",
        "disabled:opacity-50",
        className
      )}
    >
      <span
        className={cn(
          "absolute inset-0 opacity-90 transition-opacity duration-300 group-hover:opacity-100",
          tone === "primary"
            ? "bg-[linear-gradient(135deg,#3c32e8_0%,#7a4dff_52%,#4a62ff_100%)]"
            : "bg-[linear-gradient(135deg,#1ea8b4_0%,#4a62ff_100%)]"
        )}
      />
      <span className="absolute inset-0 translate-x-[-120%] bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.18),transparent)] transition-transform duration-700 group-hover:translate-x-[120%]" />
      <span className="relative flex items-center gap-2">
        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon}
        {children}
        {showArrow && !loading && (
          <ArrowRight className="h-3.5 w-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
        )}
      </span>
    </motion.button>
  );
}
