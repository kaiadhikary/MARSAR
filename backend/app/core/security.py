import hmac
import hashlib
import json
import secrets
import base64
import time
from typing import Any, Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


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
    """Issue an HMAC-signed, expiring, offline bearer token."""
    if not settings.FORENSIC_SECRET_KEY:
        raise RuntimeError("MARSAR_FORENSIC_SECRET_KEY must be configured before authentication is enabled.")
    payload = {"role": "LEAD_INVESTIGATOR", "exp": int(time.time()) + settings.AUTH_TOKEN_TTL_SECONDS,
               "nonce": secrets.token_hex(12)}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.FORENSIC_SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


async def require_investigator(credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)) -> bool:
    """
    FastAPI security dependency for securing endpoints when REQUIRE_AUTH is enabled.
    """
    if not settings.REQUIRE_AUTH:
        return True

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token missing."
        )
    try:
        encoded, signature = credentials.credentials.rsplit(".", 1)
        expected = hmac.new(settings.FORENSIC_SECRET_KEY.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.")
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token."
        )
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token expired.")
    return True


verify_api_key = require_investigator  # Backwards-compatible import name.
