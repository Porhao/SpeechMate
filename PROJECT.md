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
- **MediaPipe Tasks Vision** (`FaceLandmarker` + `PoseLandmarker`) running client-side in the browser for real-time face-mesh and pose tracking during a session — this is also where the **Gaze Tunneling** metric is computed
- **Web Audio API** for live mic-level analysis and **Web Speech API** for live transcription during a session

Pages (`app/(app)/`): `home`, `practice`, `session` (the live coaching session), `assessment`, `presentations` (presentation coach), `coach` (AI chat), `dashboard`, `progress`, `reports`, `methodology`, `profile`, `settings`. Auth flow (`app/(auth)/`): `login`, `register`, `onboarding`. API clients live in `services/` (`api.ts`, `auth.ts`, `live.ts`, `presentation.ts`).

### Backend (`backend/`)

- **FastAPI** on Python 3.12, **SQLAlchemy** (async) on **PostgreSQL** with **Alembic** migrations
- JWT auth (`pyjwt`, `bcrypt`) with access + refresh tokens
- **OpenAI** (`gpt-4o-mini`) for the live-session AI partner, the general coach, presentation scripts (vision-language), OIS coaching feedback and TTS; **ElevenLabs** for voice cloning. Any OpenAI-compatible provider works through `OPENAI_BASE_URL`.
- Routers (`app/routers/`): `auth` (accounts + profile), `live` (live sessions, progress, reports), `conversation` (AI partner, general coach, TTS), `sessions` + `practice` (presentation coaching), `health`
- Long-running work (video generation, coaching analysis, live-session analysis) runs as in-process background jobs the frontend polls

---

## The live-session AI pipeline (`backend/app/services/live/`)

`pipeline.py` orchestrates the multimodal analysis, run in the background via `POST /api/live/{id}/analyze` after a session's recording is uploaded:

```
Recording → 16 kHz audio → ASR (routed) → Language detection → Speech analysis
          → Video frames → Vision analysis
          → Confidence → Communication score → Recommendations → Progress history
```

Heavy models are optional (`requirements-ml.txt`): each stage uses its local model when installed, otherwise a lighter real signal (OpenAI Whisper, ffmpeg silence detection), and otherwise reports the metric as unavailable (`null` + a warning) — it never invents a number.

**Speech**
- `asr.py` — routes each recording between two ASR engines instead of one general-purpose model:
  - **faster-whisper** ("small", CPU int8, word-level timestamps) always runs first and doubles as the language-confidence signal.
  - If Whisper isn't confidently English, the same audio is re-run through **Mesolitica's `wav2vec2-xls-r-300m-mixed`** — a model trained specifically on Malay/Singlish/Mandarin-mixed speech (WER 0.132 / CER 0.048 per its model card), loaded directly via `transformers`/PyTorch (the same checkpoint `malaya-speech` wraps, without needing that package or TensorFlow).
  - Without local models, the OpenAI transcription API (with word timestamps) is used instead.
- `language.py` — a documented ~190-word Bahasa Malaysia/Manglish lexicon to estimate the English/Malay ratio, flag code-switching and Manglish particles, and apply the accent-fair pronunciation allowance. An honest word-list heuristic, not a trained language-ID model.
- `speech.py` — fluency (WPM, articulation rate, pauses from word timestamps or ffmpeg silence detection), English + Bahasa Melayu filler words, and stuttering: a signal-processing heuristic for repetitions, mid-utterance blocks and energy-based prolongations. (The trained CNN + BiLSTM classifier in `TECHNICAL.md` is future work — it needs SEP-28k/UCLASS training.)
- `pronunciation.py` — Wav2Vec2 (`facebook/wav2vec2-base-960h`) CTC-confidence pronunciation scoring over proportional word spans (not full GOP forced alignment).

**Vision** (`vision.py`) — eye contact (MediaPipe Face Mesh iris landmarks → camera/left/right/down gaze), posture (MediaPipe Pose: head tilt, shoulder level, stability), and facial emotion (MediaPipe face crop + the `trpakov/vit-face-expression` classifier).

**Scoring & recommendations** (`scoring.py`) — cross-modal confidence (speech/face/body), the weighted communication score (re-weighted over whichever components were measured), and prioritised exercises, a weekly focus and daily practice targets.

**Presentation coaching** (`app/services/pipeline.py`, `app/services/coach/`) — the PresentCoach-style Ideal Presentation Agent and Coach Agent; see the backend README.

---

## Data model

PostgreSQL tables (`app/models/`): `users` (with the coaching profile), `live_sessions` (one live practice session, its recording and full analysis result), `progress_records` (one row per metric per analysed session, for trend charts), `reports`; and for presentation coaching `sessions`, `slides`, `practice_sessions`, `chat_messages`.

---

## Status

Functional end-to-end for both loops — live practice (record → analyse → score → feedback → progress) and presentation coaching (deck → ideal video → practice → OIS feedback → chat) — running on pretrained inference only (no model fine-tuning/training yet). Local model weights (~2.5 GB) are downloaded on first use rather than bundled.
