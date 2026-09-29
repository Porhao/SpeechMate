"""Script generation (Ideal Agent Stage 2): slide image → spoken narration via a VLM.

Slides are scripted sequentially so each call can see the previous slide's
narration and write a connected transition. Without an API key (or if the VLM
keeps failing) a template script is built from the slide's extracted text so
the pipeline still produces a video.
"""

import base64
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.services.ai import count_words, get_llm_client, with_retries

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert presentation speaker writing the spoken narration for ONE slide of a presentation.

Rules:
- Write {min_words}-{max_words} words of natural, coherent spoken English for this slide only.
- Explain the slide's core message the way a confident, engaging presenter would. Do not read bullet points verbatim and do not describe the layout ("this slide shows...").
- If previous narration is given, open with a smooth transition from it without repeating it. The first slide should open the talk; the last slide should close it.
- Follow the presenter's requirements (audience, purpose, tone) if given.
- Output only the narration text: no headings, lists, quotes, stage directions, emojis or markdown."""


@dataclass
class ScriptResult:
    text: str
    word_count: int
    source: str  # "vlm" | "fallback"
    model: str | None = None


def _clean(text: str) -> str:
    text = re.sub(r"[*_#`>]", "", text).strip().strip('"').strip()
    return re.sub(r"\s+", " ", text)


def fallback_script(slide_index: int, slide_count: int, slide_text: str) -> str:
    """Deterministic narration built from the slide's own text (no AI needed)."""
    lines = [ln.strip(" •-–\t") for ln in slide_text.splitlines() if ln.strip(" •-–\t")]
    if not lines:
        return (
            f"Let's move on to slide {slide_index}. Take a moment to look at the visual "
            "here, because it supports the main point we are building towards."
        )
    title, points = lines[0], lines[1:]
    title = title.rstrip(".:")
    if slide_index == 1:
        opening = f"Hello everyone, and thank you for being here. Today's topic is {title}."
    else:
        opening = f"Next, let's talk about {title}."
    body = ""
    if points:
        body = " " + " ".join(p if p.endswith((".", "!", "?")) else f"{p}." for p in points[:6])
    closing = " Thank you for listening." if slide_index == slide_count and slide_count > 1 else ""
    return f"{opening}{body}{closing}"


class ScriptGenerator:
    async def generate(
        self,
        *,
        image_path: Path,
        slide_index: int,
        slide_count: int,
        slide_text: str,
        requirement_prompt: str | None,
        previous_script: str | None,
    ) -> ScriptResult:
        client = get_llm_client()
        if client is not None:
            try:
                return await self._generate_with_vlm(
                    client,
                    image_path=image_path,
                    slide_index=slide_index,
                    slide_count=slide_count,
                    slide_text=slide_text,
                    requirement_prompt=requirement_prompt,
                    previous_script=previous_script,
                )
            except Exception as e:  # noqa: BLE001 — fall back rather than fail the deck
                logger.error("VLM script generation failed for slide %d: %s", slide_index, e)

        text = fallback_script(slide_index, slide_count, slide_text)
        return ScriptResult(text=text, word_count=count_words(text), source="fallback")

    async def _generate_with_vlm(
        self,
        client,
        *,
        image_path: Path,
        slide_index: int,
        slide_count: int,
        slide_text: str,
        requirement_prompt: str | None,
        previous_script: str | None,
    ) -> ScriptResult:
        min_w, max_w = settings.script_min_words, settings.script_max_words
        image_b64 = base64.b64encode(image_path.read_bytes()).decode()

        context = [f"This is slide {slide_index} of {slide_count}."]
        if requirement_prompt:
            context.append(f"Presenter's requirements: {requirement_prompt}")
        if slide_text.strip():
            context.append(f"Text extracted from the slide (may be incomplete):\n{slide_text}")
        if previous_script:
            context.append(f"Narration of the previous slide:\n{previous_script}")
        else:
            context.append("This is the opening of the talk.")

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT.format(min_words=min_w, max_words=max_w)},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "\n\n".join(context)},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": "high"},
                    },
                ],
            },
        ]

        async def call() -> str:
            resp = await client.chat.completions.create(
                model=settings.vlm_model, messages=messages, temperature=0.6
            )
            content = resp.choices[0].message.content or ""
            if not content.strip():
                raise ValueError("VLM returned an empty script")
            return _clean(content)

        text = await with_retries(call, label=f"VLM slide {slide_index}")
        words = count_words(text)

        # Re-prompt once if the length is way outside the band (keeps TTS timing sane)
        if words < min_w - 15 or words > max_w + 30:
            logger.info("Slide %d script has %d words, re-prompting once", slide_index, words)
            messages += [
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": f"That draft has {words} words. Rewrite it to {min_w}-{max_w} words, "
                    "keeping the same message and transition. Output only the narration.",
                },
            ]
            try:
                text = await with_retries(call, attempts=2, label=f"VLM slide {slide_index} rewrite")
                words = count_words(text)
            except Exception as e:  # noqa: BLE001 — keep the first draft
                logger.warning("Rewrite failed for slide %d, keeping first draft: %s", slide_index, e)

        return ScriptResult(text=text, word_count=words, source="vlm", model=settings.vlm_model)


script_generator = ScriptGenerator()
