export type HistoryKind = "transaction" | "address" | "entity" | "network" | "query";

export interface HistoryItem {
  id: string;
  kind: HistoryKind;
  label: string;
  href: string;
  at: number;
  risk?: number | null;
}

const KEY = "marsar.investigations";
const MAX = 24;

function read(): HistoryItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as HistoryItem[]) : [];
  } catch {
    return [];
  }
}

function write(items: HistoryItem[]) {
  localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX)));
}

export const investigationHistory = {
  list: read,
  push(item: Omit<HistoryItem, "at">) {
    const next = [{ ...item, at: Date.now() }, ...read().filter((x) => x.id !== item.id)].slice(0, MAX);
    write(next);
    window.dispatchEvent(new Event("marsar:history"));
  },
  clear() {
    write([]);
    window.dispatchEvent(new Event("marsar:history"));
  },
};
