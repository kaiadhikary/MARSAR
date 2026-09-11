import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function truncateId(value: string, head = 8, tail = 4) {
  if (!value) return "—";
  if (tail <= 0) return value.length > head ? `${value.slice(0, head)}…` : value;
  if (value.length <= head + tail + 1) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

export function formatBtc(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 6 })} BTC`;
}

export function formatPct(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  const pct = value <= 1 ? value * 100 : value;
  return `${pct.toFixed(1)}%`;
}

export function formatScore100(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return 0;
  return Math.round(value <= 1 ? value * 100 : value);
}

export function relativeTime(ts?: number | string | null) {
  if (!ts) return "—";
  const date = typeof ts === "number" ? new Date(ts * (ts < 10_000_000_000 ? 1000 : 1)) : new Date(ts);
  if (Number.isNaN(date.getTime())) return "—";
  const diff = Date.now() - date.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function formatDate(ts?: number | string | null) {
  if (!ts) return "—";
  const date = typeof ts === "number" ? new Date(ts * (ts < 10_000_000_000 ? 1000 : 1)) : new Date(ts);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
