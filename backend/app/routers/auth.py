"""Account endpoints: register, login, token refresh, the user's own profile, and their data
(consent to cloud processing, export, account deletion: PDPA access and erasure)."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    user_from_token,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.limits import client_ip, limiter
from app.models.live_session import LIVE_IN_PROGRESS_STATUSES, LiveSession
from app.models.notification import Notification
from app.models.session import SESSION_IN_PROGRESS_STATUSES, Session as Deck
from app.models.user import User
from app.schemas.auth import (
    ConsentRequest,
    DeleteAccountRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)

router = APIRouter(tags=["auth"])


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id, full_name=user.full_name, email=user.email, role=user.role, language=user.language,
        age_group=user.age_group, communication_goal=user.communication_goal,
        skill_level=user.skill_level, challenges=user.challenges or [], created_at=user.created_at,
        study_level=user.study_level, field_of_study=user.field_of_study, feedback_style=user.feedback_style,
        cloud_consent_at=user.cloud_consent_at, keep_recordings=bool(user.keep_recordings),
    )


@router.post("/auth/register", status_code=201)
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    limiter.hit(f"register:{client_ip(request)}", 10, 600)
    email = body.email.lower()
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    db.add(User(
        full_name=body.full_name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        language=body.language,
        communication_goal=body.communication_goal or None,
    ))
    await db.commit()
    return {"message": "Registration successful. You can now sign in."}


# The long-lived refresh token lives in an httpOnly cookie, out of reach of page scripts (XSS),
# sent only to /api/auth. The short-lived access token (30 min) is returned in the body.
REFRESH_COOKIE = "sm_refresh"
COOKIE_PATH = "/api/auth"


def _set_refresh_cookie(response: Response, user) -> None:
    response.set_cookie(
        REFRESH_COOKIE, create_refresh_token(user.id), max_age=settings.refresh_token_expire_days * 86400,
        httponly=True, samesite="lax", secure=settings.cookie_secure, path=COOKIE_PATH,
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    # Per account (stops password guessing on one email) and per client
    limiter.hit(f"login:{email}", 10, 300)
    limiter.hit(f"login-ip:{client_ip(request)}", 30, 300)
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    _set_refresh_cookie(response, user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    request: Request, response: Response, body: RefreshRequest | None = None, db: AsyncSession = Depends(get_db),
):
    """New access token from the refresh cookie (rotated on every use). A refresh token in the body
    is still accepted, so browsers signed in before the cookie existed move over without a sign-in."""
    token = request.cookies.get(REFRESH_COOKIE) or (body.refresh_token if body else None)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in")
    user = await user_from_token(token, "refresh", db)
    _set_refresh_cookie(response, user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/auth/logout")
async def logout(response: Response):
    """Clears the refresh cookie; the client drops its access token."""
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH, httponly=True, samesite="lax", secure=settings.cookie_secure)
    return {"message": "Logged out"}


@router.get("/users/profile", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return _to_response(user)


@router.put("/users/profile", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value.strip() if isinstance(value, str) else value)
    await db.commit()
    await db.refresh(user)
    return _to_response(user)


# ── The user's data ─────────────────────────────────────────────────────────

@router.post("/users/me/consent", response_model=UserResponse)
async def set_cloud_consent(body: ConsentRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Agree to (or withdraw from) cloud processing: audio to Groq for speech-to-text, text to Gemini."""
    user.cloud_consent_at = datetime.now(timezone.utc) if body.accept else None
    await db.commit()
    await db.refresh(user)
    return _to_response(user)


def _row(obj, skip: tuple[str, ...] = ()) -> dict:
    """Every column of a row except storage paths and secrets."""
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs
            if c.key not in skip and not c.key.endswith("storage_path") and c.key != "password_hash"}


@router.get("/users/me/export")
async def export_my_data(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Everything stored about the user, as one JSON download (PDPA access request).
    Recordings and decks themselves are files; their names and results are included."""
    decks = (await db.execute(select(Deck).where(Deck.user_id == user.id))).scalars().all()
    data = {
        "exported_at": datetime.now(timezone.utc),
        "profile": _row(user),
        "practice_sessions": [_row(s) for s in (await db.execute(
            select(LiveSession).where(LiveSession.user_id == user.id).order_by(LiveSession.created_at))).scalars()],
        "decks": [_row(d) for d in decks],
        "notifications": [_row(n) for n in (await db.execute(select(Notification).where(Notification.user_id == user.id))).scalars()],
    }
    body = json.dumps(data, default=str, ensure_ascii=False, indent=1)
    return Response(body, media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="speechmate-my-data.json"'})


@router.delete("/users/me", status_code=204)
async def delete_my_account(body: DeleteAccountRequest, response: Response,
                            user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete the account and everything belonging to it, files included (PDPA erasure).
    The password is asked again so a stolen access token alone can't erase an account."""
    from app.routers.live import LIVE_STORAGE_PREFIX
    from app.services.storage import storage_service

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=403, detail="Wrong password")
    lives = (await db.execute(select(LiveSession).where(LiveSession.user_id == user.id))).scalars().all()
    decks = (await db.execute(select(Deck).where(Deck.user_id == user.id))).scalars().all()
    if any(s.status in LIVE_IN_PROGRESS_STATUSES for s in lives) or any(d.status in SESSION_IN_PROGRESS_STATUSES for d in decks):
        raise HTTPException(status_code=409, detail="Wait for running analyses to finish, then try again")
    folders = [f"{LIVE_STORAGE_PREFIX}/{s.id}" for s in lives] + [str(d.id) for d in decks]
    for deck in decks:
        await db.delete(deck)                       # its slides go with it
    for model in (Notification, LiveSession):
        await db.execute(delete(model).where(model.user_id == user.id))
    await db.delete(user)
    await db.commit()
    for folder in folders:
        storage_service.delete_session(folder)
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH, httponly=True, samesite="lax", secure=settings.cookie_secure)
