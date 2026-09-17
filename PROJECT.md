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
04 Code/
├── frontend/   Next.js 16 (App Router) + TypeScript — the web app
└── backend/    FastAPI (Python 3.13) — API, DB, AI pipeline
```

### Frontend

- **Next.js 16** (Turbopack, App Router), **React 19**, **TypeScript**
- **Tailwind CSS v4** for styling — an "editorial minimal" design system (ink-on-paper palette, serif display type paired with a grotesque UI font)
- **Zustand** for client state (`useFeedbackStore`, `useSessionStore`, `useUserStore`)
- **framer-motion** for shared-layout/page transition animation
- **recharts** for score/progress visualisation (radar, composed, line charts)
- **MediaPipe Tasks Vision** (`FaceLandmarker` + `PoseLandmarker`) running client-side in the browser for real-time face-mesh and pose tracking during a session
- **Web Audio API** for live mic-level analysis and **Web Speech API** for live transcription during a session

Pages (`app/(app)/`): `home`, `practice`, `session` (the live coaching session), `assessment`, `dashboard`, `progress`, `reports`, `coach` (AI chat), `methodology`, `profile`, `settings`. Auth flow (`app/(auth)/`): `login`, `register`, `onboarding`.

### Backend

- **FastAPI** on Python 3.13, **SQLAlchemy** (async, SQLite via `aiosqlite`) with **Alembic** migrations
- JWT auth (`python-jose`, `passlib`/`bcrypt`)
- **OpenAI API** for the AI coaching chat and feedback generation
- Routes (`app/api/routes/`): `auth`, `users`, `practice`, `speech`, `analysis`, `vision`, `coach`, `chat`, `tts`, `reports`, `websocket`

---

## The AI pipeline (`app/ai/`)

`app/ai/pipeline.py` orchestrates the full multimodal analysis, run via `POST /analysis/run` after a practice session ends:

```
Audio + Video → ASR → Speech Analysis → Vision Analysis
             → Confidence Estimation → Communication Scoring
             → Recommendation Engine → Structured Feedback
```

**Speech (`app/ai/speech/`)**
- `asr.py` — routes each recording between two ASR engines instead of one general-purpose model:
  - **faster-whisper** ("small", CPU int8, word-level timestamps) always runs first and doubles as the language-confidence signal.
  - If Whisper isn't confidently English, the same audio is re-run through **Mesolitica's `wav2vec2-xls-r-300m-mixed`** (`codeswitch_engine.py`) — a model trained specifically on Malay/Singlish/Mandarin-mixed speech (WER 0.132 / CER 0.048 per its model card), loaded directly via `transformers`/PyTorch (the same checkpoint the `malaya-speech` toolkit itself wraps, without needing that package or TensorFlow).
- `lexicon.py` — a documented ~190-word Bahasa Malaysia/Manglish lexicon used to estimate English/Malay ratio and flag code-switching — an honest word-list heuristic, not a trained language-ID model.
- `malaysian.py` — language/accent detection and the accent-fair pronunciation tolerance, built on the lexicon above.
- `fluency.py`, `stuttering.py`, `pronunciation.py`, `fillers.py`, `confidence.py`, `scoring.py` — WPM/pause/continuity analysis, disfluency detection, pronunciation (GOP-based) assessment, filler-word detection, and the cross-modal confidence/communication scores.

**Vision (`app/ai/vision/`)** — `eye_contact.py`, `emotion.py`, `posture.py`, all MediaPipe/OpenCV-based frame analysis.

**Recommendations (`app/ai/recommendation/`)** — turns all of the above into a weekly focus, daily practice targets, and prioritised exercises.

**Coach (`app/ai/llm/`)** — the OpenAI-backed conversational coaching chat.

---

## Data model

SQLite tables (`app/models/`): `users`, `user_profiles`, `practice_sessions`, `speech_analysis`, `vision_analysis`, `ai_feedback`, `progress_history`, `reports` — one practice session fans out into a speech-analysis row, a vision-analysis row, an AI-feedback row, and a set of per-metric progress-history rows for trend charts.

---

## Status

Functional end-to-end for the core loop (record → analyse → score → feedback → progress tracking), running on pretrained inference only (no model fine-tuning/training). The code-switching ASR model's full weights are downloaded on first real (non-English) transcription rather than bundled, since they're ~1.2GB.
