# MARSAR Offline Bitcoin Forensics

MARSAR ingests synthetic Bitcoin P2P and transaction metadata, links IP peers, wallets and transactions, identifies entity and laundering patterns, and produces ranked explainable leads. It is designed for offline operation after dependencies are installed or an image is built.

## Run locally

```bash
python -m pip install -r requirements.txt
python run_offline_pipeline.py --input data/bitcoin_telemetry.csv
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/dashboard`. The API also accepts offline CSV, JSON, and XML through `POST /api/v1/ingest/file`; then invoke `POST /api/v1/pipeline/run`.

## Evidence and model boundaries

The bundled data and watchlist are synthetic demonstration material. Scores are investigative triage signals, not evidence of criminality. The model is an offline supervised gradient-boosting classifier, complemented by Isolation Forest anomaly detection, CIOH/graph clustering, laundering topology detection, and taint propagation. Every alert includes its model probability, anomalous feature, topology evidence, taint score and network context.

## Offline deployment

Build the image in a connected build environment, transfer it together with any local data files, then run it without network access. Runtime code has no network clients; GeoIP/ASN enrichment reads `data/geoip_database.csv` locally.
