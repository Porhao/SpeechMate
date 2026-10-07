"""Account endpoints: register, login, token refresh, and the user's own profile."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
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
from app.models.user import User
from app.schemas.auth import (
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
