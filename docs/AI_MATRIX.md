# SpeechMate AI matrix

This document covers every AI function and every metric in SpeechMate:
- which of the three practice functions uses it;
- the model or method behind it;
- what goes in and what comes out;
- what happens when the model isn't available;
- how its accuracy is (or will be) evaluated.

The app's **How it's measured** page (`/methodology`) shows the same information.

**The three functions**

| | Function | Where | What the AI does |
|---|---|---|---|
| **C** | Daily conversation | `/conversation` → `/session` | Chats about a chosen topic, then analyses voice, language, body language and confidence, with language tips |
| **I** | Mock interview | `/interview` → `/session` | Curates questions from the role, background, job description and resume; conducts the interview; judges every answer |
| **P** | Presentation practice | `/presentations/[id]` → `/session` | Reads and summarises the deck; you present it on camera and each slide is checked against what you said; runs a Q&A drawn from the deck and judges every answer |

**Configuration (deployed and evaluated):** speech-to-text on Groq `whisper-large-v3` and the LLM on Gemini `gemini-3.5-flash-lite`, both through OpenAI-compatible APIs. Partner voice (Kokoro), pronunciation, prosody and vision run on the server. A local LLM (Ollama `qwen2.5:3b`, used during development) works by changing `LLM_BASE_URL`.

---

## 1. AI functions

| # | AI function | Used in | Model / method | Input → output | If unavailable | How quality is checked | Code |
|---|---|---|---|---|---|---|---|
| 1 | Speech recognition (session analysis) | C I P | Groq **whisper-large-v3** (lossless FLAC upload, word + segment timestamps, verbatim Manglish prompt, auto language) + **silence filter** | 16 kHz audio → transcript + word timings | ffmpeg silence measures only; word metrics "not measured" | WER **4.9%** English, **7.3%** Malay (real speakers), **16.5%** synthetic Manglish; silence filter removes 10/10 invented outputs, keeps 10/10 speech clips (`docs/benchmarks/stt-groq-cloud-2026-10-15.md`) | `live/asr.py` |
| 2 | Speech recognition (each live turn) | C I P | same service, per spoken phrase (`/api/stt`) | one phrase → text (median 0.56 s) | typed input | same as 1 | `routers/conversation.py` |
| 3 | Code-switch routing (removed) | — | Whisper language confidence → Mesolitica `wav2vec2-xls-r-300m-mixed` | — | — | Evaluated and rejected: mixed WER 15.4% → 36.7% with routing on (`docs/benchmarks/stt-routing-and-finetune-2026-10-06.md`) | removed 2026-10-14 |
| 4 | Conversation partner | C | Gemini (LLM) | last 12 turns + topic → 2–3 spoken sentences | scripted prompts | UAT naturalness rating | `routers/conversation.py` |
| 5 | Interview question plan | I | Gemini, JSON validated (Pydantic) and re-prompted once | role, company, level, type, background, job description, resume text → 6–8 questions, each with *what it tests* and *what a strong answer contains* | question bank (behavioural / technical / mixed) | relevance rating by users/supervisor | `practice_plans.py` |
| 6 | Resume reading | I | `pdftotext` / DOCX XML / plain text | resume file → text (max 8,000 chars) | user types their background | — | `practice_plans.py` |
| 7 | Q&A question plan | P | Gemini, JSON validated | deck insights + audience → 5–6 audience questions tied to slides | likely questions + key points from the insights | relevance rating | `practice_plans.py` |
| 8 | Interviewer / moderator turns | I P | **server-side plan** + Gemini for a one-sentence reaction | plan, progress, last answer → reaction + next planned question word for word, or one follow-up if the answer was under 25 words | fixed reaction + planned question | plan adherence is guaranteed by code (tested) | `practice_plans.py` |
| 9 | Partner voice | C I P | **Kokoro-82M** (Kokoro-FastAPI container) | text → speech | OpenAI TTS → browser voice | MOS-style naturalness rating | `routers/conversation.py` |
| 10 | Deck insights | P | Gemini | slide text (.pptx/.pdf) → summary, main message, structure, key point per slide, suggestions, likely questions | rule-based from slide text | supervisor rating of summaries | `deck_insights.py` |
| 11 | Slide-by-slide talk check | P | rules + Gemini | each slide's text and key point + the words spoken while it was on screen (split by slide timings) → coverage, 1–5 match, covered / missing / tip | key-word coverage only | rating vs a human judge | `live/talk.py` |
| 12 | Pronunciation | C I P | phone-level GOP: espeak-ng phonemes (British English, per phrase) + `facebook/wav2vec2-xlsr-53-espeak-cv-ft` + CTC forced alignment; deviations split into **regional** (Malaysian English features, accepted) and **intelligibility-affecting** (flagged); Malay words detected acoustically and skipped | audio + word timings → 0–100, unclear sounds named | word-level Wav2Vec2 CTC confidence + 5% allowance | Pearson r with human ratings ≥ 0.7 | `live/pronunciation.py` |
| 13 | Prosody | C I P | librosa YIN pitch + RMS (signal processing) | audio → pitch variation (semitones), loudness (dBFS), steadiness | not measured | agreement with Praat on sample clips | `live/extra_metrics.py` |
| 14 | Eye contact | C I P | MediaPipe Face Mesh (iris) | 60 sampled frames → % at camera, gaze direction | not measured | accuracy vs. manual coding ≥ 0.8 | `live/vision.py` |
| 15 | Gaze Tunneling | C I P | MediaPipe iris gaze at ~2 fps + disfluency word timings, Pearson r per 5 s window, circular-shift permutation test | recording → r, p, label (needs ≥ 100 s of speech) | left out | accuracy of gaze vs coded frames; rate of significant links | `live/vision.py`, `live/extra_metrics.py` |
| 16 | Posture, gestures, head | C I P | MediaPipe Pose | frames → posture, hand movement, head steadiness | not measured | accuracy vs. manual coding | `live/vision.py`, `live/extra_metrics.py` |
| 17 | Facial expression | C I P | ViT `trpakov/vit-face-expression` on MediaPipe face crops | frames → emotion distribution, tension | not measured | accuracy vs. manual labels | `live/vision.py` |
| 18 | Answer feedback | I P | Gemini, JSON validated, **fact-checked** | question–answer pairs + plan → per answer: relevance / structure / specificity (1–5), went well, improve, stronger answer | rule-based: STAR cue words, numbers, length, overlap with the question | Likert: specific, actionable, accurate; % of rewrites flagged by the fact check | `practice_plans.py` |
| 19 | Language tips | C | Gemini | your turns → up to 5 corrections (said → more natural, why) + conversation tips | reply length and asking questions back | Likert rating; precision of corrections | `practice_plans.py` |
| 20 | Coaching plan | C I P | measured candidates → Gemini picks and phrases the top 3 | every measured issue + your goal → 3 drills, each with its evidence and target | ranked rule-based list | Likert: actionable. The model can't add an issue that wasn't measured | `live/coaching.py` |
| 21 | Usage accounting | C I P | counts per session | STT requests, audio and billed seconds (≥ 10 s each), LLM calls and tokens → `analysis.details.usage` | — | compared with provider dashboards | `live/pipeline.py`, `services/ai.py` |

Removed on 2026-10-07: the narrated example presentation (slide scripts by `qwen2.5vl`, narration by Mesolitica Malaysian-TTS). The deck stage exists so the AI understands the deck and can check the talk against it.

**Guards against wrong AI output**

- **Plans:** the model's JSON is validated and re-prompted once. Category labels the model adds ("(Mixed)") and placeholders ("[Candidate]") are removed. Interview question 1 is always asked word for word.
- **Interview and Q&A turns:** the server decides which question comes next. The model only writes a one-sentence reaction, so even a small model can't skip or invent questions.
- **Speech-to-text silence:** text Whisper invents on silence or noise ("Subtitles by the Amara.org community", a lone "you") is dropped using its no-speech probability.
- **Stronger answers:** any name or number the candidate never said triggers a re-prompt. Examples are "Tableau", "Maybank" or "30%". If one is still there, that rewrite is replaced by a structure hint.
- **Coaching:** the model only chooses from issues that were actually measured.
- **Unmeasured metrics** show as "not measured", never as an estimated number. The reason is listed in the session's notes.

---

## 2. Metrics and the four pillars

The results page groups every measured metric into four pillars.
- Each metric is mapped to 0–100 against its comfortable range.
- A pillar's score is the mean of the metrics actually measured.
- Status: **Strong** ≥ 75 · **Okay** ≥ 55 · **Work on this** below 55.

### Voice & delivery

| Metric | Method | Score (0–100) | Comfortable range |
|---|---|---|---|
| Fluency | 100 − \|wpm − 135\| × 0.5 − min(2 × pauses, 30); pauses = gaps > 0.25 s from word timings (or ffmpeg silencedetect) | as is | ≥ 70 |
| Speaking pace | words ÷ minutes | 100 − 2.5 × wpm outside 120–160 | 120–160 wpm |
| Pronunciation | Wav2Vec2 CTC confidence over each word's span, +5% Malaysian-English allowance | as is | ≥ 70 |
| Vocal variety | SD of pitch in semitones around your median (YIN 70–400 Hz, voiced 20 ms frames, octave errors trimmed) | < 2 st: 40 → 90; 2–7: 100; above 7: −8/st | 2–7 semitones |
| Volume & steadiness | mean dBFS of voiced frames; SD of that level | min(level: −4/dB below −35; steadiness: −8/dB above 7) | louder than −35 dBFS, ±7 dB |

### Language & clarity

| Metric | Method | Score | Comfortable range |
|---|---|---|---|
| Filler words | Hesitations (*um, uh, err, erm…*) always count. Discourse markers (*like, you know, I mean, actually, basically, macam, sebenarnya…*) count only at a clause start or next to a comma. *"I like data"*, *"what kind of tool"*, *tapi* and particles (*lah, kan*) are not fillers | 100 − 12 × (per min − 2) | < 2 per min |
| Vocabulary richness | MATTR: mean type-token ratio over 50-word windows | (MATTR − 0.45) ÷ 0.27 × 100 | ≥ 65% varied |
| Hedging | *I think, maybe, kind of, sort of, I guess, probably, perhaps, I'm not sure, mungkin…* per 100 words | 100 − 18 × (per 100 − 1) | < 1 per 100 words |
| Repetitions & blocks | Repetition: the same word twice within 0.6 s. Block: mid-sentence silence ≥ 1.2 s. Prolongation: steady-energy voiced segment ≥ 0.35 s | 100 − stuttering score (8 per event) | 0–2 events |

### Body language

| Metric | Method | Score | Comfortable range |
|---|---|---|---|
| Eye contact | iris position → camera / left / right / down on 60 frames | % of frames at the camera | ≥ 70% |
| Posture | head tilt (ear line), shoulder level, torso movement | mean of the three | ≥ 75 |
| Hand gestures | share of frames where a visible wrist moved > 15% of shoulder width | 60 + 40 × min(1, ratio ÷ 0.2), minus a penalty above 60%. Hands out of view caps the score but isn't penalised | 20–60% of the time |
| Head steadiness | SD of the nose relative to the shoulder midpoint (÷ shoulder width) | 100 − 250 × SD | ≥ 70 |

### Confidence & presence

| Metric | Method | Score | Comfortable range |
|---|---|---|---|
| Confidence | 0.40 speech (pace, pauses, fluency) + 0.35 face (expression, tension) + 0.25 body (posture, stability) | as is | ≥ 70 |
| Relaxed expression | tension = share of fearful + angry + sad frames | 100 − tension | tension < 30 |
| Response time | in the browser: end of the AI's turn → first sound of your answer (median) | 100 − 12 × (s − 1.5) | ≤ 2 s |
| Gaze Tunneling | on the server: share of each 5 s window looking away (iris, ~2 fps) vs disfluencies in it (word timings); Pearson r with a circular-shift permutation test; needs ≥ 100 s of speech | 100 − 100 × r if p < 0.05, else 100 | no significant link |

### Overall score

0.25 × fluency + 0.25 × pronunciation + 0.20 × confidence + 0.15 × eye contact + 0.15 × posture, re-weighted over the components actually measured. When none of these were measured, it falls back to the mean of the pillars. Grades: ≥ 85 Excellent · ≥ 70 Good · ≥ 55 Fair.

### Content (what you said)

| Function | What is judged | Scale |
|---|---|---|
| Interview | each answer against its planned question: **relevance**, **structure** (STAR: situation, task, action, result), **specificity**; what went well; the one thing to improve; a stronger answer built from your own facts | 1–5 each |
| Presentation Q&A | each answer against the deck: relevance, structure (direct answer first, then reason or evidence), specificity | 1–5 each |
| Presentation rehearsal | **key point per slide**: coverage of each slide's key point (weighted double) plus its script terms. Also overall key-term coverage, pace vs. the example, duration ratio, long pauses | covered ≥ 60% · partly ≥ 30% · missed |
| Conversation | up to 5 grammar or word-choice corrections (Malaysian English expressions are not errors) + conversation tips | — |

---

## 3. Evaluation plan

| Component | Metric | Ground truth | Target | Status |
|---|---|---|---|---|
| Speech recognition | WER by Malay / English / mixed / US-UK English | FLEURS ms_my (25 real speakers) + Malaysian TTS + Kokoro clips | clear reduction vs. Whisper baseline | **Done:** 6.1% vs 51.3% baseline |
| Deployed speech recognition (Groq) | WER on the same held-out clips; silence outputs | 200 FLEURS en_us + 100 FLEURS ms_my + 200 Synth-Manglish + 10 silent | matches the same weights run locally; no text on silence | **Done:** 4.9% / 7.3% / 16.5%, equal to local; silence fixed by the filter (`docs/benchmarks/stt-groq-cloud-2026-10-15.md`) |
| Speech recognition (real users) | WER on app recordings | 30–50 transcribed user clips | ≤ 10% | Needs data (see §4) |
| Code-switch routing | WER routing on vs off | 200 FLEURS en_us + 200 Synth-Manglish (synthetic) | routing on ≤ off | **Done:** English 5.3% → 5.3%, mixed 15.4% → 36.7% (routing hurts) (`docs/benchmarks/stt-routing-and-finetune-2026-10-06.md`) |
| Fine-tuned ASR (not deployed) | WER vs shipped model | same 400 clips | clear reduction, silence stays empty | **Done on public data:** English 9.4% → 6.7%, mixed 14.5% → 6.7%, 0/10 silent clips with text; real speakers still needed |
| Filler & disfluency detection | precision, recall, F1 | manually annotated transcripts/audio | F1 ≥ 0.75 | Needs data |
| Pronunciation | Pearson / Spearman r with human ratings | 2–3 raters on ~20 clips | r ≥ 0.7 | Needs data |
| Eye contact / gestures / posture | accuracy vs. manual frame coding | coded webcam clips | ≥ 0.8 | Needs data |
| Prosody | agreement with Praat pitch/intensity | 10 clips | r ≥ 0.9 | Planned |
| Question plans | relevance 1–5 by supervisor/users | 10 setups × 2 raters | mean ≥ 4 | Planned |
| Answer feedback | Likert: specific, actionable, accurate; fact-check flag rate | UAT | ≥ 4 / 5 | Planned |
| Overall score | correlation with a supervisor's rating | recorded sessions | r ≥ 0.6 | Planned |

---

## 4. What would raise accuracy further

| Area | Option | Effect |
|---|---|---|
| LLM (plans, feedback, partner) | A 7B–14B local model (`qwen2.5:7b`/`14b`) on a GPU, or a cloud LLM (`OPENAI_API_KEY`, Gemini, DashScope via `LLM_BASE_URL`) | Better questions, fewer invented details, more natural replies. The 3B model needs the guards above |
| Pronunciation | Azure Pronunciation Assessment or SpeechAce (phoneme-level GOP) | True phoneme scores instead of CTC confidence |
| Prosody / emotion in voice | Hume AI Expression Measurement, or a local SER model (e.g. emotion2vec) | Vocal confidence and emotion from the audio itself |
| Eye contact | Calibrated gaze (e.g. L2CS-Net) with a 5-second calibration step | Fewer false "looked away" readings |
| Ground truth | 30–50 consenting user recordings, transcribed and annotated | Real WER, filler F1 and pronunciation correlation for the report |
