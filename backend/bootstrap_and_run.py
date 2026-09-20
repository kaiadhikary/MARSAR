#!/usr/bin/env python3
"""Single-command bootstrap for the MARSAR offline pipeline."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import joblib

from app.core.config import settings
from app.db.sqlite_client import get_db_connection, init_db, reset_database
from app.engine.alert_generator import generate_investigative_alerts
from app.engine.clustering import EntityClusterEngine
from app.ingestion.bulk_parser import BulkDataParser, OfflineGeoIPResolver
from app.ingestion.elliptic_parser import EllipticDataParser, ELLIPTIC_DIR
from app.ml.model_contract import validate_model_contract
from generate_synthetic_dataset import generate_datasets

import train_elliptic_xgboost
import tools.build_geoip_database as geoip_builder

SEED_WATCHLIST = [
    ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "OFAC_RANSOMWARE", 1.0),
    ("1CounterpartyXXXXXXXXXXXXXXXUWLpVr", "DARKNET_MARKET", 0.95),
    ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "MIXER_OPERATOR", 0.90),
]


def ensure_db_ready(wipe: bool) -> None:
    init_db()
    if wipe:
        print("      --wipe-db passed: clearing existing transactions/clusters/alerts.")
        reset_database()
    else:
        print("      Existing data preserved (pass --wipe-db to clear it instead).")

    conn = get_db_connection()
    conn.executemany(
        "INSERT OR IGNORE INTO illicit_seeds (address, category, severity) VALUES (?, ?, ?)",
        SEED_WATCHLIST,
    )
    conn.commit()
    conn.close()


def ensure_geoip_ready(auto_build: bool) -> None:
    resolver = OfflineGeoIPResolver()
    if resolver._range_starts:
        print(f"      OK - {len(resolver._range_starts)} real IP ranges already loaded.")
        return

    raw_dir = settings.DATA_DIR / "raw_geoip"
    country_csv = None
    asn_csv = None
    if raw_dir.exists():
        country_csv = next(raw_dir.glob("*[Cc][Oo][Uu][Nn][Tt][Rr][Yy]*.[Cc][Ss][Vv]"), None) \
            or next(raw_dir.glob("*DB1*.[Cc][Ss][Vv]"), None)
        asn_csv = next(raw_dir.glob("*[Aa][Ss][Nn]*.[Cc][Ss][Vv]"), None)

    if auto_build and country_csv:
        detail = country_csv.name + (f" + {asn_csv.name}" if asn_csv else " (country only - no ASN source found)")
        print(f"      No real ranges loaded - building from {detail}...")
        countries = geoip_builder._read_country(country_csv)
        asns = geoip_builder._read_asn(asn_csv) if asn_csv else []
        out_path = settings.DATA_DIR / "geoip_database.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(("ip_from", "ip_to", "country_code", "asn_name"))
            w.writerows(geoip_builder.intersect_ranges(countries, asns))
        reloaded = OfflineGeoIPResolver()
        print(f"      Built {out_path} - now {len(reloaded._range_starts)} real ranges loaded.")
    else:
        print(
            "      WARNING: only the small built-in example table is active (6 "
            "illustrative ranges). Real IPs outside those will resolve to "
            f"UNKNOWN. Drop IP2Location LITE country/ASN CSVs into {raw_dir} "
            "and re-run to build full global coverage. Continuing as-is - "
            "this is a coverage gap, not a crash."
        )


def ensure_model_ready(auto_train: bool) -> None:
    path = settings.WEIGHTS_PATH
    valid = False
    if path.exists() and path.stat().st_size > 1024:
        try:
            validate_model_contract(joblib.load(path))
            valid = True
        except Exception:
            valid = False

    if valid:
        print(f"      OK - valid model already at {path}")
        return

    if auto_train:
        print(f"      No valid model at {path} - training now...")
        train_elliptic_xgboost.train_and_export()
    else:
        print(f"      WARNING: no valid model at {path}. Inference will use its tiny embedded fallback classifier.")


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument("--input", help="CSV, JSON, or XML telemetry file. Defaults to bundled/synthetic data.")
    cli.add_argument("--elliptic", action="store_true",
                      help="Ingest the Elliptic Bitcoin dataset (backend/data/elliptic/) instead of telemetry.")
    cli.add_argument("--elliptic-dir", type=Path, default=ELLIPTIC_DIR,
                      help="Path to elliptic_txs_*.csv files (default: backend/data/elliptic).")
    cli.add_argument("--elliptic-limit", type=int, default=None,
                      help="Cap Elliptic ingestion to N labelled transactions (for quick tests).")
    cli.add_argument("--wipe-db", action="store_true",
                      help="DESTRUCTIVE: clear all existing transactions/clusters/alerts first. Off by default.")
    cli.add_argument("--no-auto-geoip", action="store_true", help="Don't auto-build the GeoIP database.")
    cli.add_argument("--no-auto-train", action="store_true", help="Don't auto-train the ML model.")
    args = cli.parse_args()

    print("=" * 78)
    print("  MARSAR - fully-linked offline pipeline bootstrap")
    print("=" * 78)

    print("\n[1/6] Database schema + watchlist seed...")
    ensure_db_ready(wipe=args.wipe_db)

    print("\n[2/6] GeoIP database...")
    ensure_geoip_ready(auto_build=not args.no_auto_geoip)

    print("\n[3/6] ML model weights...")
    ensure_model_ready(auto_train=not args.no_auto_train)

    print("\n[4/6] Dataset...")
    data_dir = settings.DATA_DIR
    use_elliptic = args.elliptic

    print("\n[5/6] Ingestion -> Clustering -> Detection -> Alerts...")
    if use_elliptic:
        elliptic_dir = args.elliptic_dir.expanduser()
        print(f"      Using Elliptic Bitcoin dataset: {elliptic_dir}")
        elliptic_parser = EllipticDataParser(elliptic_dir)
        ingested, gt_count = elliptic_parser.parse_and_ingest(limit=args.elliptic_limit)
        print(f"      Ingested {ingested} Elliptic transactions ({gt_count} ground-truth labels stored).")
        if elliptic_parser.rejected_records:
            print(f"      Rejected {len(elliptic_parser.rejected_records)} malformed rows.")
    else:
        if args.input:
            input_target = Path(args.input).expanduser()
            if not input_target.exists():
                raise FileNotFoundError(f"Input dataset does not exist: {input_target}")
            print(f"      Using: {input_target}")
        else:
            input_target = data_dir / "bitcoin_telemetry.csv"
            if not input_target.exists():
                print(f"      No dataset found - generating synthetic telemetry in {data_dir}...")
                generate_datasets(str(data_dir))
            else:
                print(f"      Using bundled dataset: {input_target}")

        parser = BulkDataParser()
        records = parser.parse_file(str(input_target))
        ingested = parser.ingest_to_db(records)
        print(f"      Ingested {ingested} transactions (safe to re-run - INSERT OR REPLACE by txid).")

    cluster_engine = EntityClusterEngine()
    clusters = cluster_engine.run_clustering()
    print(f"      {len(clusters)} entity clusters.")

    alerts = generate_investigative_alerts()
    print(f"      {len(alerts)} ranked alerts generated.")

    print("\n[6/6] Top leads:")
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT alert_id, target_type, target_identifier, risk_score, primary_focus_area
        FROM alerts ORDER BY risk_score DESC LIMIT 10
    """).fetchall()
    conn.close()
    for r in rows:
        target = (r["target_identifier"] or "")[:26]
        print(f"  {r['alert_id']:<18} | {r['target_type']:<7} | {target:<28} | {r['risk_score']:.3f} | {r['primary_focus_area']}")

    print("\nDone." + (" (--wipe-db was used - started from a clean DB.)" if args.wipe_db else " Nothing was wiped."))


if __name__ == "__main__":
    sys.exit(main())
