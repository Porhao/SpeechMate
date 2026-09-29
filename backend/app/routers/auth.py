"""Account endpoints: register, login, token refresh, and the user's own profile."""

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.database import get_db
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
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
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


@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email.lower()))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id))


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    user = await user_from_token(body.refresh_token, "refresh", db)
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=create_refresh_token(user.id))


@router.post("/auth/logout")
async def logout():
    """Tokens are stateless; the client discards them. Kept so clients have one logout call."""
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
