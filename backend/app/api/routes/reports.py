from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.base import get_db
from app.models.user import User
from app.models.session import Report
from app.middleware.auth import get_current_user
import uuid

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/generate", status_code=201)
async def generate_report(
    report_type: str = "pdf",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # TODO: Generate actual PDF/Excel report
    report = Report(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        report_url=f"/storage/reports/{current_user.id}/report_{uuid.uuid4()}.pdf",
        report_type=report_type,
    )
    db.add(report)
    await db.commit()
    return {"report_id": report.id, "report_url": report.report_url}


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    return report
