# SpeechMate

An AI-powered communication and speech-coaching web app, built as a Final Year Project (FYP), with a specific focus on **Malaysian speakers**: English, Bahasa Malaysia, and the code-switched "Manglish" speech that generic Western speech-coaching tools handle badly.

You practise speaking (a live camera + mic session with an AI partner, or rehearsing a slide deck against an AI-narrated example). SpeechMate then analyses how you spoke and presented and turns that into specific, personalised, actionable feedback.

---

## 🌟 What makes this different

1. **Accent-fair pronunciation scoring.** Malaysian-English phonology (th → d/t, final-consonant reduction, vowel shifts) is treated as regional variation, not error: pronunciation scores get a documented accent allowance instead of being marked down against American/British norms.
2. **"Never interrupts."** All scoring and correction is held until you finish speaking. This is a deliberate anxiety-reduction design choice (Cognitive Load Theory).
3. **Gaze Tunneling.** Instead of reporting eye contact and disfluency as two separate numbers, the live session computes the Pearson correlation between gaze aversion and disfluency events over time, so the app can say "you look away right when you stumble".
4. **Presentation coaching against an ideal version of *your* talk.** Upload your slides and SpeechMate writes a narration script for each one, speaks it in your cloned voice and assembles an example video. It then coaches your rehearsals against that example with Observation → Impact → Suggestion feedback and a simulated audience's reaction (a re-implementation of [PresentCoach, Chen et al. 2025](backend/docs/2511.15253v2.pdf)).

---

## ✨ Features

| Feature | Where | What it does |
|---|---|---|
| **Live practice sessions** | `/practice` → `/session` | Conversation, Interview and Pronunciation modes with an AI partner that talks back (TTS). The browser tracks face, pose and speech in real time. |
| **Multimodal analysis** | `/assessment` | After a session: transcript, fluency, fillers (EN + BM), stuttering, pronunciation, English/Malay ratio and code-switching, eye contact, posture, emotion, confidence, an overall score and recommended exercises |
| **Presentation Coach** | `/presentations` | `.pptx` → AI script per slide → narration in your cloned voice → example video. Then record the whole deck or one slide and get coached, with a chat for follow-up questions. |
| **AI Coach** | `/coach` | A general coaching chat that knows your goal and recent results, plus a follow-up chat on any presentation attempt |
| **Accounts & profile** | `/register`, `/login`, `/profile` | JWT sign-in, and a coaching profile (goal, skill level, challenges) |
| **Progress & reports** | API: `/api/progress`, `/api/reports` | Every analysed session's metrics over time, and saved summary reports |

Every AI stage has a fallback. With **no API keys and no local models**, the app still runs end to end: scripts come from the slide text, the voice is offline espeak, feedback is rule-based, and anything that genuinely couldn't be measured is shown as unavailable rather than invented.

---

## 🏗️ Architecture

```
SpeechMate/
├── frontend/             Next.js 16 web app
├── backend/   FastAPI API + AI pipelines (see its README for the full API)
├── docker-compose.yml    Postgres + backend + frontend
└── start.sh              one-command start
```

- **Frontend:** Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS v4, Zustand, Recharts, framer-motion. MediaPipe Tasks Vision runs in the browser for live face/pose tracking, and the Web Audio + Web Speech APIs handle live mic level and transcription.
- **Backend:** FastAPI, async SQLAlchemy + Alembic on **PostgreSQL**, JWT auth. Long jobs (video generation, coaching, live analysis) run as in-process background tasks that the frontend polls.
- **AI:**
  - OpenAI: `gpt-4o-mini` for the vision-language model and LLM, TTS, and Whisper. `OPENAI_BASE_URL` also accepts any OpenAI-compatible provider.
  - ElevenLabs Instant Voice Cloning.
  - Local, optional CPU models:
    - **faster-whisper** for ASR, plus **Mesolitica `wav2vec2-xls-r-300m-mixed`** for Malay / code-switched speech
    - **Wav2Vec2** for pronunciation
    - **MediaPipe** for eye contact and posture, and a **ViT** facial-expression classifier for emotion
    - **librosa** for stutter prolongations
  - ffmpeg, LibreOffice and poppler for media and slides.

### How the live-session analysis works

```
recording (webm) → 16 kHz audio → ASR: faster-whisper; if not confidently English → code-switch model
   → language & Manglish detection → fluency · fillers · stuttering · pronunciation (+ accent allowance)
   → sampled video frames → eye contact · posture · emotion
   → confidence → weighted communication score → recommendations → progress history
```

---

## 🚀 Getting started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose.
- **WSL 2:** if `docker` says *"could not be found in this WSL 2 distro"*, open Docker Desktop → Settings → Resources → **WSL Integration**, enable your distro, then restart the terminal.

### 1. Configure (optional)

```bash
cp backend/.env.example backend/.env
```

Everything in `.env` is optional, but for real use set:

| Variable | Why |
|---|---|
| `SECRET_KEY` | signs login tokens. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `OPENAI_API_KEY` | AI slide scripts, coach feedback and chat, the live AI partner and its voice, and Whisper transcription when local models aren't installed |
| `ELEVENLABS_API_KEY` | narrating your deck in **your own cloned voice** (needs a plan with Instant Voice Cloning) |

`start.sh` creates `.env` from the example if you skip this step.

### 2. Start

```bash
./start.sh                     # or: docker compose up --build -d
```

| | |
|---|---|
| Frontend | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health | http://localhost:8000/health: which binaries, local models and AI providers are active |

The first build takes a while. The backend image includes the local ML models' libraries (about 2 GB), and their weights (about 2.5 GB) download the first time a live session is analysed. They're cached in a Docker volume after that. For a much smaller image without local models:

```bash
INSTALL_ML=false ./start.sh
```

Without them, the live-session analysis uses the OpenAI API for transcription (if a key is set). Pronunciation, eye contact, posture and emotion then show as unavailable.

### Useful commands

```bash
docker compose logs -f backend   # follow backend logs
docker compose down              # stop (data is kept in Docker volumes)
docker compose down -v           # stop and delete all data, recordings and cached models
```

---

## 🛠️ Development without Docker

**Backend.** Needs Python 3.11+, Postgres, ffmpeg, LibreOffice, poppler and espeak-ng. See [`backend/README.md`](backend/README.md) for details.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt          # + requirements-ml.txt for local models
docker compose up -d db                      # or your own Postgres (set DATABASE_URL)
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev                                  # http://localhost:3000
```

The frontend calls `http://localhost:8000/api` by default. Set `NEXT_PUBLIC_API_URL` to point it elsewhere.

### Tests

```bash
cd backend && pytest              # 27 tests, SQLite, runs fully offline
cd frontend && npx tsc --noEmit && npm run lint
```

---

## 📊 Data & storage

- **PostgreSQL** tables:
  - presentation coaching: `sessions`, `slides`, `practice_sessions`, `chat_messages`
  - accounts and live practice: `users`, `live_sessions`, `progress_records`, `reports`
- **Files** (decks, slide images, narration, videos, recordings) live under `STORAGE_BASE_PATH`, which is the `storage_data` volume under Docker.

---

## 📚 Documentation

- [`backend/README.md`](backend/README.md): full API reference, fallbacks, pipelines and the smoke test
- [`PROJECT.md`](PROJECT.md): project overview and positioning
- [`TECHNICAL.md`](TECHNICAL.md): theoretical foundations, model design and the evaluation protocol
- [`TODO.md`](TODO.md): roadmap (Phases 5–8)
- `backend/docs/`: design specs and the PresentCoach paper
- `docs/`: interim report and IEEE paper draft

## ⚠️ Current limitations

- **Stuttering** detection is a signal-processing heuristic (repetitions, silence blocks, energy-based prolongations). The trained CNN + BiLSTM classifier described in `TECHNICAL.md` needs a labelled dataset (SEP-28k / UCLASS) and is future work.
- **Pronunciation** uses Wav2Vec2 CTC confidence over proportional word spans, not full forced alignment (GOP / Montreal Forced Aligner).
- **English/Malay ratio** comes from a lexicon heuristic (~190 BM/Manglish words), not a trained language-ID model.
- The **Progress, Reports and Dashboard pages** still show sample data. The backend's `/api/progress` and `/api/reports` endpoints are ready for them to use.
- Presentation-coaching decks aren't tied to user accounts yet: anyone using the app can see every deck.
