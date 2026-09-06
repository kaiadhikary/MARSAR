"""
cluster_explorer.py — pick recent or suspicious transactions and see the
full cluster (entity) address set behind each one.

Usage (interactive menu):
    python cluster_explorer.py

Usage (non-interactive, for scripting):
    python cluster_explorer.py --mode recent --limit 10
    python cluster_explorer.py --mode suspicious --min-score 30
    python cluster_explorer.py --mode suspicious --min-score 70   # high-risk only
"""
from __future__ import annotations

import argparse
import sys

from app.core.config import settings
from app.db.sqlite_client import (
    get_recent_transactions,
    get_suspicious_transactions,
    get_cluster_members,
    get_cluster_root,
    get_transaction_addresses,
)


def _print_tx_cluster(tx: dict, index: int) -> None:
    print(f"\n[{index}] TX {tx['txid']}")
    print(f"    Risk score : {tx['risk_score']:.1f}/100")
    print(f"    CoinJoin?  : {'yes' if tx['is_coinjoin'] else 'no'}")
    print(f"    Blacklist? : {'yes' if tx['blacklist_hit'] else 'no'}")
    print(f"    Flags      : {tx['typology_flags'] or '(none)'}")
    print(f"    Ingested   : {tx['created_at']}")
    print(f"    Risk verdict: {tx.get('risk_verdict', '(not stored)')}")
    print(
        f"    E5 layers  : Taint={tx.get('taint_score', 0):.1f}, "
        f"Typology={tx.get('typology_score', 0):.1f}, "
        f"ML={tx.get('ml_probability', 0):.3f}, "
        f"Mixer={tx.get('mixer_penalty_score', 0):.1f}"
    )
    tx_addresses = get_transaction_addresses(tx["txid"])
    if tx_addresses:
        print("    TX addresses:")
        for row in tx_addresses:
            print(f"      {row['direction']:<6} {row['address']} ({row['value_sats']} sats)")

    cluster_id = tx.get("cluster_id")
    if not cluster_id:
        print("    Cluster    : (none — Engine 2 did not create a CIOH cluster for this TX)")
        return

    root = get_cluster_root(cluster_id)
    members = get_cluster_members(cluster_id)
    print(f"    Cluster ID : {cluster_id}")
    print(f"    Root addr  : {root}")
    print(f"    Members ({len(members)}):")
    for addr in members:
        marker = "★" if addr == root else "-"
        print(f"      {marker} {addr}")


def show_recent(limit: int) -> None:
    txs = get_recent_transactions(limit=limit)
    if not txs:
        print("No transactions ingested yet — make sure run_worker.py has been running.")
        return
    print(f"\n=== Top {len(txs)} most recent transactions & their clusters ===")
    for i, tx in enumerate(txs, start=1):
        _print_tx_cluster(tx, i)


def show_suspicious(min_score: float) -> None:
    txs = get_suspicious_transactions(min_risk_score=min_score)
    if not txs:
        print(f"No transactions found with risk score >= {min_score}.")
        print("(This is expected until Engine 5's ML model is trained/loaded and/or")
        print(" the worker has seen a transaction that hit the blacklist, a typology")
        print(" flag, or a confident CoinJoin — those are what currently drive the score.)")
        return
    print(f"\n=== {len(txs)} transaction(s) with risk score >= {min_score} & their clusters ===")
    for i, tx in enumerate(txs, start=1):
        _print_tx_cluster(tx, i)


def interactive_menu() -> None:
    print("=" * 60)
    print(" MARSAR — Cluster Explorer")
    print("=" * 60)
    print("1) Top 10 recent transactions -> cluster addresses")
    print("2) All suspicious transactions -> cluster addresses")
    print("0) Exit")
    choice = input("\nSelect an option: ").strip()

    if choice == "1":
        show_recent(limit=10)
    elif choice == "2":
        default = settings.THRESHOLD_SUSPICIOUS
        raw = input(
            f"Minimum risk score to count as 'suspicious' [default {default}]: "
        ).strip()
        min_score = float(raw) if raw else float(default)
        show_suspicious(min_score=min_score)
    elif choice == "0":
        print("Bye.")
        return
    else:
        print("Not a valid option.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore cluster addresses behind recent/suspicious transactions.")
    parser.add_argument("--mode", choices=["recent", "suspicious"], help="Skip the menu and run directly.")
    parser.add_argument("--limit", type=int, default=10, help="For --mode recent: how many transactions (default 10).")
    parser.add_argument(
        "--min-score", type=float, default=None,
        help="For --mode suspicious: minimum risk score (default: settings.THRESHOLD_SUSPICIOUS, currently "
             f"{settings.THRESHOLD_SUSPICIOUS}).",
    )
    args = parser.parse_args()

    if args.mode == "recent":
        show_recent(limit=args.limit)
    elif args.mode == "suspicious":
        show_suspicious(min_score=args.min_score if args.min_score is not None else float(settings.THRESHOLD_SUSPICIOUS))
    else:
        interactive_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
