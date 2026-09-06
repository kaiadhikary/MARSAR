# Schema definitions & B-tree query handlers

"""
MARSAR Database Engine: SQLite Client
# Schema definitions & B-tree query handlers
Handles persistent clustering state, transaction telemetry, and threat intelligence indexing.
"""
from __future__ import annotations

import csv
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("marsar.db")


# =====================================================================
# Connection Management (WAL Mode)
# =====================================================================

def get_db_connection() -> sqlite3.Connection:
    """Instantiates a connection with Write-Ahead Logging for concurrent pipeline reads/writes."""
    db_path = Path(settings.SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    return conn


# =====================================================================
# Schema Definitions & B-Tree Indexes
# =====================================================================

def init_db() -> None:
    """Creates the relational forensic schema and associated B-tree lookup indexes."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Threat Intelligence Seeds Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklisted_seeds (
                address TEXT PRIMARY KEY,
                entity_label TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Cluster Roots Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_id TEXT PRIMARY KEY,
                root_address TEXT NOT NULL UNIQUE,
                member_count INTEGER DEFAULT 1,
                risk_score REAL DEFAULT 0.0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. Address-to-Cluster Membership Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS address_clusters (
                address TEXT PRIMARY KEY,
                cluster_id TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cluster_id) REFERENCES clusters(cluster_id) ON DELETE CASCADE
            );
        """)

        # 4. Ingested Transaction Registry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                txid TEXT PRIMARY KEY,
                inputs_count INTEGER NOT NULL,
                outputs_count INTEGER NOT NULL,
                fee_rate REAL DEFAULT 0.0,
                is_coinjoin INTEGER DEFAULT 0,
                shannon_entropy REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Transaction-to-address relationships for graph/trace lookup.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_addresses (
                txid TEXT NOT NULL,
                address TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('INPUT', 'OUTPUT')),
                value_sats INTEGER DEFAULT 0,
                PRIMARY KEY (txid, address, direction),
                FOREIGN KEY (txid) REFERENCES transactions(txid) ON DELETE CASCADE
            );
        """)

        # B-Tree Indexes for fast point queries and range evaluations
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_btree_ac_cluster_id ON address_clusters(cluster_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_btree_seeds_cat ON blacklisted_seeds(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_btree_tx_cj ON transactions(is_coinjoin);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_btree_tx_created ON transactions(created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_btree_ta_address ON transaction_addresses(address);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_btree_ta_txid ON transaction_addresses(txid);")

        conn.commit()

        # ---------------------------------------------------------------
        # Engine 5 migration: add risk-scoring columns to `transactions`
        # for DBs created before Engine 5 existed (ALTER TABLE ADD COLUMN
        # errors if the column is already there, so guard with a check).
        # ---------------------------------------------------------------
        _ensure_column(conn, "transactions", "cluster_id", "TEXT")
        _ensure_column(conn, "transactions", "risk_score", "REAL DEFAULT 0.0")
        _ensure_column(conn, "transactions", "blacklist_hit", "INTEGER DEFAULT 0")
        _ensure_column(conn, "transactions", "typology_flags", "TEXT DEFAULT ''")
        _ensure_column(conn, "transactions", "ml_probability", "REAL DEFAULT 0.0")
        _ensure_column(conn, "transactions", "taint_score", "REAL DEFAULT 0.0")
        _ensure_column(conn, "transactions", "typology_score", "REAL DEFAULT 0.0")
        _ensure_column(conn, "transactions", "mixer_penalty_score", "REAL DEFAULT 0.0")
        _ensure_column(conn, "transactions", "risk_verdict", "TEXT DEFAULT 'LICIT'")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_btree_tx_risk ON transactions(risk_score);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_btree_tx_cluster ON transactions(cluster_id);")
        conn.commit()

        logger.info("Forensic SQLite tables and B-tree indexes initialized at: %s", settings.SQLITE_DB_PATH)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, coltype: str) -> None:
    """Adds `column` to `table` if it doesn't already exist (safe schema migration)."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table});")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype};")
        logger.info("Migrated schema: added %s.%s", table, column)


# =====================================================================
# Seed Ingestion Handlers
# =====================================================================

def load_seed_data() -> None:
    """Loads and deduplicates OFAC sanctions CSV and CryptoScamDB records into blacklisted_seeds."""
    ofac_path = Path(settings.OFAC_SEEDS_PATH)
    scam_path = Path(settings.SCAM_SEEDS_PATH)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Ingest OFAC Sanctions
        if ofac_path.exists():
            try:
                with open(ofac_path, mode="r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    records: List[Tuple[str, str, str, str]] = []
                    for row in reader:
                        addr = row.get("address") or row.get("crypto_address") or row.get("Address")
                        entity = row.get("entity") or row.get("name") or row.get("Entity") or "OFAC Sanctioned"
                        if addr and len(addr.strip()) > 10:
                            records.append((addr.strip(), entity.strip(), "SANCTION", "OFAC"))

                    if records:
                        cursor.executemany("""
                            INSERT OR IGNORE INTO blacklisted_seeds (address, entity_label, category, source)
                            VALUES (?, ?, ?, ?);
                        """, records)
                        logger.info("Indexed %d OFAC sanction addresses into SQLite B-tree.", len(records))
            except Exception as err:
                logger.error("Error reading OFAC seed dataset: %s", err)

        # Ingest CryptoScamDB JSON
        if scam_path.exists():
            try:
                with open(scam_path, mode="r", encoding="utf-8") as f:
                    data = json.load(f)
                    scam_records: List[Tuple[str, str, str, str]] = []
                    entries = data if isinstance(data, list) else data.get("scams", data.get("result", []))

                    for item in entries:
                        if isinstance(item, dict):
                            addrs = item.get("addresses", item.get("coin_addresses", []))
                            name = item.get("name", "Malicious Scam")
                            cat = item.get("category", "SCAM")
                            if isinstance(addrs, str):
                                addrs = [addrs]
                            for addr in addrs:
                                if addr and len(addr.strip()) > 10:
                                    scam_records.append((addr.strip(), name.strip(), cat.upper(), "CryptoScamDB"))
                        elif isinstance(item, str) and len(item.strip()) > 10:
                            scam_records.append((item.strip(), "Known Threat Actor", "SCAM", "CryptoScamDB"))

                    if scam_records:
                        cursor.executemany("""
                            INSERT OR IGNORE INTO blacklisted_seeds (address, entity_label, category, source)
                            VALUES (?, ?, ?, ?);
                        """, scam_records)
                        logger.info("Indexed %d CryptoScamDB addresses into SQLite B-tree.", len(scam_records))
            except Exception as err:
                logger.error("Error reading CryptoScamDB seed dataset: %s", err)

        conn.commit()


# =====================================================================
# B-Tree Query Handlers & Persistence Operations
# =====================================================================

def check_address_blacklist(address: str) -> Optional[Dict[str, Any]]:
    """Performs an O(log N) B-tree point lookup for blacklisted addresses."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT address, entity_label, category, source, created_at
            FROM blacklisted_seeds
            WHERE address = ?;
        """, (address,))
        row = cursor.fetchone()
        return dict(row) if row else None


def persist_cluster_merge(root_address: str, member_addresses: List[str]) -> None:
    """Updates the cluster root and maps all member addresses into the cluster table."""
    if not root_address or not member_addresses:
        return

    cluster_id = f"entity_{root_address[:16]}"
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Upsert root cluster record
        cursor.execute("""
            INSERT INTO clusters (cluster_id, root_address, member_count, last_updated)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(cluster_id) DO UPDATE SET
                member_count = member_count + excluded.member_count,
                last_updated = CURRENT_TIMESTAMP;
        """, (cluster_id, root_address, len(member_addresses)))

        # Upsert address mappings
        addr_params = [(addr, cluster_id) for addr in member_addresses if addr]
        cursor.executemany("""
            INSERT INTO address_clusters (address, cluster_id)
            VALUES (?, ?)
            ON CONFLICT(address) DO UPDATE SET
                cluster_id = excluded.cluster_id;
        """, addr_params)

        conn.commit()


def persist_transaction(
    txid: str,
    inputs_count: int,
    outputs_count: int,
    fee_rate: float,
    is_coinjoin: bool,
    entropy: float,
    cluster_id: Optional[str] = None,
    risk_score: float = 0.0,
    blacklist_hit: bool = False,
    typology_flags: str = "",
    ml_probability: float = 0.0,
    taint_score: float = 0.0,
    typology_score: float = 0.0,
    mixer_penalty_score: float = 0.0,
    risk_verdict: str = "LICIT",
    input_addresses: Optional[List[Tuple[str, int]]] = None,
    output_addresses: Optional[List[Tuple[str, int]]] = None,
) -> None:
    """Persist transaction metadata, Engine 5 breakdown, and TX addresses."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (
                txid, inputs_count, outputs_count, fee_rate, is_coinjoin, shannon_entropy,
                cluster_id, risk_score, blacklist_hit, typology_flags,
                ml_probability, taint_score, typology_score, mixer_penalty_score, risk_verdict
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(txid) DO UPDATE SET
                cluster_id = excluded.cluster_id,
                risk_score = excluded.risk_score,
                blacklist_hit = excluded.blacklist_hit,
                typology_flags = excluded.typology_flags,
                ml_probability = excluded.ml_probability,
                taint_score = excluded.taint_score,
                typology_score = excluded.typology_score,
                mixer_penalty_score = excluded.mixer_penalty_score,
                risk_verdict = excluded.risk_verdict;
        """, (
            txid, inputs_count, outputs_count, fee_rate, int(is_coinjoin), entropy,
            cluster_id, risk_score, int(blacklist_hit), typology_flags,
            ml_probability, taint_score, typology_score, mixer_penalty_score, risk_verdict,
        ))
        cursor.execute("DELETE FROM transaction_addresses WHERE txid = ?;", (txid,))
        rows: List[Tuple[str, str, str, int]] = []
        for address, value in (input_addresses or []):
            if address:
                rows.append((txid, address, "INPUT", int(value or 0)))
        for address, value in (output_addresses or []):
            if address:
                rows.append((txid, address, "OUTPUT", int(value or 0)))
        if rows:
            cursor.executemany("""
                INSERT OR REPLACE INTO transaction_addresses
                    (txid, address, direction, value_sats)
                VALUES (?, ?, ?, ?);
            """, rows)
        conn.commit()


def update_cluster_risk_score(cluster_id: str, risk_score: float) -> None:
    """
    Records the highest risk score ever observed for a cluster (Engine 5
    output). Uses MAX() rather than overwrite so a cluster that was once
    flagged high-risk doesn't quietly drop back to 0 just because a later,
    unrelated low-risk transaction touched the same entity.
    """
    if not cluster_id:
        return
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE clusters
            SET risk_score = MAX(risk_score, ?), last_updated = CURRENT_TIMESTAMP
            WHERE cluster_id = ?;
        """, (risk_score, cluster_id))
        conn.commit()


def get_recent_transactions(limit: int = 10) -> List[Dict[str, Any]]:
    """Returns the most recently ingested transactions, newest first."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT txid, cluster_id, risk_score, risk_verdict,
                   ml_probability, taint_score, typology_score, mixer_penalty_score,
                   is_coinjoin, blacklist_hit, typology_flags,
                   fee_rate, shannon_entropy, created_at
            FROM transactions
            ORDER BY created_at DESC
            LIMIT ?;
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_suspicious_transactions(
    min_risk_score: float = 30.0,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Returns transactions at/above `min_risk_score` (defaults to
    THRESHOLD_SUSPICIOUS = 30, per the Engine 5 scoring spec), highest
    risk first. Pass `limit=None` for all matches.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT txid, cluster_id, risk_score, risk_verdict,
                   ml_probability, taint_score, typology_score, mixer_penalty_score,
                   is_coinjoin, blacklist_hit, typology_flags,
                   fee_rate, shannon_entropy, created_at
            FROM transactions
            WHERE risk_score >= ?
            ORDER BY risk_score DESC, created_at DESC
        """
        params: List[Any] = [min_risk_score]
        if limit is not None:
            query += " LIMIT ?;"
            params.append(limit)
        else:
            query += ";"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_cluster_members(cluster_id: str) -> List[str]:
    """Returns every address mapped to `cluster_id`."""
    if not cluster_id:
        return []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT address FROM address_clusters WHERE cluster_id = ?;", (cluster_id,))
        return [row["address"] for row in cursor.fetchall()]


def get_cluster_root(cluster_id: str) -> Optional[str]:
    """Returns the root address for `cluster_id`, or None if it doesn't exist."""
    if not cluster_id:
        return None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT root_address FROM clusters WHERE cluster_id = ?;", (cluster_id,))
        row = cursor.fetchone()
        return row["root_address"] if row else None


def get_cluster_by_address(address: str) -> Optional[Dict[str, Any]]:
    """Retrieves cluster metadata and all associated co-spent addresses for a given address."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.cluster_id, c.root_address, c.member_count, c.risk_score, c.first_seen, c.last_updated
            FROM address_clusters ac
            JOIN clusters c ON ac.cluster_id = c.cluster_id
            WHERE ac.address = ?;
        """, (address,))
        row = cursor.fetchone()
        if not row:
            return None

        cluster_info = dict(row)
        cursor.execute("""
            SELECT address FROM address_clusters WHERE cluster_id = ? LIMIT 100;
        """, (cluster_info["cluster_id"],))
        cluster_info["members"] = [r["address"] for r in cursor.fetchall()]
        return cluster_info


def get_transaction_addresses(txid: str) -> List[Dict[str, Any]]:
    """Returns persisted input/output addresses for a transaction."""
    if not txid:
        return []
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT txid, address, direction, value_sats
            FROM transaction_addresses
            WHERE txid = ?
            ORDER BY direction, address;
        """, (txid,))
        return [dict(row) for row in cursor.fetchall()]
