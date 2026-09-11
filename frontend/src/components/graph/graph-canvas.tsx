"use client";

import { useEffect, useRef } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import { GraphControls } from "@/components/graph/graph-controls";
import type { GraphElements } from "@/lib/types";
import { riskBand } from "@/lib/risk";

const TYPE_COLOR: Record<string, string> = {
  ip: "#3ec8ff",
  transaction: "#6d7cff",
  wallet: "#7c5cff",
  entity: "#d4a017",
  cluster: "#d4a017",
  asn: "#7a8499",
  country: "#3d9b74",
};

interface GraphCanvasProps {
  elements: GraphElements;
  riskById?: Record<string, number>;
  onSelect?: (data: Record<string, unknown> | null) => void;
  onExpand?: () => void;
  loadingLabel?: string;
}

export function GraphCanvas({ elements, riskById = {}, onSelect, onExpand }: GraphCanvasProps) {
  const ref = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const dashRef = useRef(0);
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;

  useEffect(() => {
    if (!ref.current) return;
    const cy = cytoscape({
      container: ref.current,
      wheelSensitivity: 0.16,
      minZoom: 0.2,
      maxZoom: 2.8,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            color: "rgba(255,255,255,0.45)",
            "font-size": "8px",
            "font-family": "IBM Plex Mono, monospace",
            "text-valign": "bottom",
            "text-margin-y": 6,
            width: 18,
            height: 18,
            "border-width": 1.25,
            "background-color": "#111318",
            "border-color": "#6d7cff",
          },
        },
        { selector: "node[type = 'ip']", style: { "border-color": TYPE_COLOR.ip, shape: "diamond", width: 16, height: 16 } },
        { selector: "node[type = 'transaction']", style: { "border-color": TYPE_COLOR.transaction, shape: "round-rectangle", width: 22, height: 14 } },
        { selector: "node[type = 'wallet']", style: { "border-color": TYPE_COLOR.wallet, shape: "ellipse" } },
        { selector: "node[type = 'cluster'], node[type = 'entity']", style: { "border-color": TYPE_COLOR.entity, shape: "hexagon", width: 24, height: 24 } },
        { selector: "node[type = 'asn']", style: { "border-color": TYPE_COLOR.asn, shape: "rectangle", width: 18, height: 12 } },
        { selector: "node[type = 'country']", style: { "border-color": TYPE_COLOR.country, shape: "ellipse", width: 16, height: 16 } },
        { selector: "node[riskBand = 'medium']", style: { "border-color": "#d4a017" } },
        { selector: "node[riskBand = 'high']", style: { "border-color": "#e07a2f", "overlay-opacity": 0.08, "overlay-color": "#e07a2f" } },
        { selector: "node[riskBand = 'critical']", style: { "border-color": "#e24b4b", "overlay-opacity": 0.14, "overlay-color": "#e24b4b" } },
        {
          selector: "node:selected",
          style: { "border-width": 2.2, "overlay-opacity": 0.1, "overlay-color": "#3ec8ff" },
        },
        { selector: "node.dim", style: { opacity: 0.16 } },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "rgba(140,150,170,0.22)",
            "target-arrow-color": "rgba(140,150,170,0.35)",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.6,
            "curve-style": "bezier",
            label: "data(relation)",
            "font-size": 6,
            color: "rgba(255,255,255,0.28)",
            "text-rotation": "autorotate",
            "text-opacity": 0.5,
          },
        },
        {
          selector: "edge.flow",
          style: {
            "line-style": "dashed",
            "line-dash-pattern": [5, 7],
            "line-dash-offset": 0,
            "line-color": "rgba(62,200,255,0.35)",
          },
        },
        { selector: "edge.dim", style: { opacity: 0.06 } },
        { selector: "edge.hl", style: { width: 1.8, "line-color": "rgba(62,200,255,0.7)", opacity: 1 } },
      ],
      elements: [],
    });

    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      const neighborhood = node.closedNeighborhood();
      cy.elements().addClass("dim");
      neighborhood.removeClass("dim");
      neighborhood.edges().addClass("hl");
      selectRef.current?.(node.data());
    });
    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        cy.elements().removeClass("dim hl");
        selectRef.current?.(null);
      }
    });

    let raf = 0;
    const tick = () => {
      dashRef.current = (dashRef.current + 0.55) % 24;
      cy.edges(".flow").style("line-dash-offset", -dashRef.current);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    cyRef.current = cy;
    return () => {
      cancelAnimationFrame(raf);
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const mapped: ElementDefinition[] = [
      ...elements.nodes.map((n) => {
        const id = String(n.data.id);
        const score = riskById[id];
        return {
          data: {
            ...n.data,
            riskScore: score ?? null,
            riskBand: score != null ? riskBand(score) : "low",
          },
        };
      }),
      ...elements.edges.map((e) => {
        const rel = String(e.data.relation || "");
        const flow = ["INPUT_TO", "OUTPUT_TO", "OBSERVED", "BROADCASTED_FROM", "TRANSFERRED_TO", "SPENT_IN", "OBSERVED_BY", "LINKED"].includes(rel);
        return { data: e.data, classes: flow ? "flow" : undefined };
      }),
    ];
    cy.elements().remove();
    cy.add(mapped);
    cy.layout({
      name: "breadthfirst",
      directed: true,
      padding: 40,
      spacingFactor: 1.4,
      animate: true,
      animationDuration: 420,
    } as cytoscape.LayoutOptions).run();
    cy.fit(undefined, 48);
  }, [elements, riskById]);

  const cy = () => cyRef.current;

  return (
    <div className="relative h-full min-h-[420px] overflow-hidden rounded-md border border-white/[0.08] bg-[#08090b]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(70,80,255,0.08),transparent_62%)]" />
      <div ref={ref} className="absolute inset-0" />
      <GraphControls
        onZoomIn={() => cy()?.zoom(cy()!.zoom() * 1.15)}
        onZoomOut={() => cy()?.zoom(cy()!.zoom() * 0.87)}
        onFit={() => cy()?.fit(undefined, 48)}
        onReset={() => {
          cy()?.elements().removeClass("dim hl");
          cy()?.fit(undefined, 48);
        }}
        onExpand={() => {
          cy()?.layout({ name: "breadthfirst", directed: true, animate: true, animationDuration: 280 } as cytoscape.LayoutOptions).run();
          onExpand?.();
        }}
      />
    </div>
  );
}
