#!/usr/bin/env python3
"""
Background Ingestion & Analytics Daemon.
Monitors the 'data/' directory for newly deposited telemetry files,
ignoring static seed lists and hidden files.
"""

import time
from pathlib import Path
from app.ingestion.bulk_parser import BulkDataParser
from app.engine.clustering import EntityClusterEngine
from app.engine.alert_generator import generate_investigative_alerts

WATCH_DIR = Path("data")
PROCESSED_LOG = Path(".processed_files.txt")
IGNORED_FILES = {"ofac_seeds.csv", "scam_seeds.json", ".gitkeep"}


def get_processed_files():
    if not PROCESSED_LOG.exists():
        return set()
    with open(PROCESSED_LOG, "r") as f:
        return set(line.strip() for line in f if line.strip())


def mark_processed(filename):
    with open(PROCESSED_LOG, "a") as f:
        f.write(f"{filename}\n")


def watch_and_process():
    print(f"[*] MARSAR Background Worker active. Watching: '{WATCH_DIR.resolve()}'")
    parser = BulkDataParser()
    cluster_engine = EntityClusterEngine()

    while True:
        processed = get_processed_files()
        new_files = [
            f for f in WATCH_DIR.glob("*")
            if f.suffix.lower() in (".csv", ".json", ".xml")
            and f.name not in processed
            and f.name not in IGNORED_FILES
        ]

        if new_files:
            for file_path in new_files:
                print(f"[+] New telemetry file detected: {file_path.name}")
                ext = file_path.suffix.lower()

                if ext == ".csv":
                    records = parser.parse_csv(str(file_path))
                elif ext == ".json":
                    records = parser.parse_json(str(file_path))
                else:
                    records = parser.parse_xml(str(file_path))

                count = parser.ingest_to_db(records)
                print(f"    -> Ingested {count} records.")
                mark_processed(file_path.name)

            print("[*] Re-running clustering and AI/ML detection engines...")
            cluster_engine.run_clustering()
            alerts = generate_investigative_alerts()
            print(f"[+] Generated {len(alerts)} alerts.")

        time.sleep(5)


if __name__ == "__main__":
    watch_and_process()