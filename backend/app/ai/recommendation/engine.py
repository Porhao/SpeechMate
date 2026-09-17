"""
Recommendation Engine
Input: speech analysis + vision analysis + user goals + historical trends
Output: personalized exercises, weekly targets, practice session recommendations
"""
from dataclasses import dataclass, field


@dataclass
class Recommendation:
    title: str
    description: str
    practice_type: str          # Conversation / Presentation / Pronunciation / Interview
    daily_minutes: int
    priority: str               # High / Medium / Low
    metric_target: str          # e.g. "Fluency > 80%"


@dataclass
class RecommendationResult:
    recommendations: list[Recommendation] = field(default_factory=list)
    weekly_focus: str = ""
    daily_target_minutes: int = 15
    next_session_type: str = "Conversation"
    tips: list[str] = field(default_factory=list)
    progress_forecast: str = ""


def generate_recommendations(
    fluency_score: float,
    pronunciation_score: float,
    eye_contact_score: float,
    confidence_score: float,
    posture_score: float,
    stuttering_score: float,
    filler_count: int,
    user_goal: str = "",
    session_history_count: int = 0,
) -> RecommendationResult:
    recs: list[Recommendation] = []
    tips: list[str] = []

    # --- Fluency recommendations ---
    if fluency_score < 65:
        recs.append(Recommendation(
            title="Daily Fluency Drills",
            description="Practice reading aloud for 10 minutes daily, focusing on smooth, continuous speech without stopping to self-correct.",
            practice_type="Conversation",
            daily_minutes=10,
            priority="High",
            metric_target="Fluency > 75%",
        ))
        tips.append("Try the 'smooth speech' technique: speak at 80% of your natural pace and focus on flow over perfection.")

    # --- Stuttering recommendations ---
    if stuttering_score > 20:
        recs.append(Recommendation(
            title="Stuttering Reduction Practice",
            description="Use diaphragmatic breathing before speaking. Practice slow, deliberate speech with the AI conversation partner.",
            practice_type="Conversation",
            daily_minutes=15,
            priority="High",
            metric_target="Stuttering Score < 15%",
        ))
        tips.append("Before each session, take 3 deep breaths. Slow your speech — clarity beats speed.")

    # --- Pronunciation recommendations ---
    if pronunciation_score < 70:
        recs.append(Recommendation(
            title="Pronunciation Training",
            description="Practice targeted word drills for your most common mispronunciations using the Pronunciation Training mode.",
            practice_type="Pronunciation",
            daily_minutes=10,
            priority="High" if pronunciation_score < 55 else "Medium",
            metric_target="Pronunciation > 80%",
        ))

    # --- Filler word recommendations ---
    if filler_count > 10:
        recs.append(Recommendation(
            title="Filler Word Elimination",
            description="Record yourself answering questions. When you feel the urge to say 'um' or 'uh', pause silently instead.",
            practice_type="Presentation",
            daily_minutes=10,
            priority="Medium",
            metric_target="< 5 fillers per minute",
        ))
        tips.append("Replace filler words with a confident pause — silence sounds more authoritative than 'um'.")

    # --- Eye contact recommendations ---
    if eye_contact_score < 70:
        recs.append(Recommendation(
            title="Eye Contact Practice",
            description="Practice presentation mode for 15 minutes daily. Look directly at the camera as if making eye contact with your audience.",
            practice_type="Presentation",
            daily_minutes=15,
            priority="High" if eye_contact_score < 55 else "Medium",
            metric_target="Eye Contact > 75%",
        ))

    # --- Confidence recommendations ---
    if confidence_score < 65:
        recs.append(Recommendation(
            title="Confidence Building Sessions",
            description="Start with 2-minute storytelling sessions and gradually increase duration. Focus on posture and voice projection.",
            practice_type="Conversation",
            daily_minutes=10,
            priority="Medium",
            metric_target="Confidence > 70%",
        ))
        tips.append("Power posing for 2 minutes before speaking can measurably improve confidence.")

    # --- Posture recommendations ---
    if posture_score < 75:
        recs.append(Recommendation(
            title="Presentation Posture Training",
            description="Practice the 'triangle stance': feet shoulder-width apart, shoulders level, chin parallel to the floor.",
            practice_type="Presentation",
            daily_minutes=5,
            priority="Low",
            metric_target="Posture > 80%",
        ))

    # Weekly focus: highest-priority issue
    if recs:
        top = sorted(recs, key=lambda r: {"High": 0, "Medium": 1, "Low": 2}[r.priority])
        weekly_focus = top[0].title
        next_session = top[0].practice_type
        total_mins = min(sum(r.daily_minutes for r in recs[:3]), 30)
    else:
        weekly_focus = "Maintain your excellent communication skills"
        next_session = "Conversation"
        total_mins = 10
        tips.append("You're performing excellently! Try a mock interview to challenge yourself further.")

    # Progress forecast based on session history
    if session_history_count < 5:
        forecast = "With consistent daily practice, expect 10–15% improvement in your key metrics within 2 weeks."
    elif session_history_count < 20:
        forecast = "You're building strong habits. Continue at this pace for steady 5–8% weekly improvement."
    else:
        forecast = "Advanced practitioner level. Focus on fine-tuning specific weaknesses for peak performance."

    return RecommendationResult(
        recommendations=recs,
        weekly_focus=weekly_focus,
        daily_target_minutes=total_mins,
        next_session_type=next_session,
        tips=tips,
        progress_forecast=forecast,
    )
