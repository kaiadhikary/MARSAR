#!/usr/bin/env python3
"""
Database Inspection Utility.
Displays row counts and summary statistics across all forensic tables.
"""

from app.db.sqlite_client import get_db_connection


def inspect():
    conn = get_db_connection()
    print("=== MARSAR FORENSIC DATABASE STATUS ===")

    tables = ["transactions", "entity_clusters", "illicit_seeds", "alerts"]
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"Table [{t}]: {count} records")

    # Sample transaction
    sample_tx = conn.execute("SELECT txid, src_ip, geo_country, total_input_btc FROM transactions LIMIT 1").fetchone()
    if sample_tx:
        print("\n--- Latest Sample Transaction ---")
        print(f"TXID: {sample_tx['txid']}")
        print(f"IP / Country: {sample_tx['src_ip']} ({sample_tx['geo_country']})")
        print(f"Volume: {sample_tx['total_input_btc']} BTC")

    conn.close()


if __name__ == "__main__":
    inspect()