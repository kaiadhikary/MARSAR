import type { StylesheetJson, LayoutOptions } from "cytoscape";

export const graphStylesheet: StylesheetJson = [
  {
    selector: "node",
    style: {
      "background-color": "#2563eb",
      label: "data(label)",
      color: "#e5e7eb",
      "font-size": "9px",
      "text-valign": "bottom",
      "text-margin-y": 6,
      width: 32,
      height: 32,
      "border-width": 2,
      "border-color": "#1e40af",
    },
  },
  {
    selector: 'node[type = "wallet"]',
    style: {
      "background-color": "#2563eb",
      "border-color": "#1e40af",
      shape: "ellipse",
    },
  },
  {
    selector: 'node[type = "transaction"]',
    style: {
      "background-color": "#7c3aed",
      "border-color": "#5b21b6",
      shape: "diamond",
      width: 28,
      height: 28,
    },
  },
  {
    selector: 'node[type = "ip"]',
    style: {
      "background-color": "#0891b2",
      "border-color": "#0e7490",
      shape: "hexagon",
      width: 30,
      height: 30,
    },
  },
  {
    selector: "node[?is_root]",
    style: {
      "background-color": "#f59e0b",
      "border-color": "#b45309",
      width: 44,
      height: 44,
      "font-size": "10px",
      "font-weight": "bold",
    },
  },
  {
    selector: "node[?is_blacklisted]",
    style: {
      "background-color": "#dc2626",
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
      opacity: 0.8,
    },
  },
];

export const graphLayout: LayoutOptions = {
  name: "cose",
  animate: true,
  nodeRepulsion: 8000,
  idealEdgeLength: 80,
  padding: 40,
} as LayoutOptions;
