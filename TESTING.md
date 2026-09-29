# Testing SpeechMate

How to try every feature by hand, the demo accounts to do it with, and a glossary of the terms you'll see in the app and the API.

---

## 1. Start the app

```bash
./start.sh
```

| | |
|---|---|
| App | http://localhost:3000 |
| API docs (try any endpoint in the browser) | http://localhost:8000/docs |
| Health (what's active) | http://localhost:8000/health |

The first start downloads a lot: Docker images, the local speech/vision models (on first analysis), the Malaysian TTS model (on first deck), and the Ollama LLMs (in the background; follow with `docker compose logs -f ollama-pull`). Until an LLM has finished downloading, the features that need it use their offline fallbacks.

---

## 2. Test accounts

Created automatically at startup when `SEED_DEMO_DATA=true`, which the root `docker-compose.yml` sets by default. Existing accounts are never overwritten.

| Email | Password | Use it to test |
|---|---|---|
| `demo@speechmate.dev` | `Demo1234!` | **Aisyah Rahman**: profile filled in (goal *Improve Presentations*, *Intermediate*, challenges Eye Contact / Speaking Pace / Confidence) and **3 example live sessions** over the last two weeks with improving scores (64.6 → 71.3 → 79.8), so progress, reports and the history-aware AI coach have data |
| `new@speechmate.dev` | `Demo1234!` | **Farid Hakim**: an empty account, for first-time flows (onboarding, first session, empty states) |

- The demo sessions are marked *"Demo data created by scripts/seed_demo.py — not a real recording."* in their warnings.
- To re-create the accounts from scratch, run `docker compose down -v`, which **deletes all data**, then `./start.sh`.
- To add them to an existing database without restarting, run `docker compose exec backend python scripts/seed_demo.py --force`.
- Turn seeding off for a real deployment: `SEED_DEMO_DATA=false`.

**Sample deck:** `docs/samples/sample_deck.pptx` (3 slides on time management).

---

## 3. What to test

### A. Accounts & profile
1. **Sign in** at `/login` with `demo@speechmate.dev` / `Demo1234!` → you land on the dashboard.
2. **Profile** (`/profile`): change the skill level or challenges → *Save Changes* → reload the page. The changes are stored on the server.
3. **Register** a new account at `/register`. Passwords need at least 8 characters, and using an email that already exists shows an error.

### B. Live practice session + analysis
1. **Start a session:** Home or `/practice` → **Conversation** (or Interview / Pronunciation) → allow the camera and microphone.
2. **Talk** with the AI partner for about a minute. Its replies come from the local LLM (Ollama); if no LLM is ready, you get scripted prompts instead.
3. **End the session** → wait on "Analysing…". The recording is uploaded and analysed on the server, which takes about 20 seconds to a few minutes on CPU.
4. **Check `/assessment`:**
   - transcript
   - fluency, pace, fillers (English + Malay), stuttering
   - pronunciation
   - English/Malay ratio and Manglish particles
   - eye contact, posture, emotion
   - confidence, the overall score and recommended exercises

   Any metric that couldn't be measured is listed in the notice at the top.
5. **Try Malay / Manglish:** say something like *"Actually I think the project is good lah, tapi kita perlu more time."* The language card should show code-switching and the particle *lah*.
6. **Signed out**, a session still runs, but the assessment page says *"Sign in to have your session recorded and analysed."*

### C. Presentation Coach
1. Go to `/presentations` → upload `docs/samples/sample_deck.pptx`.
2. Pick a **narrator voice** (Malaysian TTS: Husein, Idayu, …) and, optionally, an audience, e.g. *"First-year students, 5-minute talk"*.
3. **Generate** → watch the four steps: parsing slides → writing scripts (local vision model) → synthesizing audio (Malaysian TTS) → assembling the video. On CPU the narration takes a few minutes per slide.
4. **Watch the example video.** The script panel highlights the slide being narrated, and clicking a slide's script jumps the video there.
5. **Practise:** record the **whole deck**, or choose **One slide** (you can play that slide's example narration first) → *Get feedback*.
6. **Check the feedback:**
   - encouragement
   - Observation → Impact → Suggestion cards
   - delivery metrics
   - the simulated audience's reaction
   - the transcript
7. **Chat:** *"What should I fix first?"* A second attempt lets you ask *"Am I improving?"*; the coach compares against your earlier attempts.
8. **Retry / Regenerate / Delete** a deck from its page or the list.

### D. AI Coach (`/coach`)
1. **General coaching** (signed in as the demo account): *"Based on my recent sessions, what should I focus on this week?"* The answer should mention Aisyah's goal and recent scores.
2. **Presentation attempts:** pick an attempt from the list → the chat and its feedback appear side by side.

### E. Progress & reports (API; the pages still show sample data)
In http://localhost:8000/docs:

1. `POST /api/auth/login` with the demo account → copy the `access_token`.
2. Click **Authorize** (top right) → paste the token.
3. Call these:
   - `GET /api/progress`: 18 points (6 metrics × 3 sessions)
   - `POST /api/reports/generate`: averages, first → latest change and best score per metric
   - `GET /api/live`: the 3 demo sessions with their full analysis

### F. Health & fallbacks
- http://localhost:8000/health shows which local models are installed (`local_ml`), where LLM calls go (`llm`), and which cloud keys are set (`providers`).
- Stop Ollama (`docker compose stop ollama`) and chat again. The coach should return a clear "No LLM configured / unavailable" message instead of crashing.

### Automated tests
```bash
docker compose exec backend sh -c "pip install -r requirements-dev.txt && pytest"   # backend
cd frontend && npx tsc --noEmit && npm run lint                                    # frontend
```

---

## 4. Glossary

| Term | Meaning |
|---|---|
| **Accent-fair scoring** | Malaysian-English pronunciation patterns (th → d/t, dropped final consonants, vowel shifts) count as regional variation, not errors: pronunciation gets a +5% allowance for Malaysian English. |
| **Articulation rate** | Words per minute *while actually speaking*, i.e. excluding pauses. Compare **speaking rate** (WPM). |
| **ASR** | Automatic Speech Recognition, turning speech into a transcript. SpeechMate uses faster-whisper, re-checked by a code-switching model. |
| **Audience reaction** | A simulated listener from your target audience rates clarity and engagement (1–5), and lists confusing moments and the questions they'd ask. |
| **Block** | A stuttering event: an unusually long silence (≥ 1.2 s) in the middle of speech. |
| **Code-switching / Manglish** | Mixing English and Bahasa Melayu in one sentence. *Manglish particles* are words like *lah, lor, meh, kan* that mark Malaysian English style. |
| **Code-switch model** | Mesolitica's `wav2vec2-xls-r-300m-mixed`, a speech recognizer trained on Malay/Singlish/mixed speech. It's used when Whisper isn't confident the speech is English. |
| **Communication score** | The overall 0–100 score: a weighted blend of fluency 25%, pronunciation 25%, confidence 20%, eye contact 15% and posture 15%, re-weighted over whichever of these were actually measured (`scored_on`). |
| **Confidence** | Estimated from speech (pace, pauses, fluency, 40%), face (expression, tension, 35%) and body (posture, stability, 25%). |
| **Deferred feedback** | No scores or corrections appear while you're speaking; everything comes after the session, to reduce cognitive load and anxiety. |
| **Fallback** | What a stage does when its model or key isn't available (e.g. template scripts, espeak voice, rule-based feedback). Always recorded in `warnings`, never silent. |
| **Filler words** | Words like *um, uh, like, you know, basically* in English and *err, macam, sebenarnya, lah* in Bahasa Melayu. Shown as a count and per minute. |
| **Gaze Tunneling** | The correlation between looking away and stumbling over words, computed from the live session's own samples: *"you look away right when you stumble"*. |
| **Ideal Presentation Agent** | The part that turns your `.pptx` into an example narrated video (the benchmark you practise against). |
| **Coach Agent** | The part that compares your practice recording with the ideal version and gives OIS feedback and chat. |
| **Key-term coverage** | The share of the example script's important words that you actually said. *Missed key terms* lists the ones you skipped. |
| **Live session** | A camera + mic practice session with the AI partner (Conversation, Interview, Pronunciation). |
| **Local ML** | Models that run on your own server (faster-whisper, Wav2Vec2, MediaPipe, the ViT emotion model, the Malaysian TTS). Installed from `requirements-ml.txt`. |
| **LLM / VLM** | Large language model (text: chat, feedback) / vision-language model (reads slide images to write scripts). Here: Ollama `qwen2.5` / `qwen2.5vl`. |
| **Malaysian TTS** | Mesolitica's open-source `Malaysian-TTS-0.6B-v1`, which narrates in Malay, English and code-switched speech with a choice of 7 voices. It doesn't clone your voice. |
| **Narrator voice** | The Malaysian TTS voice chosen for a deck's example video. |
| **OIS** | **Observation → Impact → Suggestion**: what happened, why it matters to the audience, and one concrete thing to do next time. |
| **Ollama** | The local LLM server that runs the text and vision models on your machine instead of a cloud API. |
| **Pause frequency** | How many pauses longer than 0.25 s occurred between words. |
| **Per-slide practice** | Recording just one slide and comparing it with that slide's example narration, instead of the whole deck. |
| **Progress record** | One metric value from one analysed session, the data points behind progress charts and reports. |
| **Prolongation** | A stuttering event: a sound held unusually long ("sssso"). |
| **Repetition** | A stuttering event: the same word said twice in a row ("I I think"). |
| **RTF (real-time factor)** | Processing time ÷ audio length. RTF 5× means 10 s of audio takes 50 s to generate. |
| **Seed / demo data** | The test accounts and example sessions created by `backend/scripts/seed_demo.py`. |
| **Speaking rate / WPM** | Words per minute over the whole recording. About 120–160 is comfortable for presenting. |
| **Stuttering score** | 0–100: 8 points per detected repetition, block or prolongation. Severity is None / Mild / Moderate / Severe. |
| **Voice cloning** | Narrating the deck in *your* voice from a recorded sample. Only available with an ElevenLabs key (optional). |
| **Warnings** | The list on every session, practice run or analysis that says which fallbacks were used or what couldn't be measured. |
