"use client";

import { useCallback, useState } from "react";
import { FileUp } from "lucide-react";
import { cn } from "@/lib/cn";
import { GradientButton } from "@/components/magic/gradient-button";

export function DatasetUploader({
  onStart,
  loading,
}: {
  onStart: (file: File) => void;
  loading?: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [over, setOver] = useState(false);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }, []);

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        className={cn(
          "relative overflow-hidden rounded-lg border border-dashed border-white/[0.12] bg-[rgba(15,18,27,0.65)] px-8 py-16 text-center backdrop-blur-md transition-all duration-300",
          over && "border-accent/50 shadow-glow"
        )}
      >
        <div className={cn("pointer-events-none absolute inset-0 opacity-0 transition-opacity", over && "opacity-100")}>
          <div className="absolute inset-[-40%] animate-border-spin bg-[conic-gradient(from_0deg,transparent,rgba(109,92,255,0.35),transparent)]" />
        </div>
        <FileUp className="relative mx-auto h-6 w-6 text-ink-muted" />
        <h2 className="relative mt-4 text-lg font-medium tracking-tight">Import forensic dataset</h2>
        <p className="relative mt-1 text-[13px] text-ink-muted">Process CSV, JSON or XML datasets entirely offline.</p>
        <p className="relative mt-5 text-[13px] text-ink-faint">Drop files here.</p>
        <label className="relative mt-4 inline-flex cursor-pointer items-center rounded-md border border-white/[0.1] px-3 py-1.5 text-[13px] text-ink-muted hover:border-white/[0.18]">
          Browse files
          <input
            type="file"
            accept=".csv,.json,.xml"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>
      </div>
      {file && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/[0.08] bg-white/[0.02] px-4 py-3">
          <div>
            <p className="font-mono text-[13px]">{file.name}</p>
            <p className="mt-1 text-[11px] text-ink-faint">
              {(file.size / (1024 * 1024)).toFixed(2)} MB · READY
            </p>
          </div>
          <GradientButton loading={loading} onClick={() => onStart(file)}>
            Start Ingestion
          </GradientButton>
        </div>
      )}
    </div>
  );
}
