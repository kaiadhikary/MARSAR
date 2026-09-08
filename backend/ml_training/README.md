# MARSAR model-update pipeline

These tools are for a connected, controlled development environment only. The
MARSAR runtime never calls them and never downloads a dataset.

1. Obtain a legally usable labelled blockchain dataset, such as Elliptic, in
   accordance with its licence. Do not commit raw data to this repository.
2. Adapt the source into the documented input columns: `txid`, `label`,
   `input_amounts`, `output_amounts`, `fee`, optional `timestamp`, and optional
   `entity_id`.
3. Validate and quarantine invalid records:

   `python -m ml_training.prepare_dataset raw.csv --out datasets/prepared.csv --quarantine datasets/quarantine.json`

4. Train a versioned candidate and promote it only after independent evaluation:

   `python -m ml_training.train datasets/prepared.csv --registry models --version 1.0.0 --promote`

The training schema is intentionally blockchain-only. It never inserts fake
IP, port, ASN, country, or timing fields. Network telemetry remains a separate
runtime anomaly/risk signal. Prepared datasets, raw datasets, candidate models,
and registry artifacts must be managed outside source control.
