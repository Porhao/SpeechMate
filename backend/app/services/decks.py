"""What a deck offers the rest of the app: its title, its slides with their key points, and the
Q&A question plan built from its insights (cached in the insights)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session as Deck
from app.models.slide import Slide
from app.services import plans


def title(deck: Deck) -> str:
    return deck.original_filename.rsplit(".", 1)[0]


async def slides(db: AsyncSession, deck: Deck) -> list[dict]:
    """Each slide's title, text and key point (from the insights), in order."""
    insights = deck.insights or {}
    points = {p.get("slide_index"): p.get("key_point") for p in insights.get("slides") or []}
    titles = {p.get("slide_index"): p.get("title") for p in (insights.get("stats") or {}).get("per_slide") or []}
    rows = (await db.execute(select(Slide).where(Slide.session_id == deck.id).order_by(Slide.slide_index))).scalars()
    return [{"index": s.slide_index, "title": titles.get(s.slide_index) or "", "text": (s.slide_text or "")[:1500],
             "key_point": points.get(s.slide_index) or ""} for s in rows]


async def qa_plan(deck: Deck, learner: str) -> dict:
    """The audience's question plan, built once (normally by the deck pipeline right after the
    insights, so "Start Q&A" opens instantly) and reused for every rehearsal."""
    plan = (deck.insights or {}).get("qa_plan")
    if not plan:
        plan = await plans.build_qa_plan(title(deck), deck.insights, deck.requirement_prompt, learner)
        deck.insights = {**deck.insights, "qa_plan": plan}  # a new dict, so the JSON column is saved
    return plan
