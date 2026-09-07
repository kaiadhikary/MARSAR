"""
Database persistence layer for offline Bitcoin forensic intelligence.
Provides SQLite initialization, connection factories, and query interfaces.
"""

from app.db.sqlite_client import (
    DB_PATH,
    get_db_connection,
    init_db,
    reset_database,
    seed_initial_illicit_entities
)

__all__ = [
    "DB_PATH",
    "get_db_connection",
    "init_db",
    "reset_database",
    "seed_initial_illicit_entities"
]