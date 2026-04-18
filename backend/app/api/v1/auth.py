from __future__ import annotations
"""API endpoints for user authentication and external connections (Komoot, Strava)."""

from datetime import timezone, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.models.subscription import Subscription
from app.db.models.user import StravaToken, User

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class KomootCredentials(BaseModel):
    email: str
    password: str
    user_id: str

class StravaCallback(BaseModel):
    code: str


@router.post("/register", response_model=TokenResponse)
async def register_user(
    payload: RegisterRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> TokenResponse:
    """Create a new user account and issue an access token."""
    existing_result = await db.execute(select(User).where(User.email == payload.email))
    existing_user = existing_result.scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email is already registered.")

    user = User(
        email=payload.email,
        password_hash=security.hash_password(payload.password),
        is_active=True,
    )
    db.add(user)

    subscription = Subscription(
        user=user,
        tier="free",
        status="active",
    )
    db.add(subscription)
    await db.commit()

    access_token = security.create_access_token(str(user.id))
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    payload: LoginRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> TokenResponse:
    """Authenticate a user by email/password and issue an access token."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not user.password_hash or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")

    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User account is inactive.")

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    access_token = security.create_access_token(str(user.id))
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    user: User = Depends(deps.get_current_user),
) -> TokenResponse:
    """Issue a fresh access token for the authenticated user."""
    access_token = security.create_access_token(str(user.id))
    return TokenResponse(access_token=access_token)

@router.get("/me")
async def get_current_user_profile(
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    """Retrieve the current logged-in user profile and connection statuses."""
    return {
        "id": str(user.id),
        "email": user.email,
        "is_active": user.is_active,
        "komoot_connected": bool(user.komoot_user_id),
        "strava_connected": bool(user.strava_token),
    }

@router.get("/strava/login")
async def get_strava_login_url() -> dict[str, str]:
    """Return the Strava OAuth login URL for the frontend to redirect the user to."""
    redirect_uri = f"{settings.FRONTEND_URL}/strava-callback"
    url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={settings.STRAVA_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={redirect_uri}"
        "&approval_prompt=force"
        "&scope=activity:write,activity:read_all"
    )
    return {"url": url}

@router.post("/strava/callback")
async def strava_oauth_callback(
    payload: StravaCallback,
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, str]:
    """Exchange OAuth code for Strava tokens and save to user profile."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": settings.STRAVA_CLIENT_ID,
                    "client_secret": settings.STRAVA_CLIENT_SECRET,
                    "code": payload.code,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strava authentication failed: {exc}",
        )

    # Note: Using app_id=1 as default if `StravaApp` multi-tenant table isn't populated dynamically
    # For a self-hosted individual instance, this works exactly as intended.
    athlete_id = int(data["athlete"]["id"])
    
    if user.strava_token:
        user.strava_token.access_token = security.encrypt(data["access_token"])
        user.strava_token.refresh_token = security.encrypt(data["refresh_token"])
        user.strava_token.expires_at = datetime.fromtimestamp(data["expires_at"], tz=timezone.utc)
        user.strava_token.strava_athlete_id = athlete_id
    else:
        new_token = StravaToken(
            user_id=user.id,
            strava_app_id=1, 
            strava_athlete_id=athlete_id,
            access_token=security.encrypt(data["access_token"]),
            refresh_token=security.encrypt(data["refresh_token"]),
            expires_at=datetime.fromtimestamp(data["expires_at"], tz=timezone.utc),
            connected_at=datetime.now(timezone.utc)
        )
        db.add(new_token)
        
    await db.commit()
    return {"status": "success", "message": "Strava account connected"}

@router.post("/komoot")
async def setup_komoot_connection(
    payload: KomootCredentials,
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, str]:
    """Save encrypted Komoot credentials to user profile."""
    user.komoot_email_encrypted = security.encrypt(payload.email)
    user.komoot_password_encrypted = security.encrypt(payload.password)
    user.komoot_user_id = payload.user_id
    user.komoot_connected_at = datetime.now(timezone.utc)
    
    # Enable sync by default when they connect valid credentials
    user.sync_komoot_to_strava = True
    
    await db.commit()
    return {"status": "success", "message": "Komoot connected successfully"}


@router.delete("/strava/disconnect")
async def disconnect_strava(
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, str]:
    """Remove the current Strava connection."""
    result = await db.execute(select(StravaToken).where(StravaToken.user_id == user.id))
    token = result.scalar_one_or_none()
    if token is not None:
        await db.delete(token)
        await db.commit()
    return {"status": "success", "message": "Strava account disconnected"}


@router.delete("/komoot/disconnect")
async def disconnect_komoot(
    user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, str]:
    """Remove stored Komoot credentials for the current user."""
    user.komoot_email_encrypted = None
    user.komoot_password_encrypted = None
    user.komoot_user_id = None
    user.komoot_connected_at = None
    user.sync_komoot_to_strava = False
    await db.commit()
    return {"status": "success", "message": "Komoot account disconnected"}
