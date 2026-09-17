from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.base import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UpdateProfileRequest
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name:
        current_user.full_name = body.full_name
    if body.language:
        current_user.language = body.language
    await db.commit()
    await db.refresh(current_user)
    return current_user
