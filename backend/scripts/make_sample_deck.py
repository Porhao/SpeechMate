"""Generate a small 3-slide .pptx for testing the pipeline.

    python scripts/make_sample_deck.py [output_path]   (default: samples/sample_deck.pptx)
"""

import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

SLIDES = [
    ("Five Strategies for Effective Time Management", [
        "Why time management matters for students and professionals",
        "Simple habits you can start today",
    ]),
    ("Plan and Prioritize", [
        "Write tomorrow's top three tasks the night before",
        "Use the Eisenhower matrix: urgent vs. important",
        "Block focused time on your calendar",
    ]),
    ("Protect Your Focus", [
        "Silence notifications during deep work",
        "Work in 25-minute sprints with short breaks",
        "Review your week every Friday",
    ]),
]


def build(path: Path) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)  # 16:9

    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = SLIDES[0][0]
    title_slide.placeholders[1].text = "\n".join(SLIDES[0][1])

    for title, bullets in SLIDES[1:]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title
        body = slide.placeholders[1].text_frame
        body.text = bullets[0]
        for bullet in bullets[1:]:
            body.add_paragraph().text = bullet
        for para in body.paragraphs:
            for run in para.runs:
                run.font.size = Pt(28)

    path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(path)
    return path


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("samples/sample_deck.pptx")
    print(f"Wrote {build(out)}")
