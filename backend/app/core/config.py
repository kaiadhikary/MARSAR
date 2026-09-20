from pathlib import Path
from typing import Set, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MARSAR_", case_sensitive=True)
    PROJECT_NAME: str = "MARSAR - Bitcoin Forensic Intelligence Engine"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / "marsar_offline.db"
    WEIGHTS_PATH: Path = BASE_DIR / "app" / "ml" / "weights" / "bitcoin_network_gbdt.joblib"
    MODELS_DIR: Path = BASE_DIR / "models"
    REPORTS_OUTPUT_DIR: Path = BASE_DIR / "app" / "reports" / "output"

    FORENSIC_SECRET_KEY: str = ""
    AUTH_TOKEN_TTL_SECONDS: int = 28800
    REQUIRE_AUTH: bool = False

    PEELING_ASYMMETRY_RATIO_MIN: float = 4.0
    COINJOIN_MIN_PARTICIPANTS: int = 3
    COINJOIN_EQUAL_DENOM_RATIO_MIN: float = 0.50
    TAINT_DECAY_FACTOR: float = 0.85
    TAINT_MAX_HOPS: int = 3
    ANOMALY_CONTAMINATION: float = 0.08
    COMPOSITE_ALERT_THRESHOLD: float = 0.35

    STANDARD_BITCOIN_PORTS: Set[int] = {8333, 18333, 80, 443}
    HIGH_RISK_ASNS: Set[str] = {
        "AS12389",
        "AS58224",
        "AS49981",
        "AS205100",
        "AS51852",
    }
    HIGH_RISK_COUNTRIES: Set[str] = {"RU", "IR", "KP", "SC", "VG"}

    RISK_WEIGHTS: Dict[str, float] = {
        "ml": 0.25, "taint": 0.25, "anomaly": 0.20,
        "demixing": 0.20, "heuristics": 0.05, "network": 0.05,
    }

settings = Settings()

if abs(sum(settings.RISK_WEIGHTS.values()) - 1.0) > 1e-9:
    raise ValueError("RISK_WEIGHTS must sum to 1.0")
