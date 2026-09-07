import hmac
import hashlib
import json
import secrets
from typing import Any, Optional
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)


def hash_forensic_payload(payload: Any) -> str:
    """
    Computes a deterministic SHA-256 hash string for tamper-evident data custody.
    """
    if isinstance(payload, (dict, list)):
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    elif isinstance(payload, bytes):
        return hashlib.sha256(payload).hexdigest()
    else:
        serialized = str(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def sign_forensic_artifact(payload: Any) -> str:
    """
    Produces an HMAC-SHA256 signature for evidence dossiers using the internal offline secret.
    """
    digest = hash_forensic_payload(payload)
    signature = hmac.new(
        settings.FORENSIC_SECRET_KEY.encode("utf-8"),
        digest.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_payload_signature(payload: Any, signature: str) -> bool:
    """
    Verifies that the provided HMAC-SHA256 signature matches the payload.
    """
    expected = sign_forensic_artifact(payload)
    return hmac.compare_digest(expected.lower(), signature.lower())


def generate_investigator_token() -> str:
    """
    Generates a cryptographically strong local investigator session token.
    """
    return secrets.token_hex(24)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """
    FastAPI security dependency for securing endpoints when REQUIRE_AUTH is enabled.
    """
    if not settings.REQUIRE_AUTH:
        return True

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forensic authentication credentials missing."
        )

    # Validate against known local secrets
    is_valid = hmac.compare_digest(api_key, settings.FORENSIC_SECRET_KEY)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid forensic session token."
        )
    return True