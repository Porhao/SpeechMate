# SpeechMate — Product Requirements

Status: living document · Owner: project author · Last updated: 2026-10-07

## 1. Problem

Malaysian students and fresh graduates practise speaking (daily English, job interviews, presentations) with no one to give honest, specific feedback. Generic speech tools are built for US/UK English: they mis-transcribe Manglish, punish a Malaysian accent and judge "confidence" from nothing they can explain.

## 2. Product

An AI speaking coach with **three practice functions**. You talk to an AI partner on camera; nothing interrupts you; afterwards you get a plain-language report on your voice, language, body language and confidence, with the one thing to practise next.

| Function | What happens | Feedback specific to it |
|---|---|---|
| **Daily conversation** | Pick a topic, chat naturally for 3–5 minutes | Language corrections ("You said / Try saying"), conversation tips |
| **Mock interview** | Enter role, level, background (+ resume); the AI interviewer follows a curated question plan | Per answer: answered the question? easy to follow (STAR)? real details? plus a stronger version using only your facts |
| **Presentation practice** | Upload .pptx/.pdf; the AI reads it (summary, each slide's key point). You present it on camera, moving through the slides yourself; then rehearse the Q&A from your deck | Per slide: did what you said match the slide (match 1–5, covered / left out / tip, time on screen); voice and body language; per-answer Q&A feedback |

Out of scope (removed 2026-10-01): pronunciation drills mode, general coach chat, dashboard, reports.

## 3. Users

- **Primary:** Malaysian university students and fresh graduates (B1–C1 English, code-switching with Bahasa Melayu).
- **Secondary:** lecturers/supervisors who review students' progress; the FYP examiner who evaluates the method.

## 4. Requirements

### Functional
| ID | Requirement |
|---|---|
| F1 | Sign up, sign in, profile (goal, level, challenges) used to pitch the AI partner and feedback |
| F2 | Live session: camera + mic, AI partner with voice, turn-taking that never cuts the user off (waits ~1.6 s of silence and while words are still being transcribed; "I'm done" to end a turn early) |
| F3 | Speech recognition tuned for Malaysian English and Manglish; the user can **Fix** a misheard message |
| F4 | Typed input whenever voice isn't available |
| F5 | Post-session analysis: transcript, voice, language, body language, confidence; four pillars; overall score |
| F6 | Every number explainable: the Reference page lists method, worked example and sources; the results page shows the confidence breakdown |
| F7 | Coaching: a #1 focus with evidence, a drill and a target; "Practise this now" starts a drill session |
| F8 | Progress over time per pillar and for the #1 focus |
| F9 | Interview question plan from role/resume; Q&A plan from the deck (prepared once, instant start) |
| F10 | Notifications when an analysis is ready or fails |

### Non-functional
| ID | Requirement | Target |
|---|---|---|
| N1 | Runs fully local (no cloud keys required) | Docker Compose: Postgres, FastAPI, Next.js, Ollama, Kokoro |
| N2 | Honesty | Nothing estimated: unmeasured metrics shown as unavailable; confidence needs ≥ 30% of its evidence |
| N3 | Analysis time | < 2 min for a 5-min session on the reference machine with ≥ 10 GB RAM for WSL |
| N4 | Accessibility | WCAG AA contrast in light and dark; keyboard shortcuts; large-text option; reduced motion respected |
| N5 | Privacy | Recordings stored per user, deletable; resume text kept only with its session (see Security.md) |

## 5. Success metrics

| Metric | Target |
|---|---|
| Transcription WER on Malaysian speech | Clearly below standard Whisper (achieved: 6.1% vs 51.3%) |
| Confidence score vs. human raters | Spearman ρ ≥ 0.5 (docs/confidence-model.md) |
| Feedback rated specific & actionable (UAT, 5-point Likert) | ≥ 4.0 |
| Users who complete a 2nd session within a week | ≥ 50% |

## 6. Open questions / next

- Real-speaker evaluation and fine-tune (fine-tune/OWN_DATA_GUIDE.md).
- Saving "Fix" corrections (with consent) as training data.
- Confidence-model validation study.
