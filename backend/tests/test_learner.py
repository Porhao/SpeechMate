"""The learner brief that adapts the AI's questions and feedback to the profile (services/learner.py)."""

from types import SimpleNamespace

from app.services.learner import learner_brief, with_brief


def _user(**kw):
    base = dict(study_level=None, field_of_study=None, skill_level="Beginner", communication_goal=None,
                challenges=None, feedback_style=None)
    return SimpleNamespace(**{**base, **kw})


def test_brief_carries_level_field_style_and_adapts_difficulty():
    b = learner_brief(_user(study_level="Undergraduate", field_of_study=" Computer Science ", skill_level="Advanced",
                            communication_goal="Job Interviews", challenges=["Filler Words"], feedback_style="direct"))
    assert "undergraduate student, in Computer Science." in b
    assert "probing" in b and "Job Interviews" in b and "Filler Words" in b and "what to fix first" in b
    beginner = learner_brief(_user(study_level="Secondary"))
    assert "SPM" in beginner and "one idea at a time" in beginner


def test_no_profile_leaves_prompts_unchanged():
    assert learner_brief(None) == "" and with_brief("SYSTEM", "") == "SYSTEM"
    assert with_brief("SYSTEM", learner_brief(_user(skill_level="Intermediate"))).startswith("SYSTEM\n\nAbout the learner")
