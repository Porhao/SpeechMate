# SpeechMate TODO / Roadmap

This document tracks the action items for Phases 5–8 of the SpeechMate project, as defined in the Interim Report and IEEE paper, and what has been built so far.

**Scope (2026-10-01):** SpeechMate does three things:
1. **Daily conversation**;
2. **Mock interview** (questions curated from the role, background and resume);
3. **Presentation practice** (deck insights → rehearsal → Q&A from the deck).

The separate Pronunciation mode, general AI Coach chat, Dashboard and Reports pages were removed. Pronunciation remains a metric in every session. Every AI function is listed in [`docs/AI_MATRIX.md`](docs/AI_MATRIX.md).

Legend: `[x]` done · `[~]` partly done (the note says what's left) · `[ ]` not started

---

## AI layer (deployed: cloud configuration, 2026-10-16)

Every stage has an offline fallback, so the app runs with no keys and no local models. `GET /health` shows what's active: `local_ml` lists the local models, `llm` and `providers` the cloud APIs.

| Stage | Deployed | Without it |
|---|---|---|
| Speech recognition (sessions and each live turn) | Groq `whisper-large-v3` (auto language, verbatim Manglish prompt, word timestamps, silence filter, translation guard) | no transcript; the user types live turns |
| Pronunciation | phone-level GOP: `facebook/wav2vec2-xlsr-53-espeak-cv-ft` + forced alignment, Malaysian English features accepted | shown as unavailable |
| Stutter prolongations, pitch, loudness | librosa | transcript-only hint / unavailable |
| Eye contact, posture, gestures, head steadiness, Gaze Tunneling | MediaPipe Face Mesh / Pose (2 fps gaze stream) | shown as unavailable |
| Facial expression | ViT `trpakov/vit-face-expression` | shown as unavailable |
| Fluency, pauses, fillers (in context), vocabulary, hedging, language ratio, pillars, recommendations | plain code (ffmpeg + rules) | always runs |
| AI partner, interview / Q&A plans, answer feedback, deck insights, talk feedback | Gemini `gemini-3.5-flash-lite` (validated JSON; plans enforced in code) | question bank, fixed reactions, rule-based feedback, text outline |
| Partner's voice | Kokoro-82M in the browser (Kokoro server or OpenAI TTS as backup) | browser speech synthesis |

The example narration (Malaysian TTS, voice cloning), slide scripts and the upload-a-rehearsal coach were removed (2026-10-07 and 2026-10-16); a local LLM (Ollama) still works by setting `LLM_BASE_URL`.

---

## Phase 5: Data Collection & AI Model Training
*Status: Underway. The app runs on pretrained models. A first speech-recognition fine-tune exists (`fine-tune/`) but is not deployed.*

- [~] **Data Collection & Preparation**
  - *Done:* recording kit in `fine-tune/`: transcription style guide (`STYLE_GUIDE.md`, incl. disfluency marking for F1), session prompts (`RECORDING_PROMPTS.md`), English + Malay consent form (Claude Doc). Public training set (`scripts/prepare_public.py`: 10.3 h, Synth-Manglish + FLEURS, CC BY 4.0). *Left:* the recordings themselves.
  - Collect local Malaysian English and code-switched (Manglish) speech/video samples from consenting volunteers across casual, mock interview, and presentation scenarios.
  - Generate synthetic disfluent data by injecting controlled stutters into standard Malaysian-accented reading transcripts using a Stutter-TTS approach to augment the training set.
  - Conduct a lightweight manual annotation pass to mark filler words, repetitions, and prolonged pauses, cross-checking with automated Whisper transcripts.
- [~] **Model Development & Refinement**
  - [~] Stuttering/disfluency detection. *Done:* a signal-processing heuristic (repetitions from the transcript, mid-utterance blocks from silence detection, energy-based prolongations with librosa) in `backend/app/services/live/speech.py`. *Left:* train the CNN + BiLSTM + attention classifier on UCLASS, SEP-28K and locally augmented data, and plug it in where the heuristic runs.
  - [~] Accent-fair pronunciation. *Done:* Wav2Vec2 CTC-confidence scoring over proportional word spans, plus a +5% Malaysian-English allowance (`pronunciation.py`, `language.py`). *Left:* real GOP forced-alignment scoring with relaxed thresholds, and splitting deviations into "regional" vs. "intelligibility" (the assessment page's `pronunciation_flags` still shows sample data).
  - [~] Gaze tracking. *Done:* MediaPipe iris-based gaze classification (camera / left / right / down) on the backend, and live face and pose tracking in the browser. *Left:* map it to the tri-zone (left / right / slide) distribution metric.
  - [~] Code-switching ASR routing: faster-whisper, re-run through Mesolitica's mixed-language model when the speech isn't confidently English, plus a Bahasa Malaysia / Manglish lexicon for the language ratio and particle detection. *Fixed 2026-10-06:* the torch 2.4.1 pin made the mixed-language model fail to load, so routing silently fell back to Whisper (now torch 2.6.0; **rebuild the backend to apply**). *Measured:* routing detects mixed speech but doubles WER (15.4% → 36.7%). *Left:* drop or replace the second engine.
  - [~] Speech-recognition fine-tune (`fine-tune/`, plan in `fine-tune/docs/manglish-finetune-plan.md`): LoRA on Mesolitica turbo-v3 with 10.3 h public data. English 9.4% → 6.7%, mixed 14.5% → 6.7% WER, silence still empty. *Left:* go/no-go on real recordings (`bench_stt.py --real`), Mesolitica licence answer, then deploy via `WHISPER_MODEL_SIZE`.
- [~] **Initial Benchmarking**
  - [x] ASR baseline (`docs/benchmarks/stt-benchmark-2026-09-30.md`): Whisper medium vs. Mesolitica Malaysian Whisper small-v3 / large-v3-turbo-v3 on FLEURS Malay (real speakers) + Malaysian-accented English and Manglish. Turbo-v3 won with 7.9% WER overall (vs 51.3% for the previous medium setup) and is now the default.
  - [x] Language token (`docs/benchmarks/stt-benchmark-2026-10-01.md`): forcing `ms` translated US/UK-accented English answers into Malay. Auto-detect fixed it and improved real Malay to 6.4% WER (6.1% overall), so it is now the default.
  - [x] Routing and fine-tune evaluation on 400 public clips (`docs/benchmarks/stt-routing-and-finetune-2026-10-06.md`).
  - [ ] Re-run on a held-out set of real recordings from the app's own users, WER split by pure Malay / pure English / mixed (`bench_stt.py --real` is ready).
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
