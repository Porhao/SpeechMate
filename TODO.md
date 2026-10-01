# SpeechMate TODO / Roadmap

This document tracks the action items for Phases 5–8 of the SpeechMate project, as defined in the Interim Report and IEEE paper, and what has been built so far.

**Scope (2026-10-01):** SpeechMate does three things:
1. **Daily conversation**;
2. **Mock interview** (questions curated from the role, background and resume);
3. **Presentation practice** (deck insights → rehearsal → Q&A from the deck).

The separate Pronunciation mode, general AI Coach chat, Dashboard and Reports pages were removed. Pronunciation remains a metric in every session. Every AI function is listed in [`docs/AI_MATRIX.md`](docs/AI_MATRIX.md).

Legend: `[x]` done · `[~]` partly done (the note says what's left) · `[ ]` not started

---

## AI layer: cloud vs. local

SpeechMate is **local-first**: every stage has a local option, and cloud APIs are optional extras. Every stage also has an offline fallback, so the app runs with no keys and no local models. Check `GET /health` to see what's active: `local_ml` lists the local models, `providers` the cloud APIs.

**Live practice session analysis:**

| Stage | Local model (`backend/requirements-ml.txt`) | Cloud (`OPENAI_API_KEY`) | Neither available |
|---|---|---|---|
| Speech recognition | ✅ **Primary**: Mesolitica **Malaysian Whisper large-v3-turbo** via faster-whisper (CPU int8, auto language detection), also for each live turn (`/api/stt`, ~2.5 s per 5 s turn) | Fallback: OpenAI Whisper API | no transcript (conversation: browser recogniser) |
| Malay / code-switched ASR | ✅ Mesolitica `wav2vec2-xls-r-300m-mixed` | — | Whisper transcript kept, with a warning |
| Pronunciation | ✅ Wav2Vec2 `facebook/wav2vec2-base-960h` | — | shown as unavailable |
| Stutter prolongations | ✅ librosa energy analysis | — | transcript-only hint |
| Eye contact, posture | ✅ MediaPipe Face Mesh / Pose | — | shown as unavailable |
| Facial emotion | ✅ ViT `trpakov/vit-face-expression` | — | shown as unavailable |
| Pitch variation, loudness | ✅ librosa (YIN + RMS) | — | shown as unavailable |
| Gestures, head steadiness | ✅ MediaPipe Pose | — | shown as unavailable |
| Fluency, pauses, fillers (in context), vocabulary, hedging, language ratio, pillars, recommendations | ✅ plain code (ffmpeg + rules, no model) | — | always runs |
| AI conversation partner | ✅ Ollama `qwen2.5` | `gpt-4o-mini` | scripted prompts |
| Interview question plan (role + resume) / Q&A plan (deck) | ✅ Ollama `qwen2.5` (validated JSON) | `gpt-4o-mini` | question bank / deck insights |
| Interviewer & moderator turns | ✅ plan enforced in code + `qwen2.5` one-line reactions | `gpt-4o-mini` | fixed reactions |
| Answer feedback (interview, Q&A) & language tips (conversation) | ✅ Ollama `qwen2.5`, fact-checked | `gpt-4o-mini` | rule-based (STAR cues, specificity) |
| Partner's voice | ✅ **Kokoro-82M** (natural, ~3.5× faster than real time on CPU); Malaysian TTS on a GPU | OpenAI TTS | browser speech synthesis |

**Presentation coaching:**

| Stage | Local model | Cloud (`OPENAI_API_KEY`) | Neither available |
|---|---|---|---|
| Slide scripts | ✅ Ollama `qwen2.5vl` (vision) | `gpt-4o-mini` | template script built from the slide text |
| Narration voice | ✅ **Mesolitica `Malaysian-TTS-0.6B-v1`** (7 voices, Malay/English/code-switching) | OpenAI TTS; ElevenLabs *only* to clone your own voice | espeak-ng → silence |
| Practice transcription | ✅ faster-whisper | OpenAI Whisper API | skipped |
| OIS feedback, audience reaction, chat | ✅ Ollama `qwen2.5` | `gpt-4o-mini` | rule-based |

**Current setup:** fully local, with no cloud keys.
- `backend/.env` points the LLM at the bundled Ollama (`qwen2.5:3b` text, `qwen2.5vl:3b` vision).
- The Docker image installs the speech, vision and TTS models (`INSTALL_ML=true`).
- The live partner's voice is Kokoro (`TTS_BASE_URL`). Nothing depends on a cloud service.

**Planned vs. built:** the design documents name **Gemini Flash** as the LLM. The code talks to any OpenAI-compatible server, currently local **Qwen2.5 / Qwen2.5-VL on Ollama** (the same model family the PresentCoach paper uses); Gemini, OpenAI or DashScope work by changing `LLM_BASE_URL` / `LLM_MODEL`.

---

## Phase 5: Data Collection & AI Model Training
*Status: Underway. Everything runs on pretrained models; nothing has been trained yet.*

- [ ] **Data Collection & Preparation**
  - Collect local Malaysian English and code-switched (Manglish) speech/video samples from consenting volunteers across casual, mock interview, and presentation scenarios.
  - Generate synthetic disfluent data by injecting controlled stutters into standard Malaysian-accented reading transcripts using a Stutter-TTS approach to augment the training set.
  - Conduct a lightweight manual annotation pass to mark filler words, repetitions, and prolonged pauses, cross-checking with automated Whisper transcripts.
- [~] **Model Development & Refinement**
  - [~] Stuttering/disfluency detection. *Done:* a signal-processing heuristic (repetitions from the transcript, mid-utterance blocks from silence detection, energy-based prolongations with librosa) in `backend/app/services/live/speech.py`. *Left:* train the CNN + BiLSTM + attention classifier on UCLASS, SEP-28K and locally augmented data, and plug it in where the heuristic runs.
  - [~] Accent-fair pronunciation. *Done:* Wav2Vec2 CTC-confidence scoring over proportional word spans, plus a +5% Malaysian-English allowance (`pronunciation.py`, `language.py`). *Left:* real GOP forced-alignment scoring with relaxed thresholds, and splitting deviations into "regional" vs. "intelligibility" (the assessment page's `pronunciation_flags` still shows sample data).
  - [~] Gaze tracking. *Done:* MediaPipe iris-based gaze classification (camera / left / right / down) on the backend, and live face and pose tracking in the browser. *Left:* map it to the tri-zone (left / right / slide) distribution metric.
  - [x] Code-switching ASR routing: faster-whisper, re-run through Mesolitica's mixed-language model when the speech isn't confidently English, plus a Bahasa Malaysia / Manglish lexicon for the language ratio and particle detection.
- [~] **Initial Benchmarking**
  - [x] ASR baseline (`docs/benchmarks/stt-benchmark-2026-09-30.md`): Whisper medium vs. Mesolitica Malaysian Whisper small-v3 / large-v3-turbo-v3 on FLEURS Malay (real speakers) + Malaysian-accented English and Manglish. Turbo-v3 won with 7.9% WER overall (vs 51.3% for the previous medium setup) and is now the default.
  - [x] Language token (`docs/benchmarks/stt-benchmark-2026-10-01.md`): forcing `ms` translated US/UK-accented English answers into Malay. Auto-detect fixed it and improved real Malay to 6.4% WER (6.1% overall), so it is now the default.
  - [ ] Re-run on a held-out set of real recordings from the app's own users, WER split by pure Malay / pure English / mixed.
  - [ ] Precision, Recall and F1 for stutter and filler detection against manual annotations.

## Phase 6: Front-End and Back-End Development
*Status: Mostly done*

- [~] **Front-End (Next.js / Tailwind CSS)**
  - [x] User management: register, login (with automatic token refresh), and a profile page that saves to the backend.
  - [x] Onboarding saves the goal, level and challenges to the profile and opens the chosen function.
  - [x] **Three functions**: Conversation (`/conversation`, topic scenarios), Mock interview (`/interview`, setup + resume + question preview), Presentation practice (`/presentations`, insights → rehearsal → Q&A rehearsal).
  - [x] **Session screen** follows *Deferred Feedback*: no live scores (removed the score bars), only the timer, the question count and lighting advice.
  - [x] **Presentation Coach**: upload a deck → insights → AI example video → practise the whole deck or one slide → Observation / Impact / Suggestion feedback, **key point per slide**, audience reaction and a follow-up chat.
  - [x] **Results page** (`/results/[id]`): overall score, four pillars with metric details, answer feedback / language tips, three drills, and notes on anything not measured. Analysis progress is shown live.
  - [x] **Progress page**: real history, overall trend and a trend per pillar, filter by function (sample-data Dashboard and Reports pages removed).
  - [ ] PDF export of a results page.
- [x] **Back-End (FastAPI)**
  - [x] Core API routes: `auth`, `users/profile`, `live` (practice sessions + recording + analysis), `progress`, `reports`, `chat` (AI partner), `coach`, `tts`, plus `sessions` / `practice` for presentation coaching.
  - [x] Background processing for heavy analysis: in-process asyncio jobs with a concurrency limit and restart recovery, polled by the frontend, instead of Celery. Revisit Celery / arq if several servers are ever needed.
  - [x] PostgreSQL with Alembic migrations; Docker Compose runs the whole stack (`./start.sh`).
- [~] **Integration**
  - [x] Frontend services and Zustand stores wired to the backend (`services/api.ts`, `auth.ts`, `live.ts`, `presentation.ts`).
  - [x] Presentation decks belong to the user who uploaded them.

## Phase 7: System Integration & Unit Testing
*Status: Underway*

- [~] **Pipeline Integration**
  - [x] Unified multimodal pipeline for live sessions (`backend/app/services/live/pipeline.py`): ASR → language → fluency / fillers / stuttering / pronunciation → eye contact / posture / emotion → confidence → communication score → recommendations → progress history.
  - [x] **Gaze Tunneling**: the Pearson correlation between gaze aversion and disfluency events, computed in the browser from the live session's own samples.
  - [x] LLM feedback on live sessions: an evidence-grounded coaching plan (the LLM may only choose measured issues), per-answer interview / Q&A feedback with a fact check, and conversation language tips. Gaze Tunneling and response time are sent to the backend with the session.
- [~] **Testing & QA**
  - [x] Backend: 57 automated tests (unit + end-to-end), fully offline: auth, live-session analysis, metrics, pillars, fillers in context, interview/Q&A plans, plan-following partner, answer feedback and fact check, resume reading, presentation pipeline, notifications.
  - [x] Full-pipeline check with real models: synthesised spoken answers → upload → analysis (~80–110 s on CPU) → pillars + LLM answer feedback.
  - [ ] Frontend tests (none yet; type-check and lint only).
  - [ ] Test the vision stages with real webcam recordings (so far only verified on synthetic video with no face in it).
  - [ ] Internal User Acceptance Testing (UAT) with the planned questionnaire: does the system reduce speaking anxiety and deliver actionable feedback?

## Phase 8: Validation, Evaluation & Final Deployment
*Status: Planned*

- [ ] **Technical Validation**
  - Run the full technical evaluation with the pre-registered framework (e.g., WER reduction vs. baseline, pronunciation correlation ≥ 0.7, disfluency F1 ≥ 0.75, gaze accuracy ≥ 0.8).
  - Compare the qualitative UAT findings with the objectives from Cognitive Load Theory (do users feel more prepared and less interrupted?).
- [ ] **Final Tuning & Deployment**
  - Adjust parameters and fix issues based on the evaluation results (e.g., pronunciation scoring inconsistencies).
  - [x] Documentation: README, backend README and PROJECT.md match the code; TESTING.md has demo accounts, a test guide and a glossary.
  - [x] Local-first AI: Ollama for LLM + vision, local Malaysian TTS for narration, demo accounts seeded for testing.
  - [x] UI: single plain top bar (Home · Conversation · Interview · Presentation · Progress · How it's measured), near-square corners; dark mode with WCAG AA contrast; notifications; reference matrix with an AI-functions tab; real stats only (no invented numbers).
  - [x] Live sessions: large clean camera view and a separate MediaPipe tracking inset; lighting & contrast advice.
  - [x] Recommendations grounded in measured evidence with drills and relative targets (LLM picks/words them, can't invent issues).
  - [x] Presentation decks: .pptx or .pdf, and deck insights (summary, structure, key points, suggestions) before narration.
  - [x] Progress uses real data (sample-data pages removed).
  - [ ] Collect 30–50 consenting user recordings to measure real-user WER, filler F1, pronunciation correlation and gaze accuracy (`docs/AI_MATRIX.md` §3).
  - [ ] Deploy the prototype: set a real `SECRET_KEY`, add API keys, and pick a host with enough RAM/CPU for the local models.
  - Compile the final project report summarizing the quantitative results and user acceptance findings.
