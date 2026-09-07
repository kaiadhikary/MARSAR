"""
Core application settings, security primitives, and local broadcast mechanisms.
Ensures strict air-gapped execution and tamper-evident forensic logging.
"""

from app.core.config import settings
from app.core.security import (
    verify_api_key,
    generate_investigator_token,
    hash_forensic_payload,
    verify_payload_signature
)
from app.core.broadcast import local_broadcaster

__all__ = [
    "settings",
    "verify_api_key",
    "generate_investigator_token",
    "hash_forensic_payload",
    "verify_payload_signature",
    "local_broadcaster",
]