# SpeechMate

An AI speaking coach for **Malaysian speakers**, built as a Final Year Project (FYP). It handles English, Bahasa Malaysia and code-switched "Manglish", the speech that generic Western coaching tools handle badly.

SpeechMate does three things:

| | Function | How it works | What you get |
|---|---|---|---|
| 💬 | **Daily conversation** | Pick a topic and talk with an AI partner (camera + mic). | Your **voice, language, body language and confidence**, with language tips |
| 💼 | **Mock interview** | Enter the position, company, level, your background and (optionally) **your resume**. The AI curates the questions, then interviews you, following up when an answer is thin. | Everything above, plus **feedback on every answer**: relevance, STAR structure, specificity and a stronger version built from your own facts |
| 📊 | **Presentation practice** | Upload a `.pptx` or `.pdf`. The AI **reads and summarises the deck first**, narrates an example, coaches your rehearsals slide by slide, then runs a **Q&A drawn from your deck**. | Which slides' key points you missed, Observation → Impact → Suggestion coaching, and feedback on every Q&A answer |

Nothing is scored while you speak. After each session one simple results page shows:
1. an overall score and a two-sentence summary;
2. **four pillars**: Voice & delivery · Language & clarity · Body language · Confidence & presence (tap one for its metrics and comfortable ranges);
3. feedback on **what you said**;
4. **three drills**, each with the measured evidence and a target for next time.

---

## 🌟 What makes it different

1. **Accent-fair.** Malaysian-English pronunciation counts as regional variation, not error. Manglish particles (*lah, kan*) aren't counted as filler words. Speech recognition uses Mesolitica's Malaysian Whisper (6.1% WER on our benchmark, vs 51.3% for standard Whisper).
2. **Curated, not generic.**
   - Interview questions come from your role and resume.
   - Q&A questions come from your slides.
   - The AI follows a question plan enforced in code, so even a small local model can't drift off topic.
3. **Grounded feedback.**
   - Every recommendation cites what was measured.
   - Rewritten "stronger answers" are fact-checked against what you actually said.
   - Anything that couldn't be measured is listed as such, never estimated.
4. **Never interrupts.** All feedback comes after you finish (Cognitive Load Theory).
5. **Gaze Tunneling.** The correlation between looking away and stumbling: "you look away right when you lose your words".
6. **Local and private.** Everything runs on your machine (Ollama, faster-whisper, Kokoro, MediaPipe). Cloud APIs are optional.

The full list of AI functions, metrics, formulas and evaluation targets is in **[`docs/AI_MATRIX.md`](docs/AI_MATRIX.md)**. It is also in the app under **How it's measured**.

---

## 🧭 Using the app

| Page | What it's for |
|---|---|
| **Home** | The three functions, your next focus and recent sessions |
| **Conversation** (`/conversation`) | Choose a scenario (small talk, your week, studies & work, an opinion…) or your own topic → start |
| **Interview** (`/interview`) | Fill in the role and your background, upload a resume, preview the curated questions → start |
| **Presentation** (`/presentations`) | Upload a deck → insights → example video → rehearse (whole deck or one slide) → **Start Q&A rehearsal** |
| **Session** (`/session`) | A large camera view of yourself, a small MediaPipe tracking view, lighting advice and the AI partner's voice |
| **Results** (`/results/<id>`) | The simple four-pillar report for one session (opens automatically, or from the bell) |
| **Progress** (`/progress`) | Every session, the overall trend and a trend per pillar, filtered by function |
| **How it's measured** (`/methodology`) | The reference matrix: metrics, AI functions, evaluation |
| Bell (top left) | Notifications when an analysis, example video or rehearsal feedback is ready |
| Settings | Light / dark / system theme, profile |

---

## 🏗️ Architecture

```
SpeechMate/
├── frontend/             Next.js 16 web app
├── backend/              FastAPI API + AI pipelines (see backend/README.md for the full API)
├── docs/                 AI matrix, benchmarks, sample deck, interim report and paper
├── docker-compose.yml    Postgres + backend + frontend (+ Ollama, Kokoro)
└── start.sh              one-command start
```

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Zustand. MediaPipe Tasks Vision runs in the browser for live face and pose tracking.
- **Backend:** FastAPI, async SQLAlchemy and Alembic on PostgreSQL, JWT auth. Analyses and video generation run as background jobs; the results page polls them, and the bell notifies you when they finish.
- **AI** (all local by default):

| Job | Model |
|---|---|
| Text: partner, plans, insights, feedback | Ollama `qwen2.5:3b` |
| Vision: slide scripts | Ollama `qwen2.5vl:3b` |
| Speech recognition | Mesolitica Malaysian Whisper large-v3-turbo (faster-whisper, auto language) + `wav2vec2-xls-r-300m-mixed` for code-switching |
| AI partner's voice | Kokoro-82M |
| Narration | Mesolitica Malaysian-TTS-0.6B-v1 |
| Pronunciation | Wav2Vec2 |
| Pitch and volume | librosa |
| Eye contact, posture, gestures | MediaPipe |
| Facial expression | ViT |

### How a session is analysed

```
recording → 16 kHz audio → speech recognition → language mix & Manglish particles
  → fluency · pace · fillers (in context) · repetitions/blocks · pronunciation · pitch · volume · vocabulary · hedging
  → sampled video frames → eye contact · posture · gestures · head steadiness · expression
  → + response time and Gaze Tunneling from the browser
  → confidence → overall score → four pillars
  → answer feedback against the question plan (interview / Q&A) or language tips (conversation)
  → three evidence-based drills → progress history → notification
```

---

## 🚀 Getting started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Docker Compose.
- **WSL 2:** if `docker` says *"could not be found in this WSL 2 distro"*, open Docker Desktop → Settings → Resources → **WSL Integration**, enable your distro, then restart the terminal.

### 1. Configure

`start.sh` creates `backend/.env` from `backend/.env.example` if it doesn't exist. The important settings:

| Variable | Why |
|---|---|
| `SECRET_KEY` | Signs login tokens. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `LLM_BASE_URL`, `LLM_MODEL`, `VLM_MODEL` | The local LLM. `http://ollama:11434/v1` runs the bundled Ollama and downloads the models. `http://host.docker.internal:11434/v1` uses your own Ollama |
| `TTS_BASE_URL`, `LOCAL_TTS_VOICE` | The AI partner's voice. `http://kokoro:8880/v1` runs the bundled Kokoro; voices include `af_heart`, `am_michael`, `bf_emma` |
| `WHISPER_MODEL_SIZE`, `WHISPER_CPU_THREADS` | Speech recognition: the converted Malaysian Whisper path (`backend/scripts/convert_whisper.sh`) and CPU threads (8 was fastest) |
| `STT_LANGUAGE` | Empty = auto-detect (recommended); `ms` / `en` forces a language |
| `MALAYSIAN_TTS_VOICE` | Default narrator voice (`husein`, `idayu`, …); can also be chosen per deck |
| `OPENAI_API_KEY` | *Optional:* cloud LLM, TTS and Whisper |
| `ELEVENLABS_API_KEY` | *Optional:* narrate the example in **your own cloned voice** |

**Model size vs. RAM:** `qwen2.5:3b` and `qwen2.5vl:3b` fit an 8 GB machine. With 16 GB or more, the `7b` models give noticeably better questions and feedback. On WSL, give Docker more memory in `%UserProfile%\.wslconfig` (`[wsl2]` → `memory=12GB`). An NVIDIA GPU makes everything much faster: uncomment the GPU block in `docker-compose.yml`.

### 2. Start

```bash
./start.sh                     # or: docker compose --profile ollama --profile tts up --build -d
```

| | |
|---|---|
| App | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Health | http://localhost:8000/health (which models and providers are active) |

The first build takes a while. Model weights download on first use and are cached in Docker volumes:
- speech/vision models: about 2.5 GB;
- Malaysian TTS: about 2.5 GB;
- Ollama models: about 5 GB, in the background (`docker compose logs -f ollama-pull`).

Database migrations run automatically.

**Try it:** sign in as `demo@speechmate.dev` / `Demo1234!`. Step-by-step test guides and a glossary are in [`TESTING.md`](TESTING.md).

### Typical timings on CPU (8 GB laptop, no GPU)

| Step | Time |
|---|---|
| Interview question plan | ~30–60 s |
| Q&A plan from a deck | ~25 s |
| Deck insights | ~35 s |
| AI partner reply (text + voice) | ~2–5 s |
| Session analysis (2–5 min recording) | ~1–3 min |
| Example narration | a few minutes per slide |

### Useful commands

```bash
docker compose logs -f backend                               # follow backend logs
docker compose --profile ollama --profile tts down           # stop (data kept in Docker volumes)
docker compose --profile ollama --profile tts down -v        # stop and delete all data and cached models
```

---

## 🛠️ Development without Docker

**Backend.** Needs Python 3.11+, Postgres, ffmpeg, LibreOffice, poppler and espeak-ng. See [`backend/README.md`](backend/README.md).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt          # + requirements-ml.txt for local models
docker compose up -d db                      # or your own Postgres (set DATABASE_URL)
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend.**

```bash
cd frontend && npm install && npm run dev     # http://localhost:3000
```

The frontend calls `http://localhost:8000/api` by default. Set `NEXT_PUBLIC_API_URL` to point it elsewhere.

### Tests

```bash
cd backend && pytest              # 57 tests, SQLite, fully offline (every AI stage's fallback path)
cd frontend && npx tsc --noEmit && npm run lint
```

---

## 📊 Data & storage

- **PostgreSQL** tables:
  - `users`;
  - `live_sessions`: Conversation / Interview / Presentation Q&A, with their setup and question plan (`context`), transcript turns (`turns`), browser metrics and analysis;
  - `progress_records`, `reports`, `notifications`;
  - presentation decks: `sessions`, `slides`, `practice_sessions`, `chat_messages`.
- **Files** (decks, slide images, narration, videos, recordings) live under `STORAGE_BASE_PATH` (the `storage_data` volume).
- **Resumes:** only the extracted text is kept, inside the interview session that used it. Deleting the session deletes it.

---

## 📚 Documentation

- [`docs/AI_MATRIX.md`](docs/AI_MATRIX.md): every AI function and metric, with formulas, fallbacks and evaluation
- [`TESTING.md`](TESTING.md): demo accounts, how to test each function, glossary
- [`backend/README.md`](backend/README.md): full API reference and pipelines
- [`docs/benchmarks/`](docs/benchmarks/): speech-recognition benchmarks
- [`PROJECT.md`](PROJECT.md): project overview · [`TECHNICAL.md`](TECHNICAL.md): theory and evaluation protocol · [`TODO.md`](TODO.md): roadmap

## ⚠️ Current limitations

- **Stuttering** detection is a signal-processing heuristic. The trained CNN + BiLSTM classifier in `TECHNICAL.md` needs a labelled dataset (SEP-28k / UCLASS).
- **Pronunciation** uses Wav2Vec2 CTC confidence, not phoneme-level forced alignment (GOP).
- The **English/Malay ratio** uses a lexicon of about 190 BM/Manglish words, not a trained language-ID model.
- **Gestures** need your hands in view. At a desk the score is capped, not penalised.
- With the default **3B** local model, plans and feedback are good but less nuanced than with a 7B+ or cloud model. See `docs/AI_MATRIX.md` §4.
- The vision metrics have been verified on synthetic video only. They need real webcam recordings for the accuracy evaluation.
