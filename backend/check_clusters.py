#!/usr/bin/env python3
"""
Clustering Inspection Utility.
Outputs entity clusters identified through Common-Input-Ownership Heuristics.
"""

from app.db.sqlite_client import get_db_connection


def view_clusters():
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT cluster_id, primary_ip, confidence, COUNT(wallet_address) as wallet_count,
               GROUP_CONCAT(wallet_address, ' | ') as wallets
        FROM entity_clusters
        GROUP BY cluster_id
        ORDER BY wallet_count DESC
    ''').fetchall()
    conn.close()

    print(f"=== IDENTIFIED ENTITY CLUSTERS ({len(rows)} TOTAL) ===")
    for r in rows:
        print(f"\nCluster ID: {r['cluster_id']} (Wallets: {r['wallet_count']}, Primary IP: {r['primary_ip']}, Conf: {r['confidence']})")
        print(f"Member Wallets: {r['wallets']}")


if __name__ == "__main__":
    view_clusters()