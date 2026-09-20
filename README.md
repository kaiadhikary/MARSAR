# MARSAR — Offline Bitcoin Forensics & AML Platform

**M**etadata-**A**ugmented **R**ansomware & **S**uspicious **A**ctivity **R**esolver

MARSAR is an **air-gapped, offline forensic lead-generation system** built for **Smart India Hackathon — Problem Statement SIH26146**. It ingests bulk synthetic Bitcoin P2P/transaction metadata, links IP peers, wallets, and transactions into a single graph, applies AI/ML-driven entity clustering and anomaly detection, and produces a ranked, explainable list of investigative leads through a web dashboard.

> **Evidence disclaimer:** Every score, cluster, and alert produced by this system is an investigative lead, not a determination of criminal conduct or wallet ownership. See [Evidence & Ethical Boundaries](#evidence--ethical-boundaries) below.

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [API Overview](#api-overview)
- [Testing](#testing)
- [Evidence & Ethical Boundaries](#evidence--ethical-boundaries)
- [Model Lifecycle](#model-lifecycle)
- [Offline / Air-Gapped Deployment](#offline--air-gapped-deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Problem Statement

SIH26146 calls for an **offline** system (deployable on an isolated Linux host) that:

1. Ingests a bulk synthetic Bitcoin transaction/network metadata dataset (CSV / JSON / XML) containing fields such as `timestamp`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `txid`, `input_addresses`, `output_addresses`, `input_amounts`, `output_amounts`, and `geo_country`/`asn`.
2. Builds an entity/transaction graph linking IP addresses, wallets, and transactions.
3. Applies a working AI/ML model — not rules alone — for anomaly detection and entity clustering.
4. Outputs a ranked, explainable alert list with confidence scores.
5. Presents findings through a dashboard with link-analysis (graph) visualization.

MARSAR implements all five requirements end-to-end with no external network calls at runtime.

## Key Features

- **Bulk offline ingestion** — CSV, JSON, and XML telemetry via `POST /api/v1/ingest/file`, or the CLI pipeline (`run_offline_pipeline.py`).
- **Entity clustering** — Common-Input-Ownership Heuristic (CIOH), IP co-location, and TruncatedSVD-based similarity to group addresses into probable entities. Shared infrastructure (exchanges, VPNs, hosting) is treated as a supporting signal, never as automatic ownership.
- **Anomaly detection** — Isolation Forest for outlier telemetry, plus a supervised gradient-boosting classifier for transaction risk.
- **Laundering pattern detection** — CoinJoin-like pattern flagging (`COINJOIN_LIKE_PATTERN`) and NetworkX-based typology/topology detection.
- **Taint propagation** — Forward taint scoring from a watchlist of illicit seed addresses.
- **Offline GeoIP/ASN enrichment** — A locally built lookup table (from IP2Location LITE CSVs) resolved via binary search; unmatched IPs are reported as `UNKNOWN`, never guessed.
- **Explainable risk scoring** — Every alert carries its model probability, the anomalous feature and its local counterfactual sensitivity, topology evidence, taint score, and network context.
- **Forensic dossier export** — A deterministic, hashed (SHA-256) HTML evidence report per transaction, generated from already-persisted pipeline output (no re-computation at export time).
- **Interactive dashboard** — Next.js + Cytoscape.js link-analysis graph, transaction explorer, alert triage, and compliance views.

## Architecture

The backend is organized as a pipeline of engines, each reading the previous engine's persisted output from SQLite:

```
Bulk CSV / JSON / XML
        │
        ▼
Engine 1 — Ingestion & Parsing        (app/ingestion/)
        │
        ▼
Engine 2 — Entity Clustering          (app/engine/clustering.py)
        │
        ▼
Engine 3 — Demixing / CoinJoin        (app/engine/demixing.py)
        │
        ▼
Engine 4 — Typology & Heuristics      (app/engine/heuristics.py)
        │
        ▼
Engine 5 — Risk Scoring & ML          (app/engine/scoring.py, app/ml/)
        │
        ▼
Engine 6 — Forensic Dossier Export    (app/reports/)
        │
        ▼
FastAPI (dashboard / alerts / graph / trace / compliance)
        │
        ▼
Next.js frontend (Investigator, Explorer, Network graph, Alerts, Reports)
```

Engine 6 is a **reader only** — it never re-runs clustering, demixing, typology, or risk scoring. If Engine 5 stored a risk score of `72.4` with verdict `HIGH_RISK`, the dossier prints exactly those values, canonicalizes the evidence as UTF-8 JSON, and hashes it with SHA-256 for auditability.

## Tech Stack

**Backend**
- Python 3.11, FastAPI, Uvicorn, Pydantic v2
- scikit-learn (Gradient Boosting, Isolation Forest), NetworkX (graph/typology)
- SQLite (local, WAL mode) — no external database dependency
- Jinja2 (HTML dossier templates), Joblib (model persistence)

**Frontend**
- Next.js 14 (App Router), React 18, TypeScript
- Tailwind CSS, Radix UI primitives, `cmdk` command palette
- Cytoscape.js (link-analysis graph), Recharts (metrics), Framer Motion

## Repository Structure

```
MARSAR/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # auth, alerts, graph, trace, compliance, dashboard routes
│   │   ├── engine/          # clustering, demixing, heuristics, anomaly, scoring
│   │   ├── ingestion/       # bulk CSV/JSON/XML + Elliptic dataset parsers
│   │   ├── ml/              # feature extraction, inference, model contract, weights
│   │   ├── reports/         # Engine 6 evidence collection, hashing, HTML generator
│   │   ├── db/               # SQLite client
│   │   └── core/            # config, security, broadcast
│   ├── ml_training/         # offline, connected-environment model training pipeline
│   ├── tools/                # GeoIP/ASN database builder utilities
│   ├── tests/                 # pytest suite
│   ├── data/                  # local datasets & generated GeoIP database (gitignored)
│   ├── run_offline_pipeline.py
│   ├── generate_html_report.py
│   ├── generate_synthetic_dataset.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/(dashboard)/  # investigator, explorer, trace, transactions, network, patterns
│       ├── components/       # graph, investigation, layout, alerts, tracer, widgets, ui
│       └── ...
├── IMPLEMENTATION_NOTES.md
├── LICENSE
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- No internet access is required at runtime — only for the initial dependency install.

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env            # adjust MARSAR_REQUIRE_AUTH / secret key if needed

# Load a bulk dataset and run the pipeline
python run_offline_pipeline.py --input data/bitcoin_telemetry.csv

# Start the API
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API is now live at `http://127.0.0.1:8000` (interactive docs at `/docs`), and the bundled dashboard at `http://127.0.0.1:8000/dashboard`.

You can also POST a dataset directly instead of using the CLI:

```bash
curl -F "file=@data/bitcoin_telemetry.csv" http://127.0.0.1:8000/api/v1/ingest/file
curl -X POST http://127.0.0.1:8000/api/v1/pipeline/run
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # only needed if the API isn't on port 8000
npm run dev
```

Open `http://localhost:3000`.

### 3. GeoIP/ASN database (optional, one-time, connected environment)

```bash
cd backend
python tools/build_geoip_database.py \
  --country IP2LOCATION-LITE-DB1.CSV \
  --asn IP2LOCATION-LITE-ASN.CSV \
  --out data/geoip_database.csv
```

Do not commit the source IP2Location CSVs or place them in the deployed runtime image — only the generated `geoip_database.csv` is needed at runtime.

## API Overview

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/ingest/file` | Upload a CSV/JSON/XML telemetry dataset |
| `POST /api/v1/pipeline/run` | Run clustering → demixing → heuristics → scoring |
| `GET /api/v1/alerts/ranked` | Ranked, explainable investigative alerts |
| `GET /api/v1/graph/expand/{address}` | Expand an address into its cluster/link graph |
| `GET /api/v1/graph/topology` | Full entity/transaction topology |
| `GET /api/v1/trace/...` | Transaction/flow tracing |
| `GET /api/v1/compliance/transactions` | Compliance transaction listing |
| `GET /api/v1/compliance/flagged` | Flagged transaction listing |
| `POST /api/v1/export-str` | Generate & return the hashed HTML forensic dossier |
| `GET /health` | SQLite connectivity + record counts |

Full interactive documentation is available at `/docs` (Swagger UI) once the backend is running. Authentication is off by default (`MARSAR_REQUIRE_AUTH=false`) so the bundled dashboard can reach the API without a login flow; set it to `true` and configure `MARSAR_FORENSIC_SECRET_KEY` for a gated deployment.

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

Covers clustering, demixing, ingestion, the ML pipeline, GeoIP database building, and scoring.

## Evidence & Ethical Boundaries

- All bundled datasets and the watchlist are **synthetic demonstration material**.
- **Common-input ownership is the only automatic ownership-clustering link.** Shared IP address and graph similarity are supporting leads only — they never merge wallets, because shared exchange, VPN, or hosting infrastructure is not ownership evidence.
- CoinJoin-like output is labelled `COINJOIN_LIKE_PATTERN`. Equal denominations and multiple inputs are indicators, not confirmation of a mixer service.
- GeoIP/ASN resolution never guesses: an unmatched or invalid IP resolves to `UNKNOWN`.
- Scores and alerts are **investigative triage signals**, not legal conclusions or proof of criminal conduct.

## Model Lifecycle

- The shipped model is an `sklearn.GradientBoostingClassifier` trained on **synthetic demonstration distributions** (despite legacy filenames referencing XGBoost/Elliptic, it is neither). Its validation metrics should not be published as real-world Bitcoin crime-detection performance.
- Inference reports **per-transaction local counterfactual sensitivity** (replacing one feature with its training-set median and measuring the probability shift) — this is evidence for that specific transaction, not a global feature-importance/SHAP claim.
- To train on real, labelled data: build a separate blockchain-only schema from a properly licensed source (see `backend/ml_training/README.md`), keep network telemetry as a separate signal, freeze a holdout set, version candidate artifacts, and deploy only a validated local artifact. The production runtime should continue to make no external calls.

## Offline / Air-Gapped Deployment

Build the Docker image in a connected build environment (dependencies are resolved from `backend/wheelhouse/` with no index), transfer the image and any local data files, then run it with no network access:

```bash
cd backend
docker build -t marsar-backend .
docker run -p 8000:8000 marsar-backend
```

Runtime code makes no outbound network calls; GeoIP/ASN enrichment reads `data/geoip_database.csv` locally.

## Team

| Name | Role | GitHub |
|---|---|---|
| **Adarsh Satyajit Adhikary** (Kai) | Project Lead & Lead Backend Developer — defined the corrected SIH26146 scope, directed frontend and backend work, built the core backend (ingestion, clustering, scoring, ML, API) | [@kaidhikary](https://github.com/kaidhikary) |
| **Raj Panigrahy** | Backend Developer | [@rajpanigrahy20-gif](https://github.com/rajpanigrahy20-gif) |
| **Ayush Shashibhushan Tripathi** | Frontend Developer — built the full Next.js/Cytoscape dashboard | [@4yushtripathi](https://github.com/4yushtripathi) |

## Contributing

Issues and pull requests are welcome. Please open an issue describing the change before submitting a large PR, and run `pytest` before pushing backend changes.

## License

Released under the [MIT License](LICENSE).
