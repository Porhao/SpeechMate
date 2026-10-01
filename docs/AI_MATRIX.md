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
| **P** | Presentation practice | `/presentations/[id]` → `/session` | Reads and summarises the deck; narrates an example; coaches rehearsals per slide; runs a Q&A drawn from the deck and judges every answer |

All models run locally by default (Ollama, faster-whisper, Kokoro, Mesolitica, MediaPipe). No cloud key is needed.

---

## 1. AI functions

| # | AI function | Used in | Model / method | Input → output | If unavailable | How quality is checked | Code |
|---|---|---|---|---|---|---|---|
| 1 | Speech recognition (session) | C I P | Mesolitica **Malaysian Whisper large-v3-turbo-v3** (CTranslate2 int8, faster-whisper, 8 CPU threads, beam 5, **auto language detection**, VAD filter) | 16 kHz audio → transcript + word timings | OpenAI Whisper → (live turns) browser recogniser | WER per language: **6.1% overall, 6.4% Malay, 4.0% Malaysian English, 17.0% Manglish, 0.0% US/UK English** (`docs/benchmarks/stt-benchmark-2026-10-01.md`) | `live/asr.py` |
| 2 | Speech recognition (each live turn) | C I P | same model, per spoken turn (`/api/stt`) | one turn → text (about 2.5 s per 5 s turn) | browser recogniser | same as 1 | `routers/conversation.py` |
| 3 | Code-switch re-check | C I P | Mesolitica `wav2vec2-xls-r-300m-mixed` | audio Whisper isn't confident is English → Malay/mixed transcript | Whisper transcript + warning | WER on mixed speech | `live/asr.py` |
| 4 | Conversation partner | C | Ollama **qwen2.5:3b** | last 12 turns + topic → 2–3 spoken sentences | scripted prompts | UAT naturalness rating | `routers/conversation.py` |
| 5 | Interview question plan | I | qwen2.5:3b, JSON validated (Pydantic) and re-prompted once | role, company, level, type, background, job description, resume text → 6–8 questions, each with *what it tests* and *what a strong answer contains* | question bank (behavioural / technical / mixed) | relevance rating by users/supervisor | `practice_plans.py` |
| 6 | Resume reading | I | `pdftotext` / DOCX XML / plain text | resume file → text (max 8,000 chars) | user types their background | — | `practice_plans.py` |
| 7 | Q&A question plan | P | qwen2.5:3b, JSON validated | deck insights + audience → 5–6 audience questions tied to slides | likely questions + key points from the insights | relevance rating | `practice_plans.py` |
| 8 | Interviewer / moderator turns | I P | **server-side plan** + qwen2.5:3b for a one-sentence reaction | plan, progress, last answer → reaction + next planned question word for word, or one follow-up if the answer was under 25 words | fixed reaction + planned question | plan adherence is guaranteed by code (tested) | `practice_plans.py` |
| 9 | Partner voice | C I P | **Kokoro-82M** (Kokoro-FastAPI) | text → speech | OpenAI TTS → Malaysian TTS (GPU) → browser voice | MOS-style naturalness rating | `routers/conversation.py` |
| 10 | Deck insights | P | qwen2.5:3b | slide text (.pptx/.pdf) → summary, main message, structure, key point per slide, suggestions, likely questions | rule-based from slide text | supervisor rating of summaries | `deck_insights.py` |
| 11 | Slide scripts | P | Ollama **qwen2.5vl:3b** (vision) | slide image + text + deck context → narration per slide | template from slide text | rating of the example talk | `script_generator.py` |
| 12 | Narration voice | P | Mesolitica **Malaysian-TTS-0.6B-v1** (7 voices) | script → audio | OpenAI TTS → espeak | naturalness rating | `malaysian_tts.py` |
| 13 | Pronunciation | C I P | Wav2Vec2 `facebook/wav2vec2-base-960h` CTC confidence, +5% Malaysian-English allowance | audio + transcript → 0–100, unclear words | shown as not measured | Pearson r with human ratings ≥ 0.7 | `live/pronunciation.py` |
| 14 | Prosody | C I P | librosa YIN pitch + RMS (signal processing) | audio → pitch variation (semitones), loudness (dBFS), steadiness | not measured | agreement with Praat on sample clips | `live/extra_metrics.py` |
| 15 | Eye contact | C I P | MediaPipe Face Mesh (iris) | 60 sampled frames → % at camera, gaze direction | not measured | accuracy vs. manual coding ≥ 0.8 | `live/vision.py` |
| 16 | Posture, gestures, head | C I P | MediaPipe Pose | frames → posture, hand movement, head steadiness | not measured | accuracy vs. manual coding | `live/vision.py`, `live/extra_metrics.py` |
| 17 | Facial expression | C I P | ViT `trpakov/vit-face-expression` on MediaPipe face crops | frames → emotion distribution, tension | not measured | accuracy vs. manual labels | `live/vision.py` |
| 18 | Answer feedback | I P | qwen2.5:3b, JSON validated, **fact-checked** | question–answer pairs + plan → per answer: relevance / structure / specificity (1–5), went well, improve, stronger answer | rule-based: STAR cue words, numbers, length, overlap with the question | Likert: specific, actionable, accurate; % of rewrites flagged by the fact check | `practice_plans.py` |
| 19 | Language tips | C | qwen2.5:3b | your turns → up to 5 corrections (said → more natural, why) + conversation tips | reply length and asking questions back | Likert rating; precision of corrections | `practice_plans.py` |
| 20 | Coaching plan | C I P | measured candidates → qwen2.5:3b picks and phrases the top 3 | every measured issue + your goal → 3 drills, each with its evidence and target | ranked rule-based list | Likert: actionable. The model can't add an issue that wasn't measured | `live/coaching.py` |
| 21 | Rehearsal feedback (OIS) | P | qwen2.5:3b | metrics + transcript + scripts + insights → Observation → Impact → Suggestion, audience view | rule-based from the metrics | Likert rating | `coach/feedback.py` |

**Guards against wrong AI output**

- **Plans:** the model's JSON is validated and re-prompted once. Category labels the model adds ("(Mixed)") and placeholders ("[Candidate]") are removed. Interview question 1 is always asked word for word.
- **Interview and Q&A turns:** the server decides which question comes next. The model only writes a one-sentence reaction, so even a 3B model can't skip or invent questions.
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
| Gaze Tunneling | Pearson r between looking away and stumbling, per 5 s window (browser) | 100 − 100 × r | r < 0.3 |

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
| Speech recognition (real users) | WER on app recordings | 30–50 transcribed user clips | ≤ 10% | Needs data (see §4) |
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
