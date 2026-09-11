export type SearchKind = "transaction" | "address" | "entity" | "network" | "query";

const TXID = /^[0-9a-fA-F]{64}$/;
const SYNTH_TX = /^tx[_-]/i;
const SYNTH_WALLET = /^(benign_|merchant_|ransom_|mixer_|peel_|wallet_|user_)/i;
const BTC_ADDRESS = /^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$/;
const IP = /^(?:\d{1,3}\.){3}\d{1,3}$/;
const ENTITY = /^(ENT_|cluster[-_]?|#?\d{2,}|CLU)/i;

export function classifyQuery(raw: string): SearchKind {
  const q = raw.trim();
  if (!q) return "query";
  if (TXID.test(q) || SYNTH_TX.test(q)) return "transaction";
  if (BTC_ADDRESS.test(q) || SYNTH_WALLET.test(q)) return "address";
  if (IP.test(q)) return "network";
  if (ENTITY.test(q) || q.toLowerCase().startsWith("entity")) return "entity";
  return "query";
}

export function investigationHref(raw: string, kind?: SearchKind) {
  const q = raw.trim();
  const resolved = kind || classifyQuery(q);
  if (resolved === "transaction") return `/tx/${encodeURIComponent(q)}`;
  if (resolved === "address") return `/address/${encodeURIComponent(q)}`;
  if (resolved === "entity") {
    const id = q.replace(/^entity\s*#?/i, "").trim();
    return `/entity/${encodeURIComponent(id)}`;
  }
  if (resolved === "network") return `/network?q=${encodeURIComponent(q)}`;
  if (resolved === "query") return `/explorer?q=${encodeURIComponent(q)}`;
  return `/explorer?q=${encodeURIComponent(q)}`;
}

export function visualizerHref(raw: string) {
  const q = raw.trim();
  if (!q) return "/visualizer";
  return `/visualizer?q=${encodeURIComponent(q)}`;
}
