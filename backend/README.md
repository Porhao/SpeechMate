# SpeechMate Backend

The API behind SpeechMate, an AI communication coach for Malaysian speakers. It serves the app's three functions:
- **Daily conversation**;
- **Mock interview** (questions curated from the role, background and resume);
- **Presentation practice** (deck insights, narrated example, coached rehearsals, Q&A drawn from the deck).

Every AI function and metric is listed in [`../docs/AI_MATRIX.md`](../docs/AI_MATRIX.md).

**Presentation coaching**: a dual-agent presentation coach, re-implementing the ideas of
[PresentCoach (Chen et al., 2025, arXiv:2511.15253)](docs/2511.15253v2.pdf):

1. **Ideal Presentation Agent**: you upload a `.pptx` (plus, optionally, a short voice sample and a note about your audience). It renders each slide, writes a 60–100 word narration script per slide with a vision-language model, speaks the scripts in **your cloned voice**, and assembles a narrated benchmark video.
2. **Coach Agent**: you upload a recording of yourself practising, either the whole deck or a single slide. It measures your delivery against the ideal version and returns:
   - **Sincere Encouragement** plus 1–3 **Observation → Impact → Suggestion** items (under 150 words)
   - an **Audience** reaction from a simulated listener in your target audience
   - a **chat** for follow-up questions, which also remembers your earlier attempts on the same deck

**Live practice sessions**: the web app's camera + mic sessions with an AI partner.
- **Conversation**: a topic.
- **Interview**: a question plan curated from the setup and resume (`/api/interview/*`).
- **Presentation**: a Q&A plan drawn from a deck's insights.

In Interview and Presentation sessions the server enforces the plan: one question at a time, word for word, with at most one follow-up for a short answer. After a session, the recording goes through a multimodal analysis:

- **speech**:
  - ASR: Mesolitica Malaysian Whisper with auto language detection, re-run through Mesolitica's Malay/code-switching model when the speech isn't confidently English;
  - fluency;
  - filler words in context (English + Bahasa Melayu);
  - stuttering (repetitions, blocks, prolongations);
  - Wav2Vec2 pronunciation with a Malaysian-English accent allowance;
  - pitch variation and loudness (librosa), vocabulary richness and hedging;
  - English/Malay ratio and Manglish detection.
- **vision**: eye contact (MediaPipe iris tracking), posture, gestures and head steadiness (MediaPipe Pose), facial emotion (ViT expression classifier).
- **from the browser**: response time and Gaze Tunneling.
- **scoring**: cross-modal confidence, a weighted overall score, **four pillars** (voice, language, body, confidence) and three evidence-based drills, saved as progress history.
- **content**: per-answer feedback against the plan for interviews and Q&A (fact-checked stronger answers), or language tips for conversations.

**Accounts**: register/login with JWT access + refresh tokens, and a coaching profile (goal, skill level, challenges) that the coaching plan uses.

The backend is FastAPI with async SQLAlchemy and Postgres. Jobs run in-process as asyncio tasks. Every AI stage has an offline fallback, so you can run everything with **no API keys at all**. The heavy local models for live analysis are optional too (see [Local models](#local-models-for-live-analysis)).

---

## Quick start (Docker, recommended)

Docker bundles everything the pipeline needs: LibreOffice, poppler, ffmpeg, espeak-ng, fonts and (by default) the local ML models.

```bash
cp .env.example .env          # set SECRET_KEY; optionally add OPENAI_API_KEY / ELEVENLABS_API_KEY
docker compose up --build     # API on http://localhost:8000, Postgres on :5432
INSTALL_ML=false docker compose up --build    # slim image without the ~2 GB of local models
```

To run the whole app (backend + frontend + database), use `./start.sh` in the repository root instead.

Migrations run automatically on startup. Then:

- **Swagger UI:** http://localhost:8000/docs, where you can try every endpoint in the browser
- **Health and capabilities:** http://localhost:8000/health shows which binaries and providers are available, and therefore which fallbacks will be used

### Run the end-to-end smoke test

In a second terminal, using any Python 3.11+ with `httpx` and `python-pptx`:

```bash
pip install httpx python-pptx
python scripts/smoke_test.py                                   # generated sample deck, no mic needed
python scripts/smoke_test.py --deck my_talk.pptx \
       --voice my_voice.m4a --practice my_rehearsal.webm       # your own files
```

The smoke test runs the whole loop: upload → poll the 4 stages → download the video → whole-deck practice → per-slide practice → chat. Results are written to `./smoke_output/` (the `ideal_video.mp4` and the JSON responses). Without `--practice`, the generated ideal video is re-uploaded as the "practice" recording.

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
docker compose up -d db                     # (or use your own Postgres / Supabase)
alembic upgrade head
uvicorn app.main:app --reload
```

If a binary isn't on your `PATH`, point to it with `FFMPEG_BIN`, `LIBREOFFICE_BIN` or `ESPEAK_BIN`. On macOS LibreOffice is usually at `/Applications/LibreOffice.app/Contents/MacOS/soffice`.

---

## API keys and fallbacks

All keys are optional. The AI layer is local-first: an LLM served by Ollama (`LLM_BASE_URL`), plus local speech, vision and TTS models (`requirements-ml.txt`). "LLM" below means whichever you've configured: a local model via `LLM_BASE_URL`, or OpenAI via `OPENAI_API_KEY`. Here is what each stage uses and what happens without it:

| Stage | With keys | Without keys (fallback) |
|---|---|---|
| Slide → script | the vision model (`VLM_MODEL`, e.g. Ollama `qwen2.5vl`) reads each slide image, with the previous slide's script as context for transitions | A template script built from the slide's own text |
| Script → voice | **local Malaysian TTS** (`mesolitica/Malaysian-TTS-0.6B-v1`) in the deck's narrator voice. Only with `ELEVENLABS_API_KEY` + a voice sample: your cloned voice. | OpenAI TTS (if keyed) → espeak-ng (offline) → silence |
| Practice → transcript | `OPENAI_API_KEY`: Whisper, prompted to keep "um/uh" verbatim | Skipped. Only audio metrics (duration, pauses) are used. |
| Coach OIS feedback | LLM, JSON-validated, re-prompted once if invalid or over 150 words | Rule-based OIS from the metrics |
| Audience feedback | LLM role-plays your target audience | Rule-based from the metrics |
| Chat | LLM with deck, attempt and history context | Replies with your saved suggestions |
| Live session: AI partner + TTS | the LLM writes the partner's replies (`/api/chat/message`); its voice (`/api/tts/speak`) comes from a local Kokoro server (`TTS_BASE_URL`), then OpenAI TTS, then the Malaysian TTS on a GPU | Conversation: `503`, and the frontend falls back to scripted prompts and the browser's speech synthesis. Interview / Q&A: still follows its plan, with fixed reactions |
| Interview / Q&A question plan | LLM, JSON-validated and re-prompted; labels and placeholders stripped | Behavioural / technical question bank; for a deck, its likely questions and key points |
| Answer feedback / language tips | LLM, JSON-validated; stronger answers fact-checked against what was said | Rule-based (STAR cue words, numbers, length, overlap with the question) |
| Live session: speech recognition | Local faster-whisper (+ code-switch model), else OpenAI Whisper with word timestamps | Word-level metrics skipped; pauses and stutter blocks are still measured from the audio |

Every fallback is recorded in the `warnings` field of the session, practice or live-session response. Nothing fails silently, and no metric is ever made up: one that couldn't be measured is `null`.

**Notes**
- ElevenLabs voice cloning requires a plan that includes *Instant Voice Cloning*. The free tier returns an error, and the pipeline then falls back to a standard voice. The temporary cloned voice is deleted after each generation.
- For best cloning results, record 30–60 seconds of clear speech in a quiet room. Any common format (wav, mp3, m4a, webm, ogg) works; uploads are converted to WAV.
- **Local LLM (Ollama):** set `LLM_BASE_URL=http://ollama:11434/v1` (the root compose's bundled Ollama) or `http://host.docker.internal:11434/v1` (an Ollama on your machine), plus `LLM_MODEL` / `VLM_MODEL` to Ollama tags, e.g. `qwen2.5:3b` / `qwen2.5vl:3b`, or `7b` with ≥16 GB RAM. Only text and vision calls go there; speech keeps using OpenAI or the local models. `LLM_TIMEOUT_SEC` (default 300) allows for slow CPU inference. JSON-mode coach feedback works with Qwen2.5 as-is.
- **Malaysian TTS:** Malay, English and code-switched speech, 7 fixed voices (`GET /api/narrator-voices`; default `MALAYSIAN_TTS_VOICE`). It does **not** clone voices. The text is spelled out (numbers → words) and chunked (~10 s per generation). CPU works but is slow (minutes per slide); it's used for the live partner's voice only on a GPU (`LIVE_TTS_LOCAL=auto`) unless forced.
- `OPENAI_BASE_URL` lets you point the OpenAI client at any OpenAI-compatible endpoint. For example, you can use Qwen2.5-VL / Qwen2.5 through DashScope to match the paper's models (set `VLM_MODEL` / `LLM_MODEL` to match).

### Local models for live analysis

`requirements-ml.txt` adds CPU-only PyTorch, transformers, faster-whisper, librosa, MediaPipe and OpenCV (about 2 GB installed). The model weights (about 2.5 GB more) download on first use and are cached, which the root `docker-compose.yml` keeps in the `model_cache` volume. Each stage checks for its own packages:

| Metric | Needs | Without it |
|---|---|---|
| Transcript + word timings | `faster_whisper` | OpenAI Whisper API, or no transcript |
| Malay / code-switched transcript | `transformers`, `torch` | the Whisper transcript is kept, with a warning |
| Pronunciation | `transformers`, `torch` (Wav2Vec2) | `null` |
| Stutter prolongations | `librosa` | only prolongations the transcript spells out ("sooo") |
| Eye contact, posture | `cv2`, `mediapipe` | `null` |
| Facial emotion | `mediapipe`, `transformers`, `torch` | `null` |
| Presentation narration | `distilcodec`, `transformers`, `torch` (Malaysian TTS) | OpenAI TTS → espeak-ng |

`GET /health` lists which are installed, and `USE_LOCAL_ML=false` turns them all off. The overall and confidence scores are re-weighted over whichever components were measured, and the response's `communication_score.scored_on` says which ones those were.

---

## How it works

```
POST /api/sessions (.pptx, voice?, requirement?)
  └─ Ideal Presentation Agent (background job)
       processing_slides   .pptx → PDF (LibreOffice) → 1920px PNGs (pdftoppm) + slide text (python-pptx)
       generating_scripts  VLM per slide, sequential for smooth transitions, 60–100 words enforced
       synthesizing_audio  [ElevenLabs clone] → local Malaysian TTS → OpenAI TTS → espeak-ng → silence, normalized to WAV
       assembling_video    ffmpeg: PNG + WAV → per-slide MP4 segment → concat → ideal_video.mp4
       complete

POST /api/sessions/{id}/practice (audio or video, whole_deck | per_slide)
  └─ Coach Agent (background job)
       transcribing  normalize → Whisper
       analyzing     deterministic metrics (WPM vs. ideal, pauses via ffmpeg silencedetect,
                     filler words, key-term coverage of the ideal script, duration ratio)
                     → OIS coach feedback + audience feedback (LLM or rule-based)
       complete
```

```
POST /api/live → POST /api/live/{id}/recording (webm/mp4/wav) → POST /api/live/{id}/analyze
  └─ Live analysis (background job; poll GET /api/live/{id})
       analyzing  16 kHz WAV (ffmpeg) → ASR: faster-whisper, re-run through the code-switch model
                  if not confidently English (or the OpenAI API) → language / Manglish detection
                  → fluency (word timings or ffmpeg silences) → fillers (EN + BM) → stuttering
                  → pronunciation (Wav2Vec2 + accent allowance)
                  → sampled video frames → eye contact / posture / emotion (MediaPipe, ViT)
                  → confidence → communication score → recommendations → progress records
       complete | failed
```

- **Why metrics are computed in code:** they're deterministic and unit-tested, and the LLM only turns them into prose. So when the coach says something, you can always trace it back to a number ("Path B" in `docs/04-coach-agent-spec.md`).
- **Restarts:** jobs that were running when the server stopped are marked `failed` on the next startup. Re-run them with `POST /api/sessions/{id}/retry`, by re-uploading the practice recording, or with `POST /api/live/{id}/analyze`.
- **Concurrency:** at most `MAX_CONCURRENT_JOBS` pipelines run at once (default 2).

### Storage layout (`STORAGE_BASE_PATH`)

```
{session_id}/
  original.pptx  voice_sample_upload.*  voice_sample.wav  slides.pdf
  slides/slide_N.png   scripts/slide_N.json   audio/slide_N.wav
  segments/slide_N.mp4  ideal_video.mp4
  practice/{practice_id}/user_audio_upload.*  user_audio.wav
live/{live_session_id}/
  recording.*  audio_16k.wav
```

---

## API reference

Interactive docs are at `/docs`. All routes are under `/api` except `/health`.

**Ideal Presentation Agent**

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/sessions` | multipart: `pptx` (required), `narrator_voice`, `voice_sample`, `requirement_prompt` → `201 {session_id, status}` |
| `GET` | `/api/narrator-voices` | Malaysian TTS voices, the default, and whether the model is installed |
| `GET` | `/api/sessions` | list sessions |
| `GET` | `/api/sessions/{id}` | status, `slides_progress`, `warnings`, `error_detail`, `video_ready`, `voice_cloning_used` |
| `GET` | `/api/sessions/{id}/scripts` | per-slide script, sources, and `start_sec`/`duration_sec` in the video (for syncing the script panel) |
| `GET` | `/api/sessions/{id}/video` | the MP4 (`409` until complete) |
| `GET` | `/api/sessions/{id}/slides/{n}/image` | slide PNG |
| `GET` | `/api/sessions/{id}/slides/{n}/audio` | ideal narration for one slide (WAV) |
| `POST` | `/api/sessions/{id}/retry` | re-run a failed or finished session |
| `DELETE` | `/api/sessions/{id}` | delete the session, its practice runs and its files |

**Coach Agent**

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/sessions/{id}/practice` | multipart: `audio` (wav/mp3/m4a/webm/ogg/flac/mp4/mov), `recording_granularity` = `whole_deck` (default) or `per_slide`, `slide_index` (required for per_slide). Returns `409` if the ideal video isn't complete. |
| `GET` | `/api/sessions/{id}/practice` | all attempts, oldest first (progress over time) |
| `GET` | `/api/sessions/{id}/practice/{pid}` | status, `metrics`, `feedback`, `audience_feedback`, `transcript`, `warnings` |
| `POST` | `/api/sessions/{id}/practice/{pid}/chat` | JSON `{"message": "..."}` → `{role, content}` |
| `GET` | `/api/sessions/{id}/practice/{pid}/chat` | chat history |

**Accounts** (send `Authorization: Bearer <access_token>` to the endpoints marked 🔒)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/auth/register` | JSON `{full_name, email, password (≥8), language?, communication_goal?}` → `201` |
| `POST` | `/api/auth/login` | JSON `{email, password}` → `{access_token, refresh_token}` (access 30 min, refresh 7 days) |
| `POST` | `/api/auth/refresh` | JSON `{refresh_token}` → a new token pair |
| `POST` | `/api/auth/logout` | tokens are stateless; the client discards them |
| `GET` / `PUT` | `/api/users/profile` 🔒 | name, language, age group, communication goal, skill level, challenges |

**Live practice sessions** 🔒

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/interview/resume` | multipart `file` (PDF/DOCX/TXT, ≤ 5 MB) → `{text, chars}`. Nothing is stored. |
| `POST` | `/api/interview/plan` | `{position, company?, level, interview_type, background?, job_description?, resume_text?}` → `{intro, questions: [{question, assesses, look_for}], source}` |
| `POST` | `/api/live` | `{session_type, topic?}` for `Conversation`; `{session_type: "Interview", interview: {…setup}, plan?}` (the plan is built if omitted); `{session_type: "Presentation", deck_id}` (Q&A plan built from the deck's insights, `409` until they exist). The response's `context` holds the setup and plan. |
| `GET` | `/api/live` | your sessions, newest first |
| `GET` | `/api/live/{id}` | `status` (`active` → `analyzing` → `complete`/`failed`), `context`, `turns`, `analysis` (incl. `pillars`, `content_feedback`, `recommendations`), `warnings` |
| `POST` | `/api/live/{id}/end` | `{duration_sec, turns?: [{role, text, t_sec}], client_metrics?: {response_latency_sec: [...], gaze_tunneling}}` |
| `POST` | `/api/live/{id}/recording` | multipart `file`: the session recording (audio + video, or audio only) |
| `POST` | `/api/live/{id}/analyze` | `202`, starts the analysis. Re-running it replaces the session's progress points. |
| `DELETE` | `/api/live/{id}` | the session, its progress points and its recording |
| `GET` | `/api/progress` | every metric from every analysed session, oldest first (incl. `voice_score`, `language_score`, `body_score`, `presence_score`) |
| `POST` | `/api/reports/generate` | snapshot report: per-metric average/first/latest/best/change, session totals, latest recommendations |
| `GET` | `/api/reports`, `/api/reports/{id}` | saved reports |

**Conversation**

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/chat/message` | the AI partner: `{messages, mode, topic?, live_id?}` → `{reply, progress?, total_questions?}`. With the `live_id` of a planned Interview / Presentation session (and your token), it follows that plan. Empty `messages` gives the opening line. Free conversation needs an LLM, otherwise `503`. |
| `POST` | `/api/stt` | multipart `file`: one spoken turn (WAV/WebM) → `{text, engine}`. Local faster-whisper (auto language, or `STT_LANGUAGE`), else OpenAI; `503` makes the frontend use the browser's recogniser. |
| `POST` | `/api/tts/speak` | `{text, voice?}` → streamed MP3 |
| `GET` | `/api/tts/voices` | the available voices |

<details>
<summary>Example feedback payload</summary>

```json
{
  "feedback": {
    "encouragement": "Your opening matched the ideal pace almost exactly — 142 vs. 145 WPM.",
    "observations": [
      {
        "slide_index": 2,
        "observation": "You paused for 4.1s before the Eisenhower matrix point.",
        "impact": "The silence broke momentum right before your key framework.",
        "suggestion": "Bridge with \"Here's a simple tool for that\" instead of pausing."
      }
    ],
    "source": "llm"
  },
  "audience_feedback": {
    "audience_profile": "first-year university students",
    "clarity_score": 4, "engagement_score": 3,
    "confusing_moments": ["I didn't know what 'Eisenhower matrix' meant"],
    "key_takeaway": "Plan your top three tasks the night before",
    "questions_i_would_ask": ["How long should a focus block be?"]
  }
}
```
</details>

### Quick curl walkthrough

```bash
SID=$(curl -s -F pptx=@deck.pptx -F voice_sample=@voice.m4a \
      -F requirement_prompt="Non-specialist audience, 5-minute talk" \
      localhost:8000/api/sessions | python -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
curl -s localhost:8000/api/sessions/$SID                    # poll until "complete"
curl -s localhost:8000/api/sessions/$SID/video -o ideal.mp4
PID=$(curl -s -F audio=@rehearsal.webm localhost:8000/api/sessions/$SID/practice \
      | python -c "import sys,json;print(json.load(sys.stdin)['practice_id'])")
curl -s localhost:8000/api/sessions/$SID/practice/$PID      # poll until "complete"
curl -s -H 'Content-Type: application/json' -d '{"message":"How do I fix my pacing?"}' \
     localhost:8000/api/sessions/$SID/practice/$PID/chat
```

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite uses SQLite and a temporary storage directory, with all AI keys blanked:

- **Unit tests:** metrics, filler/coverage logic, OIS validation and re-prompting (with a fake LLM), and VLM word-count re-prompting.
- **End-to-end API test:** upload → ideal video → silent-recording rejection → practice with a synthetic track (checks that the pause is detected) → per-slide practice → chat → retry → delete.
- **Accounts and live sessions** (`test_live.py`): register/login/refresh/profile, per-user isolation, recording → analysis with local models off (checks that model-only metrics come back `null` rather than invented, and that audio-level blocks are still measured), progress, reports, and unit tests for the language, fluency, filler, stuttering and scoring logic.

The tests need ffmpeg; if it isn't on `PATH`, they use the pip-installed `imageio-ffmpeg` binary. If LibreOffice is missing, slide rendering is replaced by a Pillow renderer so every other stage still runs for real.

---

## Project layout

```
app/
  main.py                 FastAPI app, lifespan (recovers interrupted jobs)
  config.py               all settings (env / .env)
  auth.py                 password hashing, JWT tokens, current-user dependencies
  models/                 Session, Slide, PracticeSession, ChatMessage, User, LiveSession, ProgressRecord, Report
  routers/                sessions.py (Ideal Agent), practice.py (Coach Agent), auth.py (accounts),
                          live.py (live sessions, progress, reports), conversation.py (partner, coach, TTS), health.py
  services/
    pipeline.py           Ideal Presentation Agent orchestration (4 stages)
    slide_processor.py    .pptx → PNGs + slide text
    script_generator.py   VLM narration + fallback
    speech_synthesizer.py narration chain: [ElevenLabs clone] / Malaysian TTS / OpenAI TTS / espeak / silence
    malaysian_tts.py      local Mesolitica Malaysian TTS (text normalizing, chunking, DistilCodec decoding)
    media.py              ffmpeg helpers (normalize, silencedetect, segments, concat)
    tasks.py              background job runner
    coach/                metrics, transcription, OIS + audience feedback, chat, pipeline
    live/                 live-session analysis: asr, language (Malaysian), speech, pronunciation,
                          vision, scoring, pipeline
alembic/                  migrations (0001 presentation coaching, 0002 accounts + live sessions, 0003 narrator voice)
scripts/                  make_sample_deck.py, smoke_test.py, seed_demo.py (demo accounts)
tests/                    unit + end-to-end tests
docs/                     design specs and the source paper
```

## Differences from the paper

- **Analysis works on transcripts plus metrics, not raw audio.** The paper sends audio straight to Gemini 2.5 Pro. This build uses Whisper, deterministic metrics and an LLM instead, which is easier to debug and cheaper. The trade-off is that tone and intonation aren't judged directly; pace, pauses, fillers and content are.
- **Different models by default:** OpenAI and ElevenLabs instead of Qwen2.5-VL, CosyVoice2, Gemini and Qwen2.5. The paper's Qwen models work through `OPENAI_BASE_URL`.
- **Not included:** the paper's user study. The frontend lives in `../frontend`.
