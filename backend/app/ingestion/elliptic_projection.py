"""Shared Elliptic → MARSAR feature projection for training and ingestion."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np

LOCAL = {
    "volume_a": 0,
    "volume_b": 1,
    "fee_signal": 2,
    "in_count": 3,
    "out_count": 4,
    "fee_level": 5,
    "dispersion": 6,
    "asymmetry": 7,
}
AGG = {
    "neighbour_risk_a": 0,
    "neighbour_risk_b": 1,
    "neighbour_risk_c": 2,
}


def _pos_amount(z: float, base: float = 0.25, scale: float = 1.2) -> float:
    """Map a z-scored Elliptic local feature to a positive BTC-like magnitude."""
    z = float(np.clip(z, -2.5, 6.0))
    return float(np.clip(np.expm1(z) * scale + base, 0.01, 500.0))


def load_graph_degrees(edgelist_path: Path) -> Tuple[Dict[str, int], Dict[str, int]]:
    in_deg: Dict[str, int] = defaultdict(int)
    out_deg: Dict[str, int] = defaultdict(int)
    with edgelist_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            src = row["txId1"].strip()
            dst = row["txId2"].strip()
            out_deg[src] += 1
            in_deg[dst] += 1
    return in_deg, out_deg


def load_graph_edges(edgelist_path: Path) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """Return parent and child txId lists keyed by transaction id."""
    parents: Dict[str, List[str]] = defaultdict(list)
    children: Dict[str, List[str]] = defaultdict(list)
    with edgelist_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            src = row["txId1"].strip()
            dst = row["txId2"].strip()
            children[src].append(dst)
            parents[dst].append(src)
    return dict(parents), dict(children)


def load_elliptic_labels(classes_path: Path, include_unknown: bool = False) -> Dict[str, int]:
    """Return txId → label (1=illicit, 0=licit). Skips unknown unless requested."""
    labels: Dict[str, int] = {}
    with classes_path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            txid = row["txId"].strip()
            klass = row["class"].strip()
            if klass == "unknown":
                if include_unknown:
                    labels[txid] = -1
                continue
            if klass == "1":
                labels[txid] = 1
            elif klass == "2":
                labels[txid] = 0
    return labels


def iter_elliptic_features(
    features_path: Path,
    tx_filter: Optional[Set[str]] = None,
    limit: Optional[int] = None,
) -> Iterable[Tuple[str, np.ndarray]]:
    """Stream feature rows: (txId, row) where row = [time_step, local_*, agg_*]."""
    count = 0
    with features_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        for row in reader:
            if len(row) < 167:
                continue
            txid = row[0].strip()
            if tx_filter is not None and txid not in tx_filter:
                continue
            yield txid, np.asarray([float(v) for v in row[1:]], dtype=np.float32)
            count += 1
            if limit is not None and count >= limit:
                break


def elliptic_row_to_marsar_vector(
    row: np.ndarray,
    in_degree: int,
    out_degree: int,
) -> np.ndarray:
    """Project one Elliptic feature row into MARSAR's 13-dim runtime schema."""
    time_step = float(row[0])
    local = row[1:94]
    agg = row[94:]

    total_in = float(np.clip(
        _pos_amount(float(local[LOCAL["volume_a"]])) * _pos_amount(float(local[LOCAL["volume_b"]]), base=0.15, scale=0.8),
        0.01,
        500.0,
    ))
    fee_signal = float(np.clip(float(local[LOCAL["fee_signal"]]), -6.0, 6.0))
    total_out = float(np.clip(total_in * (0.90 + 0.10 / (1.0 + np.exp(-fee_signal))), 0.01, 500.0))

    n_in = max(1.0, min(64.0, float(in_degree or 0) or 1.0 + max(0.0, float(local[LOCAL["in_count"]]) + 2.0)))
    n_out = max(1.0, min(64.0, float(out_degree or 0) or 1.0 + max(0.0, float(local[LOCAL["out_count"]]) + 2.0)))

    fee = float(np.clip(total_in * 0.0015 * _pos_amount(float(local[LOCAL["fee_level"]]), base=0.05, scale=0.35), 1e-6, 5.0))
    fee_ratio = float(np.clip(fee / max(total_in, 1e-6), 1e-6, 0.25))

    entropy = float(np.clip(1.2 + float(local[LOCAL["dispersion"]]) * 0.35, 0.0, 3.5))
    asymmetry = float(np.clip(1.0 + abs(float(local[LOCAL["asymmetry"]])) * 2.5, 1.0, 60.0))

    is_non_standard_port = 1.0 if float(agg[AGG["neighbour_risk_a"]]) > 0.75 else 0.0
    is_high_risk_asn = 1.0 if float(agg[AGG["neighbour_risk_b"]]) > 0.75 else 0.0
    is_high_risk_country = 1.0 if float(agg[AGG["neighbour_risk_c"]]) > 0.75 else 0.0

    script_type_code = 3.0
    hour_of_broadcast = float(time_step % 24)

    return np.asarray(
        [
            total_in,
            total_out,
            n_in,
            n_out,
            fee,
            fee_ratio,
            entropy,
            asymmetry,
            is_non_standard_port,
            is_high_risk_asn,
            is_high_risk_country,
            script_type_code,
            hour_of_broadcast,
        ],
        dtype=np.float32,
    )
