"use client";

import { Toaster } from "sonner";
import { CommandPalette } from "@/components/layout/command-palette";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <CommandPalette />
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          className:
            "panel-elevated !border-[var(--border)] !text-[var(--text)] font-sans text-sm",
        }}
      />
    </>
  );
}
