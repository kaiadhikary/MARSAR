// Node styles, edge weights, and color ramps for the Cytoscape graph canvas.
import type { StylesheetJson, LayoutOptions } from "cytoscape";

export const graphStylesheet: StylesheetJson = [
  {
    selector: "node",
    style: {
      "background-color": "#2563eb", // blue-600 (normal address)
      label: "data(label)",
      color: "#e5e7eb",
      "font-size": "10px",
      "text-valign": "bottom",
      "text-margin-y": 6,
      width: 34,
      height: 34,
      "border-width": 2,
      "border-color": "#1e40af",
    },
  },
  {
    selector: "node[?is_root]",
    style: {
      "background-color": "#f59e0b", // amber-500 — cluster root
      "border-color": "#b45309",
      width: 46,
      height: 46,
    },
  },
  {
    selector: "node[?is_blacklisted]",
    style: {
      "background-color": "#dc2626", // red-600 — sanctioned/scam hit
      "border-color": "#7f1d1d",
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-width": 4,
      "border-color": "#ffffff",
    },
  },
  {
    selector: "edge",
    style: {
      width: 2,
      "line-color": "#64748b",
      "target-arrow-color": "#64748b",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
    },
  },
];

export const graphLayout: LayoutOptions = {
  name: "concentric",
  concentric: (node: any) => (node.data("is_root") ? 2 : 1),
  levelWidth: () => 1,
  minNodeSpacing: 60,
  animate: true,
} as LayoutOptions;
