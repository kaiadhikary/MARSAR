#!/usr/bin/env python3
"""
Database Purge Utility.
Clears transaction, cluster, and alert tables for fresh batch ingestion.
"""

from app.db.sqlite_client import reset_database, get_db_connection


def main():
    print("[*] Resetting MARSAR analytical database tables...")
    reset_database()
    conn = get_db_connection()
    tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    alert_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    conn.close()
    print(f"[+] Database purged. Transactions: {tx_count}, Alerts: {alert_count}")


if __name__ == "__main__":
    main()