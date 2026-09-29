# SpeechMate TODO / Roadmap

This document tracks the action items for Phases 5–8 of the SpeechMate project, as defined in the Interim Report and IEEE paper, and what has been built so far.

Legend: `[x]` done · `[~]` partly done (the note says what's left) · `[ ]` not started

---

## AI layer: cloud vs. local

Each AI stage uses a **local model** or a **cloud API** (or both, with one as a fallback). Every stage also has an offline fallback, so the app runs with no keys and no local models. Check `GET /health` to see what's active: `local_ml` lists the local models, `providers` the cloud APIs.

**Live practice session analysis:**

| Stage | Local model (`backend/requirements-ml.txt`) | Cloud (`OPENAI_API_KEY`) | Neither available |
|---|---|---|---|
| Speech recognition | ✅ **Primary**: faster-whisper `small` (CPU int8) | Fallback: OpenAI Whisper API | no transcript; word-level metrics skipped |
| Malay / code-switched ASR | ✅ Mesolitica `wav2vec2-xls-r-300m-mixed` | — | Whisper transcript kept, with a warning |
| Pronunciation | ✅ Wav2Vec2 `facebook/wav2vec2-base-960h` | — | shown as unavailable |
| Stutter prolongations | ✅ librosa energy analysis | — | transcript-only hint |
| Eye contact, posture | ✅ MediaPipe Face Mesh / Pose | — | shown as unavailable |
| Facial emotion | ✅ ViT `trpakov/vit-face-expression` | — | shown as unavailable |
| Fluency, pauses, fillers, language ratio, scoring, recommendations | ✅ plain code (ffmpeg + rules, no model) | — | always runs |
| AI conversation partner | — | ✅ `gpt-4o-mini` | scripted prompts |
| Partner's voice | — | ✅ OpenAI TTS | browser speech synthesis |
| General AI coach chat | — | ✅ `gpt-4o-mini` | unavailable (`503`) |

**Presentation coaching:**

| Stage | Local model | Cloud (`OPENAI_API_KEY`) | Neither available |
|---|---|---|---|
| Slide scripts | — | ✅ `gpt-4o-mini` vision-language model | template script built from the slide text |
| Narration voice | espeak-ng (fallback) | ✅ ElevenLabs voice clone → OpenAI TTS | silence |
| Practice transcription | — | ✅ OpenAI Whisper API | skipped |
| OIS feedback, audience reaction, chat | — | ✅ `gpt-4o-mini` | rule-based |

**Current setup:** the Docker image installs the local models (`INSTALL_ML=true`), and no `OPENAI_API_KEY` or `ELEVENLABS_API_KEY` is set. In practice:

- The **live-session analysis runs fully locally.**
- The live-session **conversation partner and coach chat**, and **all of presentation coaching**, are running on their offline fallbacks until a key is added.

**Planned vs. built:** the design documents name **Gemini Flash** as the LLM. The code uses **OpenAI `gpt-4o-mini`** through an OpenAI-compatible client. Setting `OPENAI_BASE_URL` points it at Gemini's OpenAI-compatible endpoint, Qwen/DashScope, or a local server (e.g. Ollama) without code changes.

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
- [ ] **Initial Benchmarking**
  - Record initial baseline metrics for Word Error Rate (WER), Precision, Recall, and F1 scores against the evaluation framework. The ASR router can already produce both the Whisper-only and the code-switched transcript to compare.

## Phase 6: Front-End and Back-End Development
*Status: Mostly done*

- [~] **Front-End (Next.js / Tailwind CSS)**
  - [x] User management: register, login (with automatic token refresh), and a profile page that saves to the backend.
  - [~] Onboarding. *Left:* the answers are only stored in the browser; send them to `PUT /api/users/profile`.
  - [x] **Practice Session Interface**: Conversation / Interview / Pronunciation modes with an AI partner (voice), live face, pose and speech tracking in the browser, recording, and upload for analysis.
  - [ ] Audit the session screen against the *Deferred Feedback* design: a silent elapsed timer, with no on-screen scores, warnings or live metrics while speaking.
  - [x] **Presentation Coach** (`/presentations`): upload a deck → AI example video in your cloned voice → practise the whole deck or one slide → Observation / Impact / Suggestion feedback, audience reaction and a follow-up chat.
  - [x] **Assessment page**: post-session results from the real analysis, with a notice listing any metric that couldn't be measured.
  - [~] **Performance Dashboard**. *Left:* the Dashboard, Progress and Reports pages still show sample data. Wire them to `GET /api/progress` and `/api/reports`, draw the radar chart against the previous session, and add PDF export.
- [x] **Back-End (FastAPI)**
  - [x] Core API routes: `auth`, `users/profile`, `live` (practice sessions + recording + analysis), `progress`, `reports`, `chat` (AI partner), `coach`, `tts`, plus `sessions` / `practice` for presentation coaching.
  - [x] Background processing for heavy analysis: in-process asyncio jobs with a concurrency limit and restart recovery, polled by the frontend, instead of Celery. Revisit Celery / arq if several servers are ever needed.
  - [x] PostgreSQL with Alembic migrations; Docker Compose runs the whole stack (`./start.sh`).
- [~] **Integration**
  - [x] Frontend services and Zustand stores wired to the backend (`services/api.ts`, `auth.ts`, `live.ts`, `presentation.ts`).
  - [ ] Tie presentation decks to user accounts; right now everyone using the app sees every deck.

## Phase 7: System Integration & Unit Testing
*Status: Underway*

- [~] **Pipeline Integration**
  - [x] Unified multimodal pipeline for live sessions (`backend/app/services/live/pipeline.py`): ASR → language → fluency / fillers / stuttering / pronunciation → eye contact / posture / emotion → confidence → communication score → recommendations → progress history.
  - [x] **Gaze Tunneling**: the Pearson correlation between gaze aversion and disfluency events, computed in the browser from the live session's own samples.
  - [~] LLM feedback on live sessions. *Done:* the LLM powers presentation-coaching feedback (OIS format, validated and re-prompted), the live AI partner and the general coach (which reads the user's recent results). *Left:* live-session recommendations are still rule-based; send the analysis to the LLM for concrete, moment-anchored feedback, and move Gaze Tunneling to the backend so the LLM can use it.
- [~] **Testing & QA**
  - [x] Backend: 27 automated tests (unit + end-to-end), fully offline: auth, live-session analysis, metrics, scoring, presentation pipeline and coach.
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
  - [x] Documentation: README, backend README and PROJECT.md match the code.
  - [ ] Deploy the prototype: set a real `SECRET_KEY`, add API keys, and pick a host with enough RAM/CPU for the local models.
  - Compile the final project report summarizing the quantitative results and user acceptance findings.
