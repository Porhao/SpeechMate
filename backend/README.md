# SpeechMate Backend

The API behind SpeechMate, an AI speaking coach for Malaysian speakers. It serves the app's three functions:
- **Daily conversation** with an AI partner;
- **Mock interview** (questions curated from the role, background and resume);
- **Presentation practice**: deck insights, a slide-by-slide check of your talk, and a Q&A drawn from the deck.

Every AI function and metric is listed in [`../docs/AI_MATRIX.md`](../docs/AI_MATRIX.md). The presentation coaching follows the ideas of
[PresentCoach (Chen et al., 2025, arXiv:2511.15253)](docs/2511.15253v2.pdf): a Deck Agent that understands the deck first, and a Coach Agent that judges what you said against it.

**Decks.** You upload a `.pptx` or `.pdf` (and optionally a note about your audience). A background job renders the slides, extracts their text, writes the deck insights (summary, structure, key point per slide, suggestions, likely questions) and caches a Q&A plan. You then present the deck yourself in a live "talk" session.

**Live sessions** (camera + mic with the AI partner):
- **Conversation**: a topic.
- **Interview**: a question plan curated from the setup and resume (`/api/interview/*`).
- **Presentation**: a talk over your slides (each slide's time and words are checked against it), or a Q&A from the deck's plan.

In Interview and Q&A sessions the server enforces the plan: one question at a time, word for word, with at most one follow-up for a short answer. After a session the recording is analysed:

- **speech**: Whisper large-v3 on Groq (auto language, verbatim Manglish prompt, word timestamps, silence-hallucination filter, a translation guard), fluency, filler words in context (English + Bahasa Melayu), stuttering, phone-level pronunciation (wav2vec2 phoneme recogniser + forced alignment, Malaysian English features accepted as regional), pitch and loudness (librosa), vocabulary and hedging, English/Malay ratio and Manglish particles;
- **vision**: eye contact (MediaPipe iris), posture, gestures, head steadiness (MediaPipe Pose), facial expression (ViT);
- **cross-modal**: Gaze Tunneling (looking away vs. disfluency timing, with a permutation test), confidence;
- **from the browser**: response time, slide times;
- **scoring**: an overall score, **four pillars** (voice, language, body, confidence) and three evidence-based drills;
- **content**: per-answer feedback against the plan (fact-checked stronger answers), per-slide talk feedback, or language tips.

**Accounts and privacy**: JWT access token + httpOnly refresh cookie, a coaching profile, PDPA consent before any cloud processing (`403 cloud_consent_required`), recordings deleted after analysis unless the user keeps them, data export and account deletion.

FastAPI with async SQLAlchemy and Postgres; jobs run in-process as asyncio tasks. Every AI stage has an offline fallback, so everything runs with **no API keys at all**, and the local models are optional too (see [Local models](#local-models-for-live-analysis)).

---

## Quick start (Docker, recommended)

Docker bundles everything the pipeline needs: LibreOffice, poppler, ffmpeg, espeak-ng, fonts and (by default) the local ML models.

```bash
cp .env.example .env          # set SECRET_KEY; add LLM_* (Gemini) and OPENAI_* (Groq) for the cloud setup
docker compose up --build     # API on http://localhost:8000, Postgres on :5432
INSTALL_ML=false docker compose up --build    # slim image without the ~2 GB of local models
```

To run the whole app (backend + frontend + database), use `./start.sh` in the repository root instead. Migrations run automatically on startup. Then:

- **Swagger UI:** http://localhost:8000/docs, where you can try every endpoint
- **Health and capabilities:** http://localhost:8000/health shows which binaries, models and providers are available, and therefore which fallbacks apply

> **WSL 2 note:** if `docker` says *"could not be found in this WSL 2 distro"*, open Docker Desktop → Settings → Resources → **WSL Integration**, enable your distro, then restart the terminal.

---

## Running locally without Docker

You need Python 3.11+, Postgres, and these system packages:

```bash
# Debian/Ubuntu
sudo apt install libreoffice-impress poppler-utils ffmpeg espeak-ng \
                 fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea
# macOS
brew install --cask libreoffice && brew install poppler ffmpeg espeak-ng
```

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r requirements-ml.txt          # optional: local models for live-session analysis
cp .env.example .env                        # set DATABASE_URL to your Postgres
docker compose up -d db                     # (or use your own Postgres)
alembic upgrade head
uvicorn app.main:app --reload
```

If a binary isn't on your `PATH`, point to it with `FFMPEG_BIN`, `LIBREOFFICE_BIN` or `ESPEAK_BIN`. On macOS LibreOffice is usually at `/Applications/LibreOffice.app/Contents/MacOS/soffice`.

---

## API keys and fallbacks

All keys are optional. "LLM" means whichever you've configured: an OpenAI-compatible endpoint via `LLM_BASE_URL` (Gemini: `https://generativelanguage.googleapis.com/v1beta/openai/`, `LLM_API_KEY` from aistudio.google.com, `LLM_MODEL=gemini-3.5-flash-lite`), or OpenAI via `OPENAI_API_KEY`. Speech recognition uses `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `TRANSCRIPTION_MODEL` (Groq: `https://api.groq.com/openai/v1`, `whisper-large-v3`).

| Stage | With keys | Without keys (fallback) |
|---|---|---|
| Deck insights | LLM, JSON-validated and re-prompted once | A text-based outline from the slides |
| Interview / Q&A question plan | LLM, JSON-validated and re-prompted; labels and placeholders stripped | Behavioural / technical question bank; for a deck, its likely questions and key points |
| AI partner (`/api/chat/message`) | the LLM writes the replies | Conversation: `503` (the frontend uses scripted prompts). Interview / Q&A: still follows its plan, with fixed reactions |
| Partner's voice (`/api/tts/speak`) | Kokoro in the browser first; then a Kokoro server (`TTS_BASE_URL`) or OpenAI TTS | `503`, and the browser's own voice is used |
| Live turn transcription (`/api/stt`) | Whisper API, retried on provider errors (`502` makes the browser retry) | `503`, and the user types |
| Session speech recognition | Whisper API with word timestamps | Word-level metrics skipped; pauses and stutter blocks are still measured from the audio |
| Answer feedback / language tips / talk feedback | LLM, JSON-validated; stronger answers fact-checked against what was said | Rule-based (STAR cue words, numbers, length, keyword coverage) |

Every fallback is recorded in the `warnings` field of the deck or live session. Nothing fails silently, and no metric is ever made up: one that couldn't be measured is `null`.

### Local models for live analysis

`requirements-ml.txt` adds CPU-only PyTorch, transformers, librosa, MediaPipe and OpenCV (about 2 GB installed). The model weights (about 2.5 GB more) download on first use and are cached in the `model_cache` volume. Each stage checks for its own packages:

| Metric | Needs | Without it |
|---|---|---|
| Pronunciation | `transformers`, `torch`, espeak-ng | `null` |
| Stutter prolongations, pitch | `librosa` | only prolongations the transcript spells out ("sooo") |
| Eye contact, posture, gestures, Gaze Tunneling | `cv2`, `mediapipe` | `null` |
| Facial expression | `mediapipe`, `transformers`, `torch` | `null` |

`GET /health` lists which are installed, and `USE_LOCAL_ML=false` turns them all off. The overall and confidence scores are re-weighted over whichever components were measured, and `communication_score.scored_on` says which ones those were.

---

## How it works

```
POST /api/sessions (.pptx/.pdf, requirement?)
  └─ deck preparation (background job; poll GET /api/sessions/{id})
       processing_slides   .pptx → PDF (LibreOffice) → PNGs (pdftoppm) + slide text
       analyzing_content   deck insights (LLM or rules) → cached Q&A plan
       complete | failed

POST /api/live → POST /api/live/{id}/end → POST /api/live/{id}/recording → POST /api/live/{id}/analyze
  └─ live analysis (background job; poll GET /api/live/{id})
       analyzing  16 kHz WAV (ffmpeg) → Whisper (FLAC upload, word timings, silence filter, translation guard)
                  → language / Manglish → fluency → fillers → stuttering → pronunciation → prosody
                  → 2 fps gaze stream + sampled frames → eye contact / posture / gestures / expression
                  → Gaze Tunneling → confidence → score → pillars → content feedback → drills
                  → notification; the recording is deleted unless the user keeps recordings
       complete | failed
```

- **Why metrics are computed in code:** they're deterministic and unit-tested, and the LLM only turns them into prose, so every piece of feedback traces back to a number.
- **Restarts:** jobs that were running when the server stopped are marked `failed` on the next startup. Re-run them with `POST /api/sessions/{id}/retry` or `POST /api/live/{id}/analyze`.
- **Concurrency:** at most `MAX_CONCURRENT_JOBS` pipelines run at once (default 2).

### Storage layout (`STORAGE_BASE_PATH`)

```
{deck_id}/
  original.pptx|pdf   slides.pdf   slides/slide_N.png
live/{live_session_id}/
  recording.*  audio_16k.wav        (deleted after analysis unless "keep recordings" is on)
```

---

## API reference

Interactive docs are at `/docs`. All routes are under `/api` except `/health`. 🔒 = send `Authorization: Bearer <access_token>`; ☁️ = also needs cloud-processing consent.

**Accounts**

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/auth/register` | JSON `{full_name, email, password (≥8), language?, communication_goal?}` → `201` |
| `POST` | `/api/auth/login` | JSON `{email, password}` → `{access_token}` + the httpOnly refresh cookie |
| `POST` | `/api/auth/refresh` | the cookie → a new access token (the cookie rotates) |
| `POST` | `/api/auth/logout` | clears the cookie |
| `GET` / `PUT` | `/api/users/profile` 🔒 | name, language, age group, communication goal, skill level, challenges |
| `POST` | `/api/users/me/consent` 🔒 | `{accept}` (false withdraws it); whether recordings are kept is `keep_recordings` on `PUT /api/users/profile` |
| `GET` | `/api/users/me/export` 🔒 | everything stored about you, as JSON |
| `DELETE` | `/api/users/me` 🔒 | `{password}`: the account, its data and its files |

**Decks** 🔒 (your own only; anyone else's is `404`)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/sessions` ☁️ | multipart: `pptx` (.pptx or .pdf), `requirement_prompt?` → `201 {session_id, status}` |
| `GET` | `/api/sessions` | your decks |
| `GET` | `/api/sessions/{id}` | `status`, `slide_count`, `slides_rendered`, `insights`, `warnings`, `error_detail` |
| `GET` | `/api/sessions/{id}/slides/{n}/image` | slide PNG (fetched with the token, not an `<img src>`) |
| `POST` | `/api/sessions/{id}/retry` ☁️ | prepare a failed or finished deck again |
| `DELETE` | `/api/sessions/{id}` | the deck, its slides and its files |

**Live sessions** 🔒

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/interview/resume` | multipart `file` (PDF/DOCX/TXT, ≤ 5 MB) → `{text, chars}`. Nothing is stored. |
| `POST` | `/api/interview/plan` ☁️ | `{position, company?, level, interview_type, background?, job_description?, resume_text?}` → `{intro, questions: [{question, assesses, look_for}], source}` |
| `POST` | `/api/live` ☁️ | `{session_type, topic?}` for `Conversation`; `{session_type: "Interview", interview: {…setup}, plan?}`; `{session_type: "Presentation", deck_id, presentation_mode: "talk"\|"qa"}`. The response's `context` holds the setup and plan. |
| `GET` | `/api/live` | your sessions as summaries, newest first (score, the three drills, pillars, a few context labels); `?deck_id=` keeps one deck's attempts |
| `GET` | `/api/live/{id}` | the session in full: `status` (`active` → `analyzing` → `complete`/`failed`), `context`, `turns`, `analysis`, `warnings` |
| `POST` | `/api/live/{id}/end` | `{duration_sec, turns?: [{role, text, t_sec}], client_metrics?: {response_latency_sec, slide_times, stt_audio_sec}}` |
| `POST` | `/api/live/{id}/recording` | multipart `file`: the session recording (audio + video, or audio only) |
| `POST` | `/api/live/{id}/analyze` ☁️ | `202`, starts the analysis |
| `DELETE` | `/api/live/{id}` | the session and its recording |

**Conversation** 🔒

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/chat/message` ☁️ | the AI partner: `{messages, mode, topic?, live_id?}` → `{reply, progress?, total_questions?}`. With the `live_id` of a planned session it follows that plan. Empty `messages` gives the opening line. |
| `POST` | `/api/stt` ☁️ | multipart `file` (one spoken turn) + `context?` (what it answers, for topic words) → `{text, engine}` |
| `POST` | `/api/tts/speak` | `{text, voice?}` → streamed MP3 |

**Notifications** 🔒: `GET /api/notifications`, `POST /api/notifications/{id}/read`, `POST /api/notifications/read-all`.

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite (63 tests) uses SQLite and a temporary storage directory, with all AI keys blanked so every stage runs its offline fallback:

- **End-to-end:** deck upload → slides + insights + Q&A plan → a talk session over it → per-slide feedback; decks and slide images are private to their owner; the history list is a summary.
- **Accounts and live sessions** (`test_live.py`): register/login/refresh/profile, per-user isolation, sign-in on every cloud endpoint, recording → analysis with local models off (model-only metrics come back `null`, audio-level blocks are still measured), and the language, fluency, filler, stuttering and scoring logic.
- **Practice functions, privacy, phone-level pronunciation, silence filter and Gaze Tunneling, notifications, talk feedback.**

The tests need ffmpeg; if it isn't on `PATH`, they use the pip-installed `imageio-ffmpeg` binary. If LibreOffice is missing, slide rendering is replaced by a Pillow renderer so every other stage still runs for real.

---

## Project layout

```
app/
  main.py                 FastAPI app, lifespan (recovers interrupted jobs)
  config.py               all settings (env / .env)
  auth.py                 password hashing, JWT tokens, current-user and consent dependencies
  limits.py               rate limits and upload size caps
  models/                 Session (deck), Slide, User, LiveSession, Notification
  routers/                sessions.py (decks), live.py (live sessions), conversation.py (partner, STT, TTS),
                          auth.py (accounts, privacy), notifications.py, health.py
  services/
    pipeline.py           deck preparation (render → insights → Q&A plan)
    slide_processor.py    .pptx/.pdf → PNGs + slide text
    deck_insights.py      deck summary, structure, key points (LLM or rules)
    practice_plans.py     interview / Q&A plans, the plan-following partner, answer feedback
    media.py              ffmpeg helpers (silences, peak level)
    tasks.py              background job runner
    live/                 live-session analysis: asr, language, speech, phone_gop + pronunciation,
                          vision, extra_metrics (prosody, hedging, Gaze Tunneling), talk, coaching, scoring, pipeline
  prompts/                the AI partner's personas
alembic/                  migrations
scripts/                  make_sample_deck.py, seed_demo.py (demo accounts), benchmark/
tests/                    unit + end-to-end tests
docs/                     the source paper and the original Phase 1 specs (historical)
```

## Differences from the paper

- **Analysis works on transcripts plus metrics, not raw audio.** The paper sends audio straight to Gemini 2.5 Pro. This build uses Whisper, deterministic metrics and an LLM instead, which is easier to debug and cheaper. The trade-off is that tone and intonation are measured (pitch, loudness) rather than judged directly.
- **No narrated example video.** The paper's Ideal Presentation Agent narrated the deck in the user's voice; here the Deck Agent's job is to understand the deck so the talk and the Q&A can be checked against it (removed 2026-10-07).
- **Not included:** the paper's user study. The frontend lives in `../frontend`.
