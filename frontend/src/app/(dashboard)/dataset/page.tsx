"use client";

import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { DatasetUploader } from "@/components/dataset/dataset-uploader";
import { INGEST_STEPS, PipelineStepper } from "@/components/pipeline/pipeline-stepper";
import { GlassCard } from "@/components/ui/glass-card";

export default function DatasetPage() {
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(-1);
  const [complete, setComplete] = useState(-1);

  async function start(file: File) {
    setLoading(true);
    setActive(0);
    setComplete(-1);
    const timer = window.setInterval(() => {
      setActive((s) => {
        const next = Math.min(INGEST_STEPS.length - 1, s + 1);
        setComplete(next - 1);
        return next;
      });
    }, 700);
    try {
      const res = await api.ingestFile(file);
      const pipeline = await api.runPipeline();
      toast.success("Dataset imported and analyzed", {
        description: `${res.transactions_ingested.toLocaleString()} transactions · ${pipeline.alerts_generated} alerts`,
      });
      setActive(INGEST_STEPS.length - 1);
      setComplete(INGEST_STEPS.length - 1);
    } catch {
      toast.error("Ingestion failed — confirm the local API is running on port 8000.");
      setActive(-1);
      setComplete(-1);
    } finally {
      window.clearInterval(timer);
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <DatasetUploader onStart={start} loading={loading} />
      {(active >= 0 || complete >= 0) && (
        <GlassCard hover={false} padding="p-5">
          <p className="mb-4 text-[11px] tracking-[0.18em] text-ink-faint">INGESTION PIPELINE</p>
          <PipelineStepper steps={INGEST_STEPS} active={active} completeThrough={complete} />
        </GlassCard>
      )}
    </div>
  );
}
