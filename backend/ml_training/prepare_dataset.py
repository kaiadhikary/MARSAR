"""Validate, deduplicate, and normalize a labelled blockchain CSV for training."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ml_training.feature_pipeline import FEATURE_NAMES, FEATURE_SCHEMA, extract_blockchain_features


def prepare(source: Path, output: Path, quarantine: Path) -> dict:
    seen, accepted, rejected = set(), [], []
    with source.open(encoding="utf-8-sig", newline="") as stream:
        for line_number, row in enumerate(csv.DictReader(stream), start=2):
            txid, label = (row.get("txid") or "").strip(), (row.get("label") or "").strip().lower()
            if not txid or txid in seen or label not in {"0", "1", "licit", "illicit"}:
                rejected.append({"line": line_number, "reason": "missing/duplicate txid or unsupported label", "record": row})
                continue
            try:
                values = extract_blockchain_features(row)
            except ValueError as exc:
                rejected.append({"line": line_number, "reason": str(exc), "record": row})
                continue
            seen.add(txid)
            accepted.append({"txid": txid, "label": 1 if label in {"1", "illicit"} else 0,
                             "timestamp": row.get("timestamp", ""), "entity_id": row.get("entity_id", ""),
                             **dict(zip(FEATURE_NAMES, values))})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(accepted[0]) if accepted else ["txid", "label", *FEATURE_NAMES])
        writer.writeheader(); writer.writerows(accepted)
    quarantine.write_text(json.dumps(rejected, indent=2), encoding="utf-8")
    return {"accepted": len(accepted), "rejected": len(rejected), "feature_schema": FEATURE_SCHEMA}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("source", type=Path); parser.add_argument("--out", type=Path, required=True); parser.add_argument("--quarantine", type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().source, parser.parse_args().out, parser.parse_args().quarantine), indent=2))
