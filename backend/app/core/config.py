"""
Environment configuration & constants.

Values are read from environment variables where present, with sane
defaults for local development. In production (AWS EC2), set these
via a .env file or systemd/Docker environment.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App metadata ---
    APP_NAME: str = "BTIF-Sentinel"
    API_V1_PREFIX: str = "/api/v1"

    # --- Ingestion sources (all free/public endpoints) ---
    MEMPOOL_WS_URL: str = "wss://mempool.space/api/v1/ws"
    BLOCKSTREAM_REST_URL: str = "https://blockstream.info/api"

    # --- Reconnect / backoff behaviour for the WebSocket consumer ---
    WS_RECONNECT_MIN_DELAY: float = 1.0
    WS_RECONNECT_MAX_DELAY: float = 30.0

    # --- Storage ---
    SQLITE_DB_PATH: str = "app/db/storage.db"

    # --- Auth ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 8

    # --- Risk scoring weights (4-layer formula) ---
    WEIGHT_TAINT: float = 0.40
    WEIGHT_TYPOLOGY: float = 0.25
    WEIGHT_ML_PROBABILITY: float = 0.20
    WEIGHT_MIXER_PENALTY: float = 0.15

    # --- Risk score thresholds ---
    THRESHOLD_SUSPICIOUS: int = 30
    THRESHOLD_HIGH_RISK: int = 70


settings = Settings()
