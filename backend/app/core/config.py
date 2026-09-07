from pathlib import Path
from typing import Set, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration for offline air-gapped forensic operations.
    Loads environment variables or defaults without remote network dependencies.
    """
    PROJECT_NAME: str = "MARSAR - Bitcoin Forensic Intelligence Engine"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "marsar_offline.db"
    WEIGHTS_PATH: Path = BASE_DIR / "app" / "ml" / "weights" / "elliptic_xgb.joblib"
    REPORTS_OUTPUT_DIR: Path = BASE_DIR / "app" / "reports" / "output"

    # Security & Chain of Custody
    FORENSIC_SECRET_KEY: str = "marsar_offline_tamper_evident_master_key_2026"
    API_KEY_HEADER_NAME: str = "X-Forensic-Token"
    REQUIRE_AUTH: bool = False  # Disabled by default for direct local CLI/evaluator usage

    # Detection Engine Thresholds
    PEELING_ASYMMETRY_RATIO_MIN: float = 4.0
    COINJOIN_MIN_PARTICIPANTS: int = 3
    COINJOIN_EQUAL_DENOM_RATIO_MIN: float = 0.50
    TAINT_DECAY_FACTOR: float = 0.85
    TAINT_MAX_HOPS: int = 3
    ANOMALY_CONTAMINATION: float = 0.08
    COMPOSITE_ALERT_THRESHOLD: float = 0.35

    # Suspicious Network Markers
    STANDARD_BITCOIN_PORTS: Set[int] = {8333, 18333, 80, 443}
    HIGH_RISK_ASNS: Set[str] = {
        "AS12389",  # Rostelecom
        "AS58224",  # TIC
        "AS49981",  # WorldStream
        "AS205100", # Tor Exit Relay
        "AS51852"   # Bulletproof Hosting
    }
    HIGH_RISK_COUNTRIES: Set[str] = {"RU", "IR", "KP", "SC", "VG"}

    # Scoring Weights for Multi-Factor Lead Prioritization
    WEIGHT_TAINT: float = 0.30
    WEIGHT_ANOMALY: float = 0.25
    WEIGHT_DEMIXING: float = 0.25
    WEIGHT_HEURISTICS: float = 0.10
    WEIGHT_NETWORK_GEO: float = 0.10

    class Config:
        case_sensitive = True


settings = Settings()