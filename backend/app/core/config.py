import os
from pathlib import Path
from typing import List

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings
    SettingsConfigDict = None

# Root directory pointing to backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "MARSAR - Bitcoin Forensics & AML"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS configuration
    # NOTE: "*" was dropped deliberately — a wildcard origin combined with
    # any future cookie/JWT-bearing request is a real exposure. Add specific
    # deployed frontend origins (e.g. your Vercel URL) here instead of
    # reintroducing "*".
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Ingestion feeds & APIs
    MEMPOOL_WS_URL: str = "wss://mempool.space/api/v1/ws"
    MEMPOOL_API_BASE_URL: str = "https://mempool.space/api"
    BLOCKSTREAM_API_BASE_URL: str = "https://blockstream.info/api"

    # WebSocket connection parameters
    WS_RECONNECT_MIN_DELAY: float = 1.0
    WS_RECONNECT_MAX_DELAY: float = 30.0

    # Persistence storage
    SQLITE_DB_PATH: str = str(BASE_DIR / "app" / "db" / "storage.db")

    # Security & Analyst JWT
    SECRET_KEY: str = "marsar-forensics-sih26146-super-secret-key-32bytes-min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Seed data & ML artifacts
    OFAC_SEEDS_PATH: str = str(BASE_DIR / "data" / "ofac_seeds.csv")
    SCAM_SEEDS_PATH: str = str(BASE_DIR / "data" / "scam_seeds.json")
    ELLIPTIC_MODEL_PATH: str = str(BASE_DIR / "app" / "ml" / "weights" / "elliptic_xgb.joblib")

    # Heuristic & Demixing engine tuning
    SUBSET_SUM_MAX_COMBINATIONS_DEPTH: int = 4
    SUBSET_SUM_MAX_ITEMS_PER_SIDE: int = 16
    RAPID_VELOCITY_SECONDS_THRESHOLD: float = 90.0

    # Engine 4 — Typology & Graph Structural tuning
    SCATTER_GATHER_MIN_FANOUT: int = 15
    SCATTER_GATHER_MAX_WINDOW_SECONDS: float = 3 * 3600.0  # gather within hours
    PEELING_CHAIN_MIN_HOPS: int = 3

    # Risk scoring weights (4-layer formula, Engine 5) — restored here after
    # being dropped in an earlier edit; scoring.py is still a stub but these
    # need to exist before that engine is wired up.
    WEIGHT_TAINT: float = 0.40
    WEIGHT_TYPOLOGY: float = 0.25
    WEIGHT_ML_PROBABILITY: float = 0.20
    WEIGHT_MIXER_PENALTY: float = 0.15
    THRESHOLD_SUSPICIOUS: int = 30
    THRESHOLD_HIGH_RISK: int = 70

    # Pydantic v1 / v2 compatibility layer
    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore",
        )
    else:
        class Config:
            env_file = ".env"
            case_sensitive = True
            extra = "ignore"


settings = Settings()