"""Ingest the Elliptic Bitcoin dataset into MARSAR's forensic engine."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from app.db.sqlite_client import get_db_connection
from app.ingestion.elliptic_projection import (
    elliptic_row_to_marsar_vector,
    iter_elliptic_features,
    load_elliptic_labels,
    load_graph_degrees,
    load_graph_edges,
)
ELLIPTIC_DIR = Path(__file__).resolve().parents[2] / "data" / "elliptic"

_HIGH_RISK_IP = "198.51.100.42"
_NEUTRAL_IP = "104.28.0.1"


def _distribute_amounts(total: float, count: int, asymmetry: float) -> List[float]:
    """Split *total* across *count* positive amounts with max/min ≈ *asymmetry*."""
    count = max(1, count)
    total = max(total, 0.01)
    asymmetry = max(1.0, min(asymmetry, 60.0))

    if count == 1:
        return [round(total, 8)]

    min_amt = total / (asymmetry + count - 1)
    max_amt = min_amt * asymmetry
    remainder = total - max_amt
    per_other = remainder / (count - 1)
    amounts = [round(per_other, 8) for _ in range(count - 1)]
    amounts.append(round(max_amt, 8))

    drift = round(total - sum(amounts), 8)
    amounts[-1] = round(amounts[-1] + drift, 8)
    return amounts


def _build_io_addresses(
    txid: str,
    parent_ids: List[str],
    child_ids: List[str],
    n_in: int,
    n_out: int,
) -> Tuple[List[str], List[str]]:
    """Map edgelist neighbours to pseudo-addresses for graph connectivity."""
    in_addrs: List[str] = []
    for parent in parent_ids[:n_in]:
        in_addrs.append(f"elliptic_{parent}_out")
    while len(in_addrs) < n_in:
        in_addrs.append(f"elliptic_genesis_{txid}_{len(in_addrs)}")

    out_addrs: List[str] = []
    for child in child_ids[:n_out]:
        out_addrs.append(f"elliptic_{child}_in")
    while len(out_addrs) < n_out:
        out_addrs.append(f"elliptic_sink_{txid}_{len(out_addrs)}")

    return in_addrs, out_addrs


def elliptic_vector_to_tx_record(
    txid: str,
    row: np.ndarray,
    in_degree: int,
    out_degree: int,
    parent_ids: List[str],
    child_ids: List[str],
) -> Dict[str, Any]:
    """Convert one Elliptic row into a MARSAR transaction dict."""
    vec = elliptic_row_to_marsar_vector(row, in_degree, out_degree)
    total_in = float(vec[0])
    total_out = float(vec[1])
    n_in = max(1, int(round(vec[2])))
    n_out = max(1, int(round(vec[3])))
    fee = float(vec[4])
    asymmetry = float(vec[7])
    non_std_port = bool(vec[8])
    high_risk_asn = bool(vec[9])
    high_risk_country = bool(vec[10])
    time_step = float(row[0])
    hour = int(vec[12]) % 24

    in_addrs, out_addrs = _build_io_addresses(txid, parent_ids, child_ids, n_in, n_out)
    in_amounts = _distribute_amounts(total_in, n_in, asymmetry)
    out_amounts = _distribute_amounts(total_out, n_out, asymmetry)

    inputs = [{"address": addr, "amount": amt} for addr, amt in zip(in_addrs, in_amounts)]
    outputs = [{"address": addr, "amount": amt} for addr, amt in zip(out_addrs, out_amounts)]

    if high_risk_country:
        country, asn = "RU", "AS12389 - Rostelecom"
        src_ip = _HIGH_RISK_IP
    elif high_risk_asn:
        country, asn = "SC", "AS51852 - Private Layer"
        src_ip = "194.26.0.1"
    else:
        country, asn = "US", "AS13335 - Cloudflare"
        src_ip = _NEUTRAL_IP

    return {
        "txid": f"elliptic_{txid}",
        "timestamp": int(hour * 3600 + time_step * 86_400),
        "src_ip": src_ip,
        "dst_ip": _NEUTRAL_IP,
        "src_port": 8333,
        "dst_port": 54321 if non_std_port else 8333,
        "fee": fee,
        "script_type": "p2wpkh",
        "geo_country": country,
        "geo_asn": asn,
        "inputs": inputs,
        "outputs": outputs,
        "total_input_btc": round(total_in, 8),
        "total_output_btc": round(total_out, 8),
    }


class EllipticDataParser:
    """Load Elliptic CSVs and ingest projected records into the forensic DB."""

    def __init__(self, data_dir: Path | str | None = None):
        self.data_dir = Path(data_dir) if data_dir else ELLIPTIC_DIR
        self.rejected_records: List[Dict[str, Any]] = []
        self.ground_truth: Dict[str, str] = {}

    def _validate_paths(self) -> None:
        required = [
            "elliptic_txs_features.csv",
            "elliptic_txs_classes.csv",
            "elliptic_txs_edgelist.csv",
        ]
        missing = [name for name in required if not (self.data_dir / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Elliptic dataset incomplete in {self.data_dir}. Missing: {', '.join(missing)}"
            )

    def load_records(
        self,
        labelled_only: bool = True,
        include_unknown: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Parse Elliptic CSVs into MARSAR transaction records."""
        self._validate_paths()
        self.rejected_records.clear()
        self.ground_truth.clear()

        labels = load_elliptic_labels(self.data_dir / "elliptic_txs_classes.csv", include_unknown)
        in_deg, out_deg = load_graph_degrees(self.data_dir / "elliptic_txs_edgelist.csv")
        parents_map, children_map = load_graph_edges(self.data_dir / "elliptic_txs_edgelist.csv")

        tx_filter: Optional[Set[str]] = set(labels.keys()) if labelled_only else None

        records: List[Dict[str, Any]] = []
        for txid, row in iter_elliptic_features(
            self.data_dir / "elliptic_txs_features.csv",
            tx_filter=tx_filter,
            limit=limit,
        ):
            try:
                record = elliptic_vector_to_tx_record(
                    txid,
                    row,
                    in_deg.get(txid, 0),
                    out_deg.get(txid, 0),
                    parents_map.get(txid, []),
                    children_map.get(txid, []),
                )
                records.append(record)

                label_val = labels.get(txid)
                if label_val == 1:
                    self.ground_truth[record["txid"]] = "illicit"
                elif label_val == 0:
                    self.ground_truth[record["txid"]] = "licit"
                elif label_val == -1:
                    self.ground_truth[record["txid"]] = "unknown"
            except (ValueError, KeyError, TypeError) as exc:
                self.rejected_records.append({"txid": txid, "reason": str(exc)})

        return records

    def ingest_to_db(self, records: List[Dict[str, Any]]) -> int:
        """Insert projected Elliptic transactions into SQLite."""
        if not records:
            return 0
        conn = get_db_connection()
        cur = conn.cursor()
        for record in records:
            cur.execute(
                """
                INSERT OR REPLACE INTO transactions (
                    txid, timestamp, src_ip, dst_ip, src_port, dst_port,
                    fee, script_type, geo_country, geo_asn,
                    inputs_json, outputs_json, total_input_btc, total_output_btc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["txid"],
                    record["timestamp"],
                    record["src_ip"],
                    record["dst_ip"],
                    record["src_port"],
                    record["dst_port"],
                    record["fee"],
                    record["script_type"],
                    record["geo_country"],
                    record["geo_asn"],
                    json.dumps(record["inputs"]),
                    json.dumps(record["outputs"]),
                    record["total_input_btc"],
                    record["total_output_btc"],
                ),
            )
        conn.commit()
        conn.close()
        return len(records)

    def ingest_ground_truth(self) -> int:
        """Store Elliptic labels in the ground_truth table."""
        if not self.ground_truth:
            return 0
        conn = get_db_connection()
        cur = conn.cursor()
        for txid, label in self.ground_truth.items():
            cur.execute(
                """
                INSERT OR REPLACE INTO ground_truth (txid, label, source)
                VALUES (?, ?, 'elliptic')
                """,
                (txid, label),
            )
        conn.commit()
        conn.close()
        return len(self.ground_truth)

    def parse_and_ingest(
        self,
        labelled_only: bool = True,
        include_unknown: bool = False,
        limit: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Load, ingest transactions, and store ground-truth labels."""
        records = self.load_records(
            labelled_only=labelled_only,
            include_unknown=include_unknown,
            limit=limit,
        )
        tx_count = self.ingest_to_db(records)
        gt_count = self.ingest_ground_truth()
        return tx_count, gt_count
