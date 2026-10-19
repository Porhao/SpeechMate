# SpeechMate

An AI-powered communication and speech-coaching web app, built as a Final Year Project (FYP), with a specific focus on **Malaysian speakers** — English, Bahasa Malaysia, and the code-switched "Manglish" speech that generic Western speech-coaching tools handle badly.

The core idea: give a user a live practice session (camera + mic), analyse how they spoke and presented afterward across several channels — fluency, pronunciation, disfluency, eye contact, posture, facial emotion — and turn that into a single communication score plus specific, personalised, actionable feedback.

---

## Positioning / what makes this different

Three deliberate differentiators, chosen over other directions (an educator/cohort-dashboard role was considered and explicitly dropped from scope):

1. **Accent-fair pronunciation scoring.** Deviations from "standard" pronunciation are split into two buckets: consistent Malaysian-English phonology (regional variation — not penalised) vs. deviations that would actually cost a listener intelligibility (flagged). Malaysian-accented speech gets a documented scoring tolerance rather than being marked down against American/British norms it was never trying to match.
2. **"Never interrupts."** All scoring and correction is held until the user finishes speaking — nothing interrupts mid-sentence. This is a deliberate anxiety-reduction design choice (Cognitive Load Theory), not just a technical limitation, and it's called out directly in the product's own copy.
3. **Gaze Tunneling.** A fused metric that doesn't just report eye-contact percentage and disfluency count as two separate numbers — it computes the real Pearson correlation between gaze aversion and disfluency events over time, so the app can say "you look away right when you stumble" rather than two disconnected stats.

---

## Architecture

```
SpeechMate/
├── frontend/             Next.js 16 (App Router) + TypeScript — the web app
└── backend/   FastAPI (Python 3.12) — API, database, AI pipelines
```

### Frontend

- **Next.js 16** (Turbopack, App Router), **React 19**, **TypeScript**
- **Tailwind CSS v4** for styling — an "editorial minimal" design system (ink-on-paper palette, serif display type paired with a grotesque UI font)
- **Zustand** for client state (`useFeedbackStore`, `useSessionStore`, `useUserStore`)
- **framer-motion** for shared-layout/page transition animation
- **recharts** for score/progress visualisation (radar, composed, line charts)
- **MediaPipe Tasks Vision** (`FaceLandmarker` + `PoseLandmarker`) running client-side in the browser for real-time face-mesh and pose tracking during a session (camera stage, lighting advice). **Gaze Tunneling** is computed on the server after the session, from the recording (see below)
- **Web Audio API** for live mic-level analysis and **Web Speech API** for live transcription during a session

Pages (`app/(app)/`), organised around the three functions:
- `home`;
- `conversation` (topic picker);
- `interview` (setup, resume, question preview);
- `presentations` and `presentations/[id]` (deck insights, example, rehearsal, Q&A launcher);
- `session` (the live session for all three);
- `results/[id]` (the four-pillar report);
- `progress`, `methodology` ("How it's measured"), `profile`, `settings`.

(`assessment` only redirects old links.) Auth flow (`app/(auth)/`): `login`, `register`, `onboarding`. API clients live in `services/` (`api.ts`, `auth.ts`, `live.ts`, `presentation.ts`).

### Backend (`backend/`)

- **FastAPI** on Python 3.12, **SQLAlchemy** (async) on **PostgreSQL** with **Alembic** migrations
- JWT auth (`pyjwt`, `bcrypt`) with access + refresh tokens
- **AI services (cloud configuration, deployed and evaluated).** Speech-to-text: **Groq `whisper-large-v3`** (OpenAI-compatible API, word timestamps, automatic language). LLM: **Gemini `gemini-3.5-flash-lite`** through its OpenAI-compatible endpoint (`LLM_BASE_URL`): AI partner, interview and Q&A question plans, deck insights, answer feedback, coaching plans. Partner voice: **Kokoro-82M** (local container). Pronunciation, prosody and vision models run on the server. A local configuration (Ollama `qwen2.5`, local Malaysian Whisper) is still supported by settings; the local speech-to-text code is restorable from commit `6f89bed` (`docs/project/local-stt-removal.md`).
- Routers (`app/routers/`): `auth` (accounts + profile), `live` (live sessions, progress, reports), `conversation` (AI partner, which follows interview/Q&A plans; STT; TTS), `sessions` + `practice` (presentation coaching), `health`
- Long-running work (video generation, coaching analysis, live-session analysis) runs as in-process background jobs the frontend polls

---

## The live-session AI pipeline (`backend/app/services/live/`)

`pipeline.py` orchestrates the multimodal analysis, run in the background via `POST /api/live/{id}/analyze` after a session's recording is uploaded:

```
Recording → 16 kHz audio → ASR (routed) → Language detection → Speech analysis
          → Video frames → Vision analysis
          → Confidence → Communication score → Recommendations → Progress history
```

Heavy models are optional (`requirements-ml.txt`): each stage uses its model when available, otherwise a lighter real signal (ffmpeg silence detection), and otherwise reports the metric as unavailable (`null` + a warning) — it never invents a number.

**Speech**
- `asr.py` — routes each recording between two ASR engines instead of one general-purpose model:
  - one call to **Groq `whisper-large-v3`**: lossless FLAC upload, word and segment timestamps, a short verbatim Manglish prompt so fillers and code-switches are kept, automatic language detection;
  - a **silence filter** drops segments Whisper invents on silence or noise (by its no-speech probability and stock phrases such as "Subtitles by the Amara.org community"); calibrated in `docs/benchmarks/stt-groq-cloud-2026-10-15.md`;
  - measured: 4.9% WER on English, 7.3% on Malay, 16.5% on synthetic Manglish. The earlier dual-engine router (Whisper → Mesolitica code-switch model) was evaluated and removed: it doubled WER on mixed speech (`docs/benchmarks/stt-routing-and-finetune-2026-10-06.md`).
- `language.py` — a documented ~190-word Bahasa Malaysia/Manglish lexicon to estimate the English/Malay ratio, flag code-switching and Manglish particles, and apply the accent-fair pronunciation allowance. An honest word-list heuristic, not a trained language-ID model.
- `speech.py` — fluency (WPM, articulation rate, pauses from word timestamps or ffmpeg silence detection), English + Bahasa Melayu filler words counted in context (hesitations always; discourse markers like "like" / "macam" only as markers), and stuttering: a signal-processing heuristic for repetitions, mid-utterance blocks and energy-based prolongations. (The trained CNN + BiLSTM classifier in `TECHNICAL.md` is future work — it needs SEP-28k/UCLASS training.)
- `pronunciation.py` — Wav2Vec2 (`facebook/wav2vec2-base-960h`) CTC-confidence pronunciation scoring over proportional word spans (not full GOP forced alignment).

**Vision** (`vision.py`) — eye contact (MediaPipe Face Mesh iris landmarks → camera/left/right/down gaze), posture (MediaPipe Pose: head tilt, shoulder level, stability), and facial emotion (MediaPipe face crop + the `trpakov/vit-face-expression` classifier).

**Extra metrics & pillars** (`extra_metrics.py`):
- vocal variety (pitch, semitones) and volume/steadiness (librosa);
- vocabulary richness (MATTR) and hedging;
- gestures and head steadiness (MediaPipe Pose);
- response time (measured in the browser);
- Gaze Tunneling, computed on the server: a 2 fps iris-gaze stream from the video against the disfluencies' word timings, in 5 s windows, with a circular-shift permutation test (needs ≥ 100 s of speech);
- the four pillars that group all metrics for the results page.

**Scoring & recommendations** (`scoring.py`, `coaching.py`):
- cross-modal confidence (speech / face / body);
- the weighted overall score (re-weighted over whichever components were measured);
- an evidence-based coaching plan: the LLM may only pick and phrase issues that were actually measured.

**Interview & Q&A** (`app/services/practice_plans.py`):
- resume text extraction;
- LLM question plans (interview from the setup and resume; Q&A from the deck insights);
- the server-enforced plan the AI partner follows;
- per-answer feedback with a fact check on the "stronger answer".

**Presentation coaching** — deck preparation (`app/services/pipeline.py`: render the slides, deck insights, a cached Q&A plan), the slide-by-slide talk check (`app/services/live/talk.py`) and the Q&A rehearsal (`practice_plans.py`); see the backend README.

---

## Data model

PostgreSQL tables (`app/models/`): `users` (with the coaching profile), `live_sessions` (one practice session: its setup and question plan in `context`, transcript `turns`, browser `client_metrics`, recording and full analysis result), `notifications`; and for presentation decks `sessions`, `slides`.

---

## Status

Functional end to end for the three functions: live practice (record → analyse → score → feedback → progress) and presentation practice (deck → insights and Q&A plan → present on camera, judged slide by slide → Q&A rehearsal). The narrated example presentation was removed on 2026-10-07: the deck stage exists so the AI understands the deck and can check the talk against it. A LoRA fine-tune of Malaysian Whisper was trained and evaluated (`fine-tune/`) but is not deployed. Each analysis records its own usage (speech-to-text billed seconds, LLM tokens). Full technical write-up for the paper: `TECHNICAL.md`.
