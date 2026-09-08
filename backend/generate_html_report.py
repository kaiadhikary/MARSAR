#!/usr/bin/env python3
"""
Suspicious Transaction Report (STR) HTML Generator CLI.
Generates an air-gapped forensic report for a specific TXID or the top-ranked alert.
"""

import sys
import argparse
from app.db.sqlite_client import get_db_connection
from app.reports.generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate forensic STR HTML dossier.")
    parser.add_argument("--txid", type=str, help="Specific transaction ID to report.")
    args = parser.parse_args()

    txid = args.txid
    if not txid:
        conn = get_db_connection()
        top_alert = conn.execute(
            "SELECT target_identifier FROM alerts WHERE target_type = 'txid' ORDER BY risk_score DESC LIMIT 1"
        ).fetchone()
        conn.close()
        if not top_alert:
            print("[-] No transaction alerts found in database. Run the pipeline first.")
            sys.exit(1)
        txid = top_alert["target_identifier"]

    print(f"[*] Compiling forensic report for TXID: {txid}")
    generator = ReportGenerator()
    result = generator.generate_html_str(txid)

    if result:
        print(f"[+] Forensic STR dossier generated successfully:")
        print(f"    File: {result['report_path']}")
        print(f"    Chain-of-Custody SHA-256: {result['chain_of_custody_hash']}")
    else:
        print(f"[-] Failed to generate report. Transaction not found.")


if __name__ == "__main__":
    main()