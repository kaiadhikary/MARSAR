#!/usr/bin/env python3
"""
Transaction Ledger Verification Utility.
Prints parsed transaction records with dual-layer telemetry.
"""

from app.db.sqlite_client import get_db_connection
import json


def view_transactions(limit=5):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()

    print(f"=== DISPLAYING RECENT {len(rows)} TRANSACTIONS ===")
    for r in rows:
        print(f"\nTXID: {r['txid']}")
        print(f"Timestamp: {r['timestamp']} | Fee: {r['fee']} BTC | Script: {r['script_type']}")
        print(f"Network Origin: {r['src_ip']}:{r['src_port']} -> {r['dst_ip']}:{r['dst_port']}")
        print(f"Location: {r['geo_country']} ({r['geo_asn']})")
        print(f"Inputs: {json.loads(r['inputs_json'])}")
        print(f"Outputs: {json.loads(r['outputs_json'])}")


if __name__ == "__main__":
    view_transactions()