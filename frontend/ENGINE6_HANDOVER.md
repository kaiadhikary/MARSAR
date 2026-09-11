# MARSAR Engine 6 — Handover Document

**Engine:** Forensic Dossier & Legal Compliance Engine  
**Report version:** `E6-1.0`  
**Canonicalization version:** `1.0`  
**Hash algorithm:** SHA-256  
**Artefact format:** standalone HTML (not PDF)  
**Date of this handover:** 6 September 2026  

This document describes **what was actually implemented** in this repository. It supersedes earlier Engine 6 notes that described JWT-gated PDF export via WeasyPrint.

---

## 1. Purpose

Engine 6 turns **already persisted** Engines 1–5 evidence into a deterministic, auditable forensic dossier.

It does **not**:

- re-run clustering (Engine 2)
- re-run CoinJoin / demixing (Engine 3)
- re-run typology heuristics (Engine 4)
- recompute Engine 5 risk (`compute_risk_score` is never imported by Engine 6)

If Engine 5 stored `risk_score = 72.4` and `risk_verdict = HIGH_RISK`, the dossier prints **exactly those values**.

The HTML file is meant to be understandable **without** the live MARSAR UI.

---

## 2. What is implemented vs future / unused

| Item | Status |
| --- | --- |
| Evidence contract from SQLite | Implemented |
| Canonical UTF-8 JSON | Implemented |
| SHA-256 of hashed body | Implemented |
| `verify_evidence_hash()` | Implemented |
| Jinja2 HTML dossier | Implemented |
| Write HTML to `backend/app/reports/output/` | Implemented |
| CLI `generate_html_report.py` (no HTTP) | Implemented |
| `POST /api/v1/export-str` returns HTML | Implemented |
| Reports / Investigator / Alerts UI | Implemented |
| `flagged_transactions` table | Implemented |
| No login required for export | Implemented (current product decision) |
| WeasyPrint PDF | **Removed** (GTK/`libgobject` failed on this Windows host) |
| Merkle tree | **Not implemented** (`merkle_root` is always `null`) |
| JWT on export | **Not required** (`app/api/v1/auth.py` still exists but export does not use it) |
| Multi-hop FIFO taint % | **Not implemented** (never fabricated) |
| Full historical DAG | **Not implemented** (vin→vout of this TX only) |

---

## 3. Architecture

```
TXID (must already be in SQLite)
        │
        ├─ CLI:  python generate_html_report.py <txid>
        └─ UI / HTTP:  POST /api/v1/export-str  { "txid": "..." }
                │
                ▼
        collect_evidence()     # app/reports/evidence.py
                │
                ▼
        hashable_snapshot()    # exclude integrity + audit.generated_at
        canonicalize UTF-8 JSON
        SHA-256
                │
                ▼
        Jinja2 str_template.html
                │
                ▼
        Write  app/reports/output/MARSAR-STR-<txid16>.html
        Return HTML (+ integrity headers if HTTP)
```

Engine 6 is a **reader**. The writer is `backend/run_worker.py` (Engines 1–5 → SQLite).

---

## 4. Files (created / modified for Engine 6)

### Backend — Engine 6 core

| Path | Role |
| --- | --- |
| `backend/app/reports/__init__.py` | `REPORT_VERSION`, `CANONICALIZATION_VERSION`, `HASH_ALGORITHM` |
| `backend/app/reports/evidence.py` | Evidence contract from SQLite |
| `backend/app/reports/hashing.py` | Normalize, canonicalize, SHA-256, verify |
| `backend/app/reports/generator.py` | Orchestration + HTML file write |
| `backend/app/reports/templates/str_template.html` | Presentation only |
| `backend/app/reports/output/` | Generated HTML artefacts |
| `backend/app/api/v1/compliance.py` | Export + list endpoints (no auth) |
| `backend/generate_html_report.py` | CLI, no HTTP |

### Backend — persistence / worker (smallest integration)

| Path | Role |
| --- | --- |
| `backend/app/db/sqlite_client.py` | Engine 6 columns, `transaction_ios`, `flagged_transactions` |
| `backend/run_worker.py` | Persists I/O order, demix JSON, typology JSON, blacklist hits, change findings |
| `backend/app/ingestion/parser.py` | Passes `block_height` from existing `status` if present |

### Backend — leftover auth (not used by export)

| Path | Role |
| --- | --- |
| `backend/app/core/security.py` | JWT helpers (optional future) |
| `backend/app/api/v1/auth.py` | `POST /api/v1/auth/login` still mounted |
| `backend/app/core/config.py` | `ANALYST_USERNAME` / `ANALYST_PASSWORD` unused by current UI |

### Frontend

| Path | Role |
| --- | --- |
| `frontend/src/lib/api.ts` | `exportStrReport`, flagged/transaction lists |
| `frontend/src/app/(dashboard)/reports/page.tsx` | TXID → HTML dossier |
| `frontend/src/app/(dashboard)/investigator/page.tsx` | Same export on investigator |
| `frontend/src/app/(dashboard)/alerts/page.tsx` | Flagged table |

### Tests / docs

| Path | Role |
| --- | --- |
| `backend/tests/test_engine6.py` | Engine 6 tests |
| `ENGINE6_HANDOVER.md` | This document (repo root) |
| `backend/ENGINE6.md` | Same content for backend-only copies |

**Not changed (must stay green):** Engine 5 scoring formula, thresholds, feature extractor, inference.

---

## 5. Data flow and upstream provenance

| Dossier section | Upstream | SQLite |
| --- | --- | --- |
| TXID, vin/vout, prev_txid/prev_vout, values | Engine 1 | `transactions` + `transaction_ios` (fallback: `transaction_addresses`) |
| Cluster id, root, members, change findings | Engine 2 | `clusters`, `address_clusters`, `change_findings_json` |
| CoinJoin flag, Shannon entropy, demix links | Engine 3 | `is_coinjoin`, `shannon_entropy`, `demix_json` |
| peeling_chain / scatter_gather / rapid_velocity | Engine 4 | `typology_findings_json` (else flag names only) |
| Risk score, verdict, component scores, flags, ML probability | Engine 5 | `risk_score`, `risk_verdict`, `taint_score`, `typology_score`, `mixer_penalty_score`, `ml_probability`, `typology_flags` |
| Direct blacklist hits | Seed lookup at ingest | `blacklist_hits_json` / `blacklist_hit` |
| Flagged list in UI | Engine 5 verdict | `flagged_transactions` |

Missing optional fields render as **Unavailable** / `null` / empty lists. Engine 6 does not invent KYC, timestamps, taint percentages, or legal conclusions.

CoinJoin is labeled **`observed_forensic_indicator`**. `legal_conclusion` is always `null`.

---

## 6. Evidence contract

Conceptual snapshot (fields omitted when unavailable):

```json
{
  "canonicalization_version": "1.0",
  "case": { "case_id": null, "investigator_note": null },
  "transaction": {
    "txid": "...",
    "inputs": [{ "vin_index": 0, "prev_txid": "...", "prev_vout": 0, "address": "...", "value_sats": 0 }],
    "outputs": [{ "vout_index": 0, "address": "...", "value_sats": 0, "script_type": null }],
    "fee_sats": null,
    "fee_rate_sat_vb": null,
    "observed_at": null,
    "confirmed": null,
    "block_height": null,
    "locktime": null,
    "inputs_count": null,
    "outputs_count": null
  },
  "cluster": {
    "cluster_id": null,
    "root_address": null,
    "member_count": null,
    "members": [],
    "change_findings": [],
    "cluster_risk_score": null
  },
  "coinjoin": {
    "is_coinjoin": false,
    "entropy": null,
    "classification": "observed_forensic_indicator",
    "legal_conclusion": null,
    "demixing": []
  },
  "typology": { "findings": [] },
  "blacklist": { "hits": [] },
  "risk": {
    "taint_score": null,
    "typology_score": null,
    "ml_probability": null,
    "mixer_penalty_score": null,
    "risk_score": null,
    "verdict": null,
    "flags": [],
    "component_weights": { "taint": 0.40, "typology": 0.25, "ml_probability": 0.20, "mixer_penalty": 0.15 },
    "source": "engine5_persisted"
  },
  "graph": { "paths": [], "summary": {} },
  "audit": {
    "report_version": "E6-1.0",
    "application_version": "1.0.0",
    "investigator": null,
    "session": null,
    "generated_at": null
  },
  "integrity": {
    "canonicalization_version": "1.0",
    "hash_algorithm": "SHA-256",
    "evidence_sha256": null,
    "merkle_root": null
  }
}
```

`component_weights` are **copied from settings for display**. They are not used to recompute the score.

---

## 7. Canonicalization and SHA-256

Never hash `str(dict)` or `repr(dict)`.

1. `normalize_evidence()` — JSON-safe types; NaN/Inf → `null`
2. `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`
3. Encode UTF-8
4. `SHA-256` of those **exact bytes**

**Hashed sections:** `canonicalization_version`, `case`, `transaction`, `cluster`, `coinjoin`, `typology`, `blacklist`, `risk`, `graph`, `audit` **without** `generated_at`.

**Not hashed:** `integrity` (including the digest itself), `audit.generated_at`.

Same forensic evidence → same SHA-256 across exports. Changing a hashed field changes the digest.

Vin/vout **array order is preserved**. Cluster members and blacklist hits are sorted for digest stability.

Independent check: `verify_evidence_hash(snapshot, expected_hash)`.

Known vector used in tests: SHA-256(`b"abc"`) = `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`.

---

## 8. Engine 5 contract (authoritative; do not change in E6)

Formula (in `app/engine/scoring.py` / settings — **Engine 6 only reads persisted results**):

```
Risk = 0.40 × Taint + 0.25 × Typology + 0.20 × ML Probability + 0.15 × Mixer Penalty
```

Typology severities: `peeling_chain = 100`, `scatter_gather = 100`, `rapid_velocity = 70`.

Verdicts: `< 30` LICIT, `30–69` SUSPICIOUS, `70+` HIGH_RISK.

`ml_probability` in SQLite is the raw model probability in `[0, 1]`, not the 0–100 layer score.

---

## 9. HTML report structure

Template: `backend/app/reports/templates/str_template.html` (no SQL, no scoring, no hashing).

1. Case summary (TXID, case id, generated at, risk, verdict)
2. Transaction (inputs/outputs in vin/vout order, fee, confirmation, block height)
3. Risk assessment (persisted Engine 5 + weights as configuration context)
4. Typology findings
5. Blacklist / taint (direct hits only)
6. CoinJoin / demixing
7. Cluster
8. Graph / DAG (vin→vout pairs, index order; truncated at 250 pairs with an explicit note)
9. Evidence integrity (canonicalization version, SHA-256, hash algorithm, timestamp)
10. Audit metadata

Legal language: SHA-256 is **evidence integrity verification**, not a claim of legal admissibility. Investigator notes are Jinja2-autoescaped.

Browser print-to-PDF is optional if a PDF is needed later.

---

## 10. Database

SQLite path: `backend/app/db/storage.db` (`settings.SQLITE_DB_PATH`).

### `transactions` (Engine 5 + Engine 6 columns)

Existing Engine 5: `cluster_id`, `risk_score`, `blacklist_hit`, `typology_flags`, `ml_probability`, `taint_score`, `typology_score`, `mixer_penalty_score`, `risk_verdict`.

Added for Engine 6 (nullable, backward compatible via `ALTER TABLE`):

`fee_sats`, `confirmed`, `block_height`, `locktime`, `demix_json`, `typology_findings_json`, `change_findings_json`, `blacklist_hits_json`.

### `transaction_ios`

Ordered I/O: `txid`, `io_role` (`INPUT`/`OUTPUT`), `io_index`, `prev_txid`, `prev_vout`, `address`, `value_sats`, `script_type`.

### `flagged_transactions`

Copy of **SUSPICIOUS** and **HIGH_RISK** only. Maintained in `persist_transaction()` via `_sync_flagged_transaction()`. LICIT rows are deleted from this table. `init_db()` backfills from existing `transactions`.

LICIT example still generates a dossier; it simply does not appear on Alerts / flagged lists.

### Pre-migration rows

Export still works: I/O falls back to `transaction_addresses` (no prevout pointers). Typology may degrade to Engine 5 flag names without hop/path detail.

---

## 11. API

No authentication on these routes (current decision). CORS: `http://localhost:3000`, `http://127.0.0.1:3000`.

### `POST /api/v1/export-str`

```json
{ "txid": "<64 hex>", "case_id": "...", "investigator_note": "..." }
```

Response: `text/html; charset=utf-8`

Headers: `X-Txid`, `X-Risk-Score`, `X-Verdict`, `X-Evidence-SHA256`, `X-Generated-At`, `X-Report-Path`

Alias: `POST /api/v1/compliance/export-str`

Errors: `400` invalid/missing TXID, `404` not in SQLite, `500` unexpected failure.

### `GET /api/v1/compliance/transactions?limit=50`

`{ "recent", "suspicious", "flagged" }`

### `GET /api/v1/compliance/flagged?limit=100`

`{ "flagged": [ ... ] }`

TXID must match `^[0-9a-fA-F]{64}$`.

---

## 12. Frontend

**Reports** (`/reports`): paste TXID → generate HTML → download + iframe preview. Shows flagged list and recent txs. If FastAPI is down, shows an explicit “cannot reach port 8000” message (empty flagged list used to look like “no flags” because the fetch was swallowed).

**Investigator** (`/investigator`): same export from a TXID field.

**Alerts** (`/alerts`): table from `flagged_transactions`.

Frontend API base: `NEXT_PUBLIC_API_BASE_URL` or `http://localhost:8000/api/v1`.

---

## 13. Security

- Export is currently **unauthenticated** (handover note: re-enable JWT if this is deployed beyond local demo).
- Template path is fixed; requests cannot choose files.
- Investigator notes escaped in Jinja2.
- Secrets / `.env` / DB credentials are not written into the dossier.
- Response header values strip control characters; Windows paths in `X-Report-Path` use `/`.

---

## 14. How to run

Two processes:

```text
Terminal 1 — API
  cd backend
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

Terminal 2 — worker (fills SQLite)
  cd backend
  python run_worker.py

Terminal 3 — UI
  cd frontend
  npm run dev
```

Then open `http://localhost:3000/reports`.

**CLI (no HTTP):**

```text
cd backend
python generate_html_report.py <64-char-txid>
```

Output: `backend/app/reports/output/MARSAR-STR-<first 16 hex chars>.html`

**Tests:**

```text
cd backend
pytest tests/ -v
```

Engine 6 + Engine 5 tests should all pass. Engine 5 tests must remain green.

---

## 15. Verified live TX (this repo)

TXID:

`b9e4e69ad1cf4ae72971b4cb55ccf0a5325335fb42a48192e8816fb7cefcabcf`

| Check | Result |
| --- | --- |
| Present in SQLite | Yes |
| CLI HTML | `app/reports/output/MARSAR-STR-b9e4e69ad1cf4ae7.html` |
| Verdict / score | LICIT / 0.0 |
| In `flagged_transactions` | No (LICIT) |
| HTTP export (API running) | 200, `text/html`, SHA-256 `8137a1d7b5ea7fa3de00618b7626c1db04f433753e5dfe7618f2ae6fe9677cdf` |

---

## 16. Operational pitfalls (already hit)

1. **UI “Report generation failed” with FastAPI down** — connection refused; CLI can still succeed. Start uvicorn on port 8000.
2. **Empty flagged list while API is down** — list fetch failed silently (now surfaced).
3. **`ReferenceError: error is not defined` on `/reports`** — JSX used `error` after a state rename; restored.
4. **WeasyPrint / `libgobject-2.0-0`** — PDF path abandoned; HTML is the artefact.
5. **Export requires a persisted TXID** — mempool.space TXIDs that the worker never ingested return 404.

---

## 17. Limitations

- No multi-hop taint percentages, no KYC, no identities.
- Graph is this transaction’s vin→vout pairs, not a full historical DAG.
- Engine 4 hop/path detail exists only if `typology_findings_json` was persisted.
- ML probability is whatever Engine 5 stored (often `0` if the model file is empty).
- No Merkle root.
- Cluster `member_count` can be inflated by historical `persist_cluster_merge` upsert behaviour (Engine 2 persistence; Engine 6 reports stored values).
- Unauthenticated export is a demo choice, not a production hardening choice.

---

## 18. Suggested next work (not done)

- Optional PDF via browser print, or WeasyPrint on a Linux/GTK host.
- Re-enable JWT on export if leaving localhost.
- Persist a full address-level DAG if multi-hop reports are required.
- Do not duplicate Engine 5 scoring inside Engine 6.
