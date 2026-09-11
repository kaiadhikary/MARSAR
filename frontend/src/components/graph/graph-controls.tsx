"use client";

import { Maximize2, RotateCcw, Scan, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "@/components/ui/button";

export function GraphControls({
  onZoomIn,
  onZoomOut,
  onFit,
  onReset,
  onExpand,
}: {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
  onReset: () => void;
  onExpand: () => void;
}) {
  return (
    <div className="panel-elevated absolute bottom-3 left-3 z-10 flex items-center gap-1 rounded-md p-1">
      <Button variant="ghost" size="icon" onClick={onZoomIn} title="Zoom +">
        <ZoomIn className="h-3.5 w-3.5" />
      </Button>
      <Button variant="ghost" size="icon" onClick={onZoomOut} title="Zoom -">
        <ZoomOut className="h-3.5 w-3.5" />
      </Button>
      <Button variant="ghost" size="icon" onClick={onFit} title="Fit">
        <Scan className="h-3.5 w-3.5" />
      </Button>
      <Button variant="ghost" size="icon" onClick={onReset} title="Reset">
        <RotateCcw className="h-3.5 w-3.5" />
      </Button>
      <Button variant="ghost" size="icon" onClick={onExpand} title="Expand">
        <Maximize2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
