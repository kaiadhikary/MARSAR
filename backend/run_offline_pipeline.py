#!/usr/bin/env python3
"""
Master Offline CLI Pipeline Orchestrator.
Ingestion -> Correlation -> Graph Construction -> CIOH + Graph Embedding Clustering -> 
Supervised ML + Unsupervised Anomaly Detection -> Demixing -> Taint Diffusion -> Ranked Alerts.
"""

import sys
import json
import argparse
from pathlib import Path

from app.core.config import settings
from app.db.sqlite_client import init_db, get_db_connection, reset_database
from app.ingestion.bulk_parser import BulkDataParser
from app.engine.clustering import EntityClusterEngine
from app.engine.alert_generator import generate_investigative_alerts
from generate_synthetic_dataset import generate_datasets


def main():
    cli = argparse.ArgumentParser(description="Run the MARSAR offline investigation pipeline.")
    cli.add_argument("--input", help="CSV, JSON, or XML telemetry file. Defaults to bundled CSV.")
    cli.add_argument("--keep-data", action="store_true", help="Do not clear existing transaction data before ingesting.")
    args = cli.parse_args()
    print("=" * 80)
    print("  MARSAR: BITCOIN P2P TRAFFIC FORENSIC PIPELINE (OFFLINE AIR-GAP RUNNER)")
    print("=" * 80)

    # 1. Reset and initialize SQLite schema
    print("\n[+] Stage 1: Initializing Forensic Persistence Layer...")
    init_db()
    if not args.keep_data:
        reset_database()

    # Pre-seed watchlist addresses
    conn = get_db_connection()
    conn.execute('''
        INSERT OR IGNORE INTO illicit_seeds (address, category, severity) VALUES 
        ('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa', 'OFAC_RANSOMWARE', 1.0),
        ('1CounterpartyXXXXXXXXXXXXXXXUWLpVr', 'DARKNET_MARKET', 0.95),
        ('3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy', 'MIXER_OPERATOR', 0.90)
    ''')
    conn.commit()
    conn.close()

    # 2. Verify or create bulk datasets using settings path
    data_dir = settings.DATA_DIR
    input_target = Path(args.input).expanduser() if args.input else data_dir / "bitcoin_telemetry.csv"
    if not input_target.exists() and not args.input:
        print(f"[+] Stage 2: Generating synthetic telemetry datasets in {data_dir}...")
        generate_datasets(str(data_dir))
    elif not input_target.exists():
        raise FileNotFoundError(f"Input dataset does not exist: {input_target}")
    else:
        print(f"[+] Stage 2: Using offline dataset: {input_target}")

    # 3. Ingest Bulk Data & Resolve GeoIP Offline
    print("\n[+] Stage 3: Ingesting Bulk Metadata & Resolving GeoIP Offline...")
    parser = BulkDataParser()
    records = parser.parse_file(str(input_target))
    ingested = parser.ingest_to_db(records)
    print(f"    -> Ingested {ingested} transactions into local database.")

    # 4. Entity Clustering (CIOH + Graph Embeddings)
    print("\n[+] Stage 4: Executing Entity Clustering (CIOH + IP Co-location + Graph Embeddings)...")
    cluster_engine = EntityClusterEngine()
    clusters = cluster_engine.run_clustering()
    print(f"    -> Identified {len(clusters)} distinct real-world entity clusters.")

    # 5. Run Detection Engines & ML Models
    print("\n[+] Stage 5: Running AI/ML Models, Demixing & Seed Taint Propagation...")
    alerts = generate_investigative_alerts()
    print(f"    -> Generated {len(alerts)} prioritized investigative alerts (Transactions & Wallets).")

    # 6. Display Ranked Investigative Leads
    print("\n" + "=" * 80)
    print("  TOP PRIORITIZED INVESTIGATIVE LEADS (RANKED BY COMPOSITE RISK)")
    print("=" * 80)

    conn = get_db_connection()
    rows = conn.execute('''
        SELECT alert_id, target_type, target_identifier, risk_score, confidence, primary_focus_area, explanation_json
        FROM alerts
        ORDER BY risk_score DESC
        LIMIT 10
    ''').fetchall()
    conn.close()

    header = f"{'ALERT ID':<18} | {'TYPE':<7} | {'IDENTIFIER':<28} | {'RISK':<6} | {'FOCUS AREA'}"
    print(header)
    print("-" * len(header))

    for r in rows:
        alert_id = r["alert_id"]
        ttype = r["target_type"]
        target = r["target_identifier"][:26] + ".."
        risk = f"{r['risk_score']:.3f}"
        focus = r["primary_focus_area"]
        print(f"{alert_id:<18} | {ttype:<7} | {target:<28} | {risk:<6} | {focus}")

    print("\n[+] Evidence Dossier on #1 Ranked Alert:")
    if rows:
        top = rows[0]
        evidence = json.loads(top["explanation_json"])
        print(json.dumps(evidence, indent=2))

    print("\n[+] Complete pipeline executed successfully.")


if __name__ == "__main__":
    main()
