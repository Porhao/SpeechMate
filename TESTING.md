# Testing SpeechMate

How to try each of the three functions by hand, the demo accounts to use, and a glossary of the terms in the app.

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

The first start downloads a lot:
- Docker images;
- the speech/vision models (on the first analysis);
- the Malaysian TTS (on the first deck);
- the Ollama models (in the background; follow with `docker compose logs -f ollama-pull`).

Until the LLM has downloaded, AI features use their offline fallbacks (question bank, rule-based feedback).

Use **Chrome or Edge** and allow the camera and microphone. Use headphones if you can, so the AI's voice doesn't reach your mic.

---

## 2. Test accounts

They're created at startup when `SEED_DEMO_DATA=true`, which the root `docker-compose.yml` sets by default. Existing accounts are never overwritten.

| Email | Password | Use it to test |
|---|---|---|
| `demo@speechmate.dev` | `Demo1234!` | **Aisyah Rahman**: profile filled in (goal *Improve Presentations*). Has **3 example sessions** (conversation → interview → presentation Q&A) with improving scores, pillars and interview answer feedback, so Home, Progress and Results have data |
| `new@speechmate.dev` | `Demo1234!` | **Farid Hakim**: an empty account, for first-time flows and empty states |

- Demo sessions are marked *"Demo data created by scripts/seed_demo.py — not a real recording."* in their notes.
- To add the demo accounts to an existing database: `docker compose exec backend python scripts/seed_demo.py --force`.
- To start completely fresh: `docker compose down -v` (**deletes all data**), then `./start.sh`.
- For a real deployment, set `SEED_DEMO_DATA=false`.

**Sample deck:** `docs/samples/sample_deck.pptx` (3 slides on time management).
**Sample resume:** any PDF, DOCX or TXT CV of your own.

---

## 3. What to test

### A. Accounts
1. **Sign in** at `/login` with the demo account → you land on **Home**, which shows the three functions, *Your next focus* and *Recent sessions*.
2. **Register** a new account. The onboarding asks for your goal and preferred practice and takes you straight to that function.
3. **Profile and Settings:** change your goal or theme (Light / Dark / System).

### B. Daily conversation
1. Top bar → **Conversation** → pick a scenario (or type your own topic) → **Start conversation** → allow the camera and microphone.
2. The partner greets you about the topic. **Talk for 2–3 minutes:**
   - pause for about a second and "Transcribing…" appears, then the partner replies in the Kokoro voice;
   - you can also type;
   - **Shuffle** changes the topic.
3. Check the camera stage: the large view is a clean mirror, the small inset shows MediaPipe tracking, and *Lighting & contrast* gives advice once a second. No scores are shown while you talk.
4. **End.** You go straight to **Results**, which says "Analysing…" with the stages (1–3 min on CPU). The bell also notifies you.
5. **Check Results:**
   - the overall score and summary;
   - four pillar cards (tap one to see each metric, your value and the comfortable range);
   - **Your language** (corrections and tips);
   - **Practise next** (3 drills with evidence and targets);
   - the transcript, and notes on anything that couldn't be measured.
6. **Malay / Manglish:** say *"Actually I think the project is good lah, tapi kita perlu more time."* The **Language mix** card should show both languages and the particle *lah*. *lah* and *tapi* must **not** count as filler words.

### C. Mock interview
1. Top bar → **Interview**:
   - position (e.g. *Data Analyst*), company, level, type (Behavioural / Technical / Mixed);
   - your background;
   - optionally a job description and a **resume** upload (the extracted text preview appears; you can remove it).
2. **Preview questions** (30–60 s with the local LLM). The questions should mention your role, background or resume. **New set** regenerates them.
3. **Start interview** → the session page shows *Your interview* (role, level, "using your resume") → **Start interview**:
   - Alex greets you by name and asks question 1;
   - the header shows **Question 1 of N**.
4. Answer briefly (under about 25 words). Alex should ask **one follow-up** and not move on. Answer that, or give a full answer: Alex reacts in one sentence and asks the **next planned question** word for word. After the last question Alex closes the interview.
5. **End → Results.** Besides the pillars, **Your answers** lists each question with:
   - *On topic / Structure / Specific* (1–5);
   - *Went well*, *Improve*;
   - *Show a stronger answer*: it should only use facts you said; missing details appear as placeholders like "<the result>".

### D. Presentation practice
1. Top bar → **Presentation** → upload `docs/samples/sample_deck.pptx` (or a PDF). Optionally choose a narrator voice and an audience (e.g. *"First-year students, 5-minute talk"*).
2. The three-step strip appears.
   - **Step 1 Understand the deck:** after "Analysing content" (~35 s) the insights panel shows the summary, structure, each slide's key point, suggestions and likely questions, while the example video is still building.
3. **Step 3 Rehearse the Q&A** (available as soon as the insights are ready) → **Start Q&A rehearsal**:
   - the moderator thanks you and asks questions drawn from your slides;
   - the header shows Question x of N.
   - **End → Results:** **Your Q&A answers** has per-answer feedback.
4. **Step 2 Rehearse the talk** (once the video is ready):
   - watch the example narration (the script highlights the current slide);
   - record the **whole deck** or **one slide** → feedback.
5. **Check the rehearsal feedback:**
   - what went well;
   - Observation → Impact → Suggestion cards;
   - delivery metrics;
   - **Key point per slide** (Covered / Partly / Missed, with the terms you didn't say);
   - the audience view;
   - the transcript;
   - the follow-up chat (*"What should I fix first?"*).

### E. Progress
**Progress** shows totals, the overall score per session, a trend per pillar and every session. Filter by function, open a session's results, or delete it.

### F. Notifications, theme, reference
- **Bell** (top left): a count appears when an analysis, example video or rehearsal feedback is ready (or failed). Click an item to open it.
- **Theme:** the moon/sun button, or Settings → Appearance.
- **How it's measured:** four tabs:
  - Session metrics (every formula and range);
  - Presentation practice;
  - **AI functions** (model, input → output, fallback, quality check);
  - Project evaluation.

### G. Fallbacks (no LLM)
Stop the LLM with `docker compose stop ollama`, then:
- interview preview shows *"standard question bank"*;
- the interviewer still follows the plan (fixed reactions);
- answer feedback is rule-based (marked);
- the conversation partner uses scripted prompts.

Nothing crashes. Restart with `docker compose start ollama`.

### H. API checks (http://localhost:8000/docs)
1. `POST /api/auth/login` with the demo account → copy the `access_token` → **Authorize**.
2. Try these:
   - `POST /api/interview/plan` with `{"position": "Nurse", "interview_type": "behavioural"}`;
   - `GET /api/live`: sessions with `context` (setup + plan), `turns`, and `analysis.pillars` / `analysis.content_feedback`;
   - `GET /api/progress`: one point per metric per session, including `voice_score`, `language_score`, `body_score`, `presence_score`.

### Automated tests
```bash
docker compose exec backend sh -c "pip install -r requirements-dev.txt && pytest"   # 57 backend tests
cd frontend && npx tsc --noEmit && npm run lint                                    # frontend
```

---

## 4. Glossary

| Term | Meaning |
|---|---|
| **Accent-fair scoring** | Malaysian-English patterns (th → d/t, dropped final consonants, vowel shifts) count as regional variation, not errors. Pronunciation gets a +5% allowance, and Manglish particles aren't counted as fillers. |
| **Answer feedback** | After an interview or Q&A, each answer is rated 1–5 for *on topic* (relevance), *structure* and *specific* (concrete details), with what went well, the one thing to improve, and a stronger answer. |
| **ASR** | Automatic Speech Recognition: speech → transcript. SpeechMate uses Mesolitica's Malaysian Whisper with automatic language detection. |
| **Code-switching / Manglish** | Mixing English and Bahasa Melayu in one sentence. *Manglish particles* are words like *lah, lor, meh, kan*. |
| **Comfortable range** | The range a metric is scored against (e.g. 120–160 words per minute). Inside it scores high. |
| **Communication score / Overall** | 0–100: fluency 25%, pronunciation 25%, confidence 20%, eye contact 15%, posture 15%, re-weighted over what was measured (or the mean of the pillars). |
| **Confidence** | Estimated from speech (40%), face (35%) and body (25%). |
| **Deck insights** | The AI's reading of your deck before you practise: summary, main message, structure, each slide's key point, suggestions and likely questions. |
| **Deferred feedback** | No scores or corrections while you speak; everything comes after, to reduce cognitive load. |
| **Fact check (stronger answers)** | Any name or number in a rewritten answer that you never said makes the AI rewrite it. If it persists, a structure hint is shown instead. |
| **Fallback** | What a stage does when its model isn't available. It's always noted, never silent. |
| **Filler words** | Hesitations (*um, uh, err*) always count. Discourse markers (*like, you know, actually, macam, sebenarnya*) count only at the start of a clause or next to a comma. |
| **Follow-up** | In an interview or Q&A, an answer under about 25 words gets one follow-up question before the next planned question. |
| **Gaze Tunneling** | The correlation between looking away and stumbling over words, computed from the session's own samples. |
| **Hand gestures** | The share of the time your hands are visible and moving. 20–60% looks natural. |
| **Head steadiness** | How still your head is relative to your shoulders (excessive nodding or bobbing lowers it). |
| **Hedging** | Phrases that make you sound unsure (*I think, maybe, kind of, I guess*), per 100 words. |
| **Key point per slide** | Whether each slide's key point (from the deck insights) came through in your rehearsal: Covered, Partly or Missed. |
| **Kokoro** | The open-source 82M TTS that gives the AI partner its natural voice. |
| **LLM / VLM** | Large language model (text) / vision-language model (reads slide images). Here: Ollama `qwen2.5` / `qwen2.5vl`. |
| **MATTR (vocabulary richness)** | Moving-average type-token ratio: the share of different words in each 50-word window. |
| **OIS** | **Observation → Impact → Suggestion**: what happened, why it matters to the audience, and one thing to do next time. |
| **Pillars** | The four simple scores on Results: **Voice & delivery**, **Language & clarity**, **Body language**, **Confidence & presence**. Each is the mean of its measured metrics. |
| **Question plan** | The curated questions for an interview (from your setup and resume) or a Q&A (from your deck), each with what it tests and what a strong answer contains. The AI follows it in order. |
| **Response time** | How long you take to start answering after the AI finishes. Under 2 s is comfortable. |
| **Speaking rate / WPM** | Words per minute. 120–160 is comfortable. |
| **STAR** | Situation, Task, Action, Result: a structure for behavioural interview answers. |
| **Stuttering events** | Repetitions ("I I think"), blocks (silence ≥ 1.2 s mid-sentence) and prolongations ("sssso"). |
| **Vocal variety** | How much your pitch moves, in semitones. Under 2 sounds monotone; 2–7 is lively. |
| **Volume & steadiness** | How loud your voice is (dBFS) and how steady it stays. |
| **Warnings / notes** | The list on every result of what couldn't be measured and which fallbacks were used. |
