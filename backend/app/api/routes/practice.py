from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.base import get_db
from app.models.user import User
from app.models.session import PracticeSession
from app.schemas.session import StartSessionRequest, EndSessionRequest, SessionResponse
from app.middleware.auth import get_current_user
import uuid

router = APIRouter(prefix="/practice", tags=["Practice"])


@router.post("/start", response_model=SessionResponse, status_code=201)
async def start_session(
    body: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = PracticeSession(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        session_type=body.session_type,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/end", response_model=SessionResponse)
async def end_session(
    body: EndSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PracticeSession).where(
            PracticeSession.id == body.session_id,
            PracticeSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Session not found")

    session.duration = body.duration
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/history", response_model=list[SessionResponse])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PracticeSession)
        .where(PracticeSession.user_id == current_user.id)
        .order_by(PracticeSession.created_at.desc())
    )
    return result.scalars().all()
