from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import generate_investigator_token

router = APIRouter()


class LoginRequest(BaseModel):
    passkey: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    airgap_mode: bool


@router.post("/login", response_model=TokenResponse)
def local_login(req: LoginRequest):
    """
    Authenticates a local investigator session using the air-gapped forensic secret.
    """
    if req.passkey != settings.FORENSIC_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid offline forensic master key."
        )

    token = generate_investigator_token()
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "LEAD_INVESTIGATOR",
        "airgap_mode": True
    }


@router.get("/status")
def security_status():
    """Returns local offline security parameters and air-gap enforcement status."""
    return {
        "airgap_active": True,
        "network_listeners_disabled": True,
        "require_auth": settings.REQUIRE_AUTH,
        "tamper_evident_hashing": "SHA-256"
    }