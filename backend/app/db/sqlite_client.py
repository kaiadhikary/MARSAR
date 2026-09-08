import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent.parent / "marsar_offline.db"


def get_db_connection() -> sqlite3.Connection:
    """
    Returns an optimized SQLite connection configured for offline analytical querying.
    Enables Write-Ahead Logging (WAL) and dictionary-like Row factory access.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """
    Initializes database schemas for dual-layer network and blockchain metadata,
    entity clusters, illicit seed lists, and explainable investigative alerts.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Dual-Layer Transactions (Network metadata + Blockchain ledger state)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        txid TEXT PRIMARY KEY,
        timestamp INTEGER NOT NULL,
        src_ip TEXT NOT NULL,
        dst_ip TEXT NOT NULL,
        src_port INTEGER NOT NULL,
        dst_port INTEGER NOT NULL,
        fee REAL NOT NULL,
        script_type TEXT NOT NULL,
        geo_country TEXT NOT NULL,
        geo_asn TEXT NOT NULL,
        inputs_json TEXT NOT NULL,
        outputs_json TEXT NOT NULL,
        total_input_btc REAL NOT NULL,
        total_output_btc REAL NOT NULL
    );
    ''')

    # Indices for high-speed graph correlation & temporal range queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions(timestamp);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_src_ip ON transactions(src_ip);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_country ON transactions(geo_country);")

    # 2. Clustered Real-World Entities (Common-Input-Ownership + IP Co-location)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS entity_clusters (
        cluster_id TEXT NOT NULL,
        wallet_address TEXT PRIMARY KEY,
        primary_ip TEXT,
        confidence REAL DEFAULT 0.95
    );
    ''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cluster_id ON entity_clusters(cluster_id);")
    cluster_columns = {row[1] for row in cur.execute("PRAGMA table_info(entity_clusters)").fetchall()}
    if "evidence_json" not in cluster_columns:
        cur.execute("ALTER TABLE entity_clusters ADD COLUMN evidence_json TEXT NOT NULL DEFAULT '[]'")

    # 3. Known Illicit Seeds (OFAC Sanctions, Ransomware Wallets, Darknet Cashouts)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS illicit_seeds (
        address TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        severity REAL DEFAULT 1.0,
        added_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
    );
    ''')

    # 4. Ranked, Explainable Investigative Leads & Forensic Alerts
    cur.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY,
        target_type TEXT NOT NULL,          -- 'txid', 'wallet', or 'ip'
        target_identifier TEXT NOT NULL,
        risk_score REAL NOT NULL,
        confidence REAL NOT NULL,
        primary_focus_area TEXT NOT NULL,   -- e.g. 'Peeling-Chain Detection', 'Mixing / CoinJoin'
        anomaly_score REAL DEFAULT 0.0,
        taint_score REAL DEFAULT 0.0,
        peeling_chain_flag INTEGER DEFAULT 0,
        mixer_flag INTEGER DEFAULT 0,
        explanation_json TEXT NOT NULL,
        created_at INTEGER NOT NULL
    );
    ''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_risk ON alerts(risk_score DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_target ON alerts(target_identifier);")

    conn.commit()
    conn.close()

    # Pre-populate known seeds if empty
    seed_initial_illicit_entities()


def seed_initial_illicit_entities():
    """
    Populates default sanctions and ransomware seed addresses into the local database
    if the illicit_seeds table is uninitialized.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM illicit_seeds").fetchone()[0]

    if count == 0:
        default_seeds = [
            ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "OFAC_RANSOMWARE", 1.0),
            ("1CounterpartyXXXXXXXXXXXXXXXUWLpVr", "DARKNET_MARKET", 0.95),
            ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "MIXER_OPERATOR", 0.90),
            ("bc1qa5wkgaew2dkv56kfvj49j0av5nmar2m78chn7y", "EXCHANGE_HEIST", 0.85),
            ("12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX", "EXTORTION_CAMPAIGN", 0.80)
        ]
        cur.executemany('''
            INSERT OR IGNORE INTO illicit_seeds (address, category, severity)
            VALUES (?, ?, ?)
        ''', default_seeds)
        conn.commit()

    conn.close()


def reset_database():
    """Purges all records from analytical tables for a clean ingestion run."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM alerts;")
    cur.execute("DELETE FROM entity_clusters;")
    cur.execute("DELETE FROM transactions;")
    conn.commit()
    conn.close()


def fetch_all_transactions() -> List[Dict[str, Any]]:
    """Retrieves all ingested transaction records with deserialized input/output arrays."""
    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM transactions ORDER BY timestamp ASC").fetchall()
    conn.close()

    transactions = []
    for r in rows:
        d = dict(r)
        d["inputs"] = json.loads(d["inputs_json"])
        d["outputs"] = json.loads(d["outputs_json"])
        transactions.append(d)
    return transactions


def fetch_ranked_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves alerts ordered by composite risk score with parsed explanation JSON."""
    conn = get_db_connection()
    cur = conn.cursor()
    rows = cur.execute('''
        SELECT * FROM alerts 
        ORDER BY risk_score DESC 
        LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()

    alerts = []
    for r in rows:
        item = dict(r)
        item["explanation"] = json.loads(item["explanation_json"])
        alerts.append(item)
    return alerts
