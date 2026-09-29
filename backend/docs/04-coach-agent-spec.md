# Coach Agent — Detailed Spec (Phase 2)

## Precondition
A session must have a `complete` Ideal Presentation Agent output (video + per-slide scripts + per-slide ideal audio) before a practice/coaching run can be started against it. Enforce this at the API level — reject coaching requests for sessions not yet `complete`.

## Goal
Input: the user's own recorded practice audio (per-slide or whole-deck, see below) for the same deck.
Output: structured feedback in Observation–Impact–Suggestion (OIS) format, plus an interactive chat for follow-up.

## Recording granularity decision (make this explicit before building)
The paper is somewhat ambiguous on whether user practice is recorded per-slide or as one continuous take. Pick one deliberately:
- **Recommended for v1: whole-deck single recording.** Simpler UX (user watches ideal video, then hits record once and presents the whole deck), simpler storage. Downside: harder to map specific feedback moments back to specific slides without timestamp alignment.
- **Alternative: per-slide recording.** User records slide-by-slide, matching the ideal agent's segment structure exactly. Easier to generate precise per-slide feedback, more tedious UX.
- Whichever you pick, keep the practice audio segmentation strategy noted in the session/practice record schema (`05-data-models-api.md`) so it's not re-decided ad hoc later.
- If going whole-deck, you'll want rough slide-boundary timestamps for the analysis step (either ask the user to click "next slide" while recording to log timestamps, or skip alignment and treat the whole recording as one unit for v1 — simplest option, defer per-slide granularity to a later iteration).

## Stage 1: Multimodal Speech Analysis
- Input per practice session: user's practice audio + the deck's ideal script(s) + ideal audio + slide image(s).
- **Two implementation paths** (pick per `02-tech-stack.md` decision):
  - **Path A (native multimodal):** send slide image + ideal audio + user audio directly to a model with native audio understanding (e.g., Gemini 2.5). Fewer moving parts, less control over intermediate output.
  - **Path B (transcribe-then-reason, recommended for debuggability):**
    1. Transcribe user audio with Whisper (also gives word-level timestamps, useful for pacing metrics).
    2. Compute objective delivery metrics separately and deterministically (not via LLM): words-per-minute, pause count/duration, filler-word count (simple regex/wordlist match: "um", "uh", "like", "you know"), total duration vs. ideal audio duration.
    3. Feed transcript + computed metrics + ideal script text + slide content into a text LLM to generate the qualitative feedback.
  - Path B is more code but each piece is independently testable — recommended for a first build so you can debug "why did the feedback say X" without opening a black-box multimodal call.

## Stage 2: Structured Feedback Generation (OIS format)
Required output structure, mirroring the paper:
1. **Sincere Encouragement** — 1-2 sentences identifying a genuine strength, not generic praise. Ground it in something specific from the analysis (e.g., pacing matched the ideal closely, or a specific well-phrased transition).
2. **OIS block(s)** — under ~150 words total, structured as:
   - **Observation:** what specifically happened (e.g., "You paused for over 4 seconds before slide 3's key statistic")
   - **Impact:** why it matters (e.g., "This broke the narrative momentum right before your strongest point")
   - **Suggestion:** a concrete, actionable fix (e.g., "Try a shorter transitional phrase like 'Here's the number that matters' instead of a silent pause")
- Enforce this shape server-side: prompt the LLM to return structured JSON (`{encouragement, observations: [{observation, impact, suggestion}]}`), not freeform prose — makes it renderable as UI components and keeps length under control. Validate/parse the JSON; re-prompt once if malformed.
- Limit to 1-3 OIS items per feedback pass — the paper caps total feedback at under 150 words, so don't generate five observations; pick the most impactful ones.

## Stage 2b (stretch, Phase 3): Audience Agent
A second feedback lens that simulates listener comprehension/engagement rather than delivery technique.
- Same inputs as Stage 1, different system prompt: "You are an audience member listening to this presentation for the first time. Note points of confusion, moments of high/low engagement, and overall clarity of the message — not delivery mechanics like pacing."
- Present as a distinct, separately labeled feedback block in the UI so users understand it's a different perspective (paper's participants valued this distinction — see `06-frontend-ui-spec.md`).
- Build this only after Stage 1/2 are solid — it's additive, not required for a working Coach Agent.

## Stage 3: Conversational Follow-up (chat)
- Standard chat interface scoped to one practice session.
- Context passed to the LLM on each chat turn: the ideal script(s), the structured feedback just generated, and the running chat history for this session (not the whole app's history — keep it scoped).
- No RAG/embeddings needed at this scale — just include the relevant text directly in the prompt (session context is small: a handful of slide scripts + one feedback report + recent chat turns).
- Persist chat history per practice session (`chat_history.json` or a `messages` table row per turn) so the user can leave and come back.

## API surface for this agent
- `POST /sessions/{id}/practice` — upload practice audio (and/or video), kicks off Stage 1+2 analysis
- `GET /sessions/{id}/practice/{practice_id}` — poll status, fetch feedback once ready
- `POST /sessions/{id}/practice/{practice_id}/chat` — send a chat message, get a response
- `GET /sessions/{id}/practice/{practice_id}/chat` — fetch chat history

## What to stub first when building
1. Get Stage 1 Path B's deterministic metrics (WPM, pauses, filler words) working on a real recording *before* touching any LLM call — these are pure code and easy to unit test.
2. Feed a hand-written fake transcript + fake metrics into the OIS prompt and verify the JSON structure comes back clean and under the word limit.
3. Only then wire up real transcription (Whisper) and real practice-audio upload.
4. Add the chat follow-up last — it depends on Stage 2's output already existing.
5. Audience Agent and richer multi-session progress tracking are Phase 3 — don't build them before Stage 1-3 are solid for a single session.
