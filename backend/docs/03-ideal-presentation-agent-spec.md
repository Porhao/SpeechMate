# Ideal Presentation Agent — Detailed Spec (Phase 1 / MVP)

## Goal
Input: `.pptx` file + voice sample (short audio clip) + optional free-text requirement (audience type, purpose).
Output: an MP4 video of the deck narrated in the user's cloned voice, plus the per-slide script text.

This is the entire scope of Phase 1. Do not start Phase 2 (Coach Agent) until this produces a working video end-to-end for a real deck.

## Stage 1: Slide Processing (.pptx → PNGs)
- Input: uploaded `.pptx` file.
- Convert each slide to a high-resolution PNG (target ~1920x1080 or the deck's native aspect ratio).
- **Tooling options:**
  - `LibreOffice` headless (`soffice --headless --convert-to png`) — most reliable for arbitrary pptx layouts/fonts, requires LibreOffice installed in the container.
  - `python-pptx` + manual rendering — python-pptx can *read* slide content/text but does not render visual PNGs faithfully; use it only if you need raw text extraction, not for the image conversion itself.
  - Recommended: LibreOffice headless conversion for fidelity (matches what the paper implies with `split_pptx_to_pngs`), since the VLM step needs an accurate visual render, not just extracted text.
- Output: `slides/slide_1.png ... slide_N.png`, plus slide count stored on the session record.
- Error handling: if a slide fails to render (corrupt embedded media, unusual layout), log it and either retry with a lower-fidelity fallback render or skip with a placeholder — never let one bad slide abort the whole deck.

## Stage 2: Script Generation (VLM)
- For each slide PNG, call the VLM with:
  - The slide image
  - The user's requirement/context prompt (audience, purpose) — pass this once, reused for every slide call for consistency
  - A system instruction that fixes: target length (60–100 words per slide, matching the paper), tone (coherent, natural spoken English, not a bullet-point read-out), and a note to consider transition continuity with neighboring slides
- **Continuity handling:** pass the *previous* slide's generated script (or a short summary) as context when generating slide N's script, so transitions feel connected rather than each slide narrated in isolation. Don't generate all scripts fully independently in parallel if transition quality matters — either do this sequentially, or do a first parallel pass then a light second pass to smooth transitions.
- Output: `scripts/slide_i.json` = `{ "slide_index": i, "text": "...", "word_count": N, "model": "...", "generated_at": "..." }`
- Validation: enforce the word-count band server-side (re-prompt once if wildly outside 60-100 words) so downstream TTS timing stays sane.

## Stage 3: Speech Synthesis (voice cloning)
- Input: each slide's script text + the user's voice sample.
- Voice cloning call produces one audio clip per slide (don't try to synthesize the whole deck as one giant TTS call — per-slide keeps retry/caching granular and matches Stage 4's per-slide video assembly).
- **Required fallback logic:**
  1. Attempt voice cloning with the user's sample.
  2. If cloning fails (bad audio quality, provider error, no sample provided) → fall back to a standard non-cloned TTS voice, log a flag on the session (`voice_cloning_used: false`) so the UI can inform the user.
  3. Never let a TTS failure block the whole pipeline — retry 2-3x with backoff, then fall back, then only fail the specific slide as a last resort (with the rest of the deck still completing).
- Audio format handling: normalize whatever the TTS API returns (often WAV or MP3) to one consistent format (WAV) before Stage 4.
- Output: `audio/slide_i.wav`

## Stage 4: Video Assembly
- For each slide: combine `slide_i.png` (as a static image) + `audio/slide_i.wav` into a per-slide video segment, where segment duration = audio duration.
- Concatenate all per-slide segments into one MP4 via FFmpeg.
- Consider a simple crossfade or hard cut between slides (hard cut is fine for v1 — don't over-engineer transitions).
- Output: `ideal_video.mp4`, plus per-slide segment files kept around (useful later if the Coach Agent needs to reference a specific slide's ideal audio independently, which it does — see `04-coach-agent-spec.md`).

## Status/progress tracking
Update the session's `status` field at each stage boundary so the frontend can show real progress (this is the "transparent pipeline" UX from the paper — see `06-frontend-ui-spec.md`):
```
queued → processing_slides → generating_scripts → synthesizing_audio → assembling_video → complete
                                                                                          → failed (with error detail)
```
Store per-slide status too if you want finer-grained progress (`3/8 slides scripted`), which is a nice-to-have, not required for v1.

## API surface for this agent (see `05-data-models-api.md` for full contract)
- `POST /sessions` — create session, upload pptx + voice sample + requirement text, kicks off the pipeline
- `GET /sessions/{id}` — poll status + progress
- `GET /sessions/{id}/video` — fetch the final video once complete
- `GET /sessions/{id}/scripts` — fetch per-slide scripts (needed by frontend for the script-view panel, and by the Coach Agent later)

## What to stub first when building
1. Hardcode a single test `.pptx` and get Stage 1 (PNG conversion) working standalone — verify visually the PNGs look right before touching AI calls.
2. Get Stage 2 working on that one deck with a cheap/fast VLM call, print scripts to console — verify quality before wiring up TTS (expensive to iterate on prompt quality once audio is in the loop).
3. Get Stage 3 working with the TTS fallback path *first* (simpler, no cloning), then add cloning on top.
4. Get Stage 4 working with those existing audio+PNG files.
5. Only then wire the 4 stages into the async job pipeline with status tracking.
