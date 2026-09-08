"use client";

// Cytoscape.js DAG interactive renderer.
import { useEffect, useRef } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import { GraphEdge, GraphNode } from "@/lib/api";
import { graphLayout, graphStylesheet } from "@/lib/cytoscape-config";

interface CanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeSelect?: (node: GraphNode | null) => void;
}

export default function Canvas({ nodes, edges, onNodeSelect }: CanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  // Create the Cytoscape instance once.
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: graphStylesheet,
      elements: [],
      wheelSensitivity: 0.2,
    });

    cy.on("tap", "node", (evt) => {
      const data = evt.target.data() as GraphNode;
      onNodeSelect?.(data);
    });
    cy.on("tap", (evt) => {
      if (evt.target === cy) onNodeSelect?.(null);
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Push new node/edge data in whenever the address search changes.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const elements: ElementDefinition[] = [
      ...nodes.map((n) => ({ data: { ...n } })),
      ...edges.map((e) => ({ data: { ...e } })),
    ];

    cy.elements().remove();
    cy.add(elements);
    cy.layout(graphLayout).run();
    cy.fit(undefined, 40);
  }, [nodes, edges]);

  return (
    <div
      ref={containerRef}
      className="h-[520px] w-full rounded-lg border border-slate-700 bg-slate-900"
    />
  );
}
