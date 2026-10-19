# Implementation Roadmap

Build order across all the specs, sequenced so there's always something runnable/demoable at each checkpoint. Do not jump ahead to a later milestone before the current one's "done" bar is met.

## Milestone 0 — Repo & infra skeleton
- Monorepo or two-repo split (backend `api/`, frontend `web/`) — either works, pick based on preference.
- FastAPI app boots, Postgres connection works (local Postgres or Supabase dev project), Docker Compose brings up API + DB.
- Next.js app boots, hits a health-check endpoint on the API.
- **Done when:** `docker-compose up` gives you a working empty app, frontend can ping backend.

## Milestone 1 — Slide processing standalone (no AI yet)
- `POST /sessions` accepts a `.pptx`, stores it, converts to PNGs via LibreOffice headless, stores PNGs.
- `sessions` and `slides` tables exist and get populated.
- **Done when:** you can upload a real deck and see correctly-rendered PNGs land in storage, one per slide, in order.

## Milestone 2 — Script generation
- Wire the VLM call per slide PNG → populate `slides.script_text`.
- Enforce word-count band, basic prompt including requirement_prompt + prior-slide continuity context.
- **Done when:** a real deck produces sensible, on-topic scripts for every slide, printed/visible via `GET /sessions/{id}/scripts`.

## Milestone 3 — Voice synthesis + fallback
- Wire TTS fallback path first (no cloning) — confirm `audio/slide_i.wav` files are produced from script text.
- Add voice cloning on top, with the fallback triggering correctly on simulated failure (e.g., temporarily point at a bad API key to confirm the fallback kicks in).
- **Done when:** every slide has a corresponding audio file, and you've manually verified the fallback path actually works, not just exists in code.

## Milestone 4 — Video assembly + status pipeline
- FFmpeg stitches PNG+audio pairs into per-slide segments, concatenates into `ideal_video.mp4`.
- Wire the full 4-stage async job with status updates at each boundary.
- **Done when:** `POST /sessions` → polling `GET /sessions/{id}` → eventually `complete` → `GET /sessions/{id}/video` plays a real narrated video of a real deck, end to end, with zero manual steps.

**This is the Phase 1 / MVP finish line.** Don't start Phase 2 work before this milestone is solid and demoable.

## Milestone 5 — Frontend Stage 1 & 2 (upload + progress)
- Build the upload form and progress UI per `06-frontend-ui-spec.md`, wired to the real Milestone 4 backend.
- **Done when:** a user can go from the web UI, upload a deck, watch real progress, and land on a playable video — no API calls made manually/via curl.

## Milestone 6 — Frontend Stage 3 shell (video + script panel)
- Video player + script panel wired to real data.
- **Done when:** the practice environment screen shows the real video and real per-slide scripts for a completed session.

## Milestone 7 — Coach Agent: deterministic metrics + practice upload
- `POST /sessions/{id}/practice` accepts audio, transcribes via Whisper, computes WPM/pause/filler metrics deterministically (pure code, no LLM).
- **Done when:** submitting a real recording returns real, sane metrics via `GET /sessions/{id}/practice/{practice_id}` (LLM feedback not wired yet — metrics only).

## Milestone 8 — Coach Agent: OIS feedback generation
- Wire the LLM call producing structured `{encouragement, observations}` JSON from transcript + metrics + ideal script.
- Validate/enforce the JSON shape and word limits.
- **Done when:** real practice recordings produce coherent, specific (not generic) OIS feedback, rendered correctly by the Coach panel UI.

## Milestone 9 — Chat follow-up
- Wire `POST .../chat` scoped to the practice session's context.
- **Done when:** a user can ask a follow-up question about their feedback and get a contextually relevant answer, with history persisting across page reloads.

**This is the Phase 2 finish line** — the full dual-agent loop (generate exemplar → practice → get feedback → chat) works end to end.

## Milestone 10+ (Phase 3, stretch, in any order once Phase 2 is solid)
- Audience Agent second feedback lens
- Multi-session history / progress-over-time view per user
- Per-slide (vs. whole-deck) practice recording granularity
- Auth/multi-user support if not already needed by this point
- UI polish pass

## General building rules throughout
- Get each stage working with hardcoded/fake inputs before wiring the real upstream stage — this is called out per-spec-file but applies globally.
- Keep the fallback paths (TTS fallback, JSON re-prompt on malformed feedback) in from the start of the milestone that introduces the failure-prone call, not bolted on afterward.
- After each milestone, do one real end-to-end manual test with an actual `.pptx` file you didn't use during development — synthetic/toy test decks hide real-world slide-layout and content edge cases.
