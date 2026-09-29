# Tech Stack

Chosen to fit an existing React/Next.js/TypeScript + FastAPI/Python + Postgres/Supabase stack. The original paper used Qwen2.5-VL, CosyVoice2, Gemini 2.5 Pro, and Qwen2.5 — those are good reference points but not all are equally easy to stand up solo. Alternatives are noted where it meaningfully changes cost/complexity.

## Backend
- **FastAPI (Python)** — API layer, matches existing skills.
- **Background jobs:** start with a simple `asyncio`-based in-process worker; migrate to **Celery + Redis** or **arq** once concurrent sessions matter.
- **Postgres (Supabase)** — session/deck/slide/script/feedback records. Already in your stack — use it rather than adding Mongo for this; the data here is relational (session → slides → scripts → audio), not document-shaped.
- **Object storage:** Supabase Storage (S3-compatible, same ecosystem as your DB) for pptx uploads, PNGs, audio, video.

## AI model choices

### 1. Slide → script (Visual Language Model)
Needs to read a slide image and produce a narration script.
- **Recommended:** GPT-4o or GPT-4o-mini (vision) via OpenAI API, or Claude with vision via Anthropic API — both handle slide-image-to-text well and are simple to call from FastAPI with no self-hosting.
- **Paper's choice:** Qwen2.5-VL — viable if you want to self-host (Ollama can run smaller Qwen2.5-VL variants) but adds infra complexity; only worth it if cost or data-privacy is a hard constraint.
- **Decision rule:** start with a hosted API (fastest to a working demo), swap to self-hosted only if you hit cost/privacy limits.

### 2. Script → speech (voice cloning / TTS)
This is the highest-risk, highest-cost component.
- **Recommended for v1:** **ElevenLabs** (voice cloning API, easiest integration, has a free/low tier) — get the pipeline working end-to-end first.
- **Open-source alternative:** CosyVoice2 (paper's choice) or **XTTS-v2** (Coqui) — both support voice cloning from a short sample and can run locally/on a GPU box, no per-call API cost, but require you to host inference (GPU needed for reasonable speed).
- **Fallback path (required, not optional):** standard non-cloned TTS (e.g., a fixed neural voice from the same provider, or `pyttsx3`/OS TTS as an absolute last resort) — if voice cloning fails or the user skips the voice sample, the pipeline must still produce a video. Build this fallback in from day one, don't bolt it on later.

### 3. Video assembly
- **FFmpeg** — no alternative needed here, this matches the paper and is the standard tool. Call it via `subprocess` or the `ffmpeg-python` wrapper. Sync each slide PNG with its corresponding audio clip's duration, concatenate segments.

### 4. Coach Agent (multimodal comparison + feedback)
Needs to reason over: slide image + ideal script text + ideal audio + user's practice audio, and produce structured feedback.
- **Recommended:** Gemini 2.5 Pro or Gemini 2.5 Flash (native audio input support, and cheaper than GPT-4o for audio-heavy multimodal calls) — matches the paper's choice and has the best native audio-understanding support among mainstream APIs as of writing.
- **Alternative:** transcribe both audios with Whisper first, then feed transcripts + timing/pace metrics (computed separately) + slide text into a text-only LLM (GPT-4o, Claude) for feedback generation. This is more engineering but decouples "speech analysis" from "feedback writing," which is easier to debug and cheaper per call.
- **Decision rule:** if budget/simplicity matters more than exact fidelity to the paper, use the transcribe-then-reason approach — it's more inspectable and controllable for OIS-formatted output.

### 5. Coach Agent chat follow-up
- Any text LLM you're already using (GPT-4o-mini, Claude, Qwen2.5) — this is a standard RAG-lite chat over session history (ideal script + feedback + prior chat turns as context), nothing exotic needed.

## Frontend
- **Next.js + TypeScript + React** — matches existing stack.
- **Audio/video recording:** browser `MediaRecorder` API (no library needed for basic record/upload).
- **Video playback:** native `<video>` element is sufficient; no need for a heavy player library for v1.
- **Polling/live progress:** simple polling (`setInterval` + `GET /sessions/{id}`) is fine for v1; upgrade to SSE/WebSocket only if polling feels janky.
- **State/data fetching:** whatever you already reach for (React Query/TanStack Query recommended for the polling + mutation pattern here).

## Infra / deployment
- **Docker** for the backend + worker (already in your stack).
- Local dev: everything runs via `docker-compose` (API, worker, Postgres if not using hosted Supabase, Redis if using Celery).
- Deployment target: pick whatever's cheapest to start — a single VM (or Fly.io/Railway) running API + worker containers, Supabase hosted for DB/storage/auth. Don't over-provision (no k8s) for a solo project.

## What NOT to add yet
- No Kubernetes, no multi-region, no message broker beyond Redis (if even needed) — this is a single-user-at-a-time demo app until proven otherwise.
- No vector DB / RAG pipeline needed initially — session context for the Coach Agent chat is small enough (one deck's scripts + one feedback report) to pass directly in the prompt context window rather than retrieving via embeddings.
