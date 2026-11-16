# Untangle log (decision log)

Refactor of `backend/app` and `frontend/` using the untangle-codebase method: pieces that change together end up together, pieces that don't aren't tied, and everything depends on what changes less. Extras chosen: **Comments** and **Tests** (tests last).

Each fix sits above the problems it solves. **BUG** = changes behaviour today and will be fixed along the way. **DECIDE** = needs the author's call before it changes a number users see.

Status key: `[ ]` todo · `[x]` done · `[-]` dropped (reason given).

**Decisions (author, 2026-11-16):** pace and fillers unified to the documented rules (−2.5/wpm outside 120–160, fillers ×12); eye contact from the single 2 fps gaze pass; DB columns kept, legacy refresh-token code removed; Manglish words like "what"/"also"/"one" count as particles only at the end of a clause.

---

## Backend

### B1. One LLM call helper in `services/ai.py` (public `llm_json`, `llm_text`), one word counter in `services/text.py`
**Status: done.** `ai.llm_json` / `ai.llm_text` (both providers get usage counting + fallback model), `services/text.py` (`words`, `count_words`, `invented_terms`), `with_retries` retries only transient errors and `llm_json` uses it. Bonus bug found: `content_feedback`'s 65-line `except` hid a wrong call; now only the LLM call is guarded and a provider error falls back to rule feedback.
`llm_json(system, payload, model, check=, tries=, fallback_on_fail=)` and `llm_text(system, messages, max_tokens, temperature, fallback)` own retries, usage counting and the fallback model for both providers.
- `practice_plans.py:89` `_llm_json` is private but imported by `routers/impromptu.py:16`, `services/script_writer.py:19`, `live/talk.py:139`.
- `deck_insights.py:158-186` and `live/coaching.py:338-376` re-implement the same validate/re-prompt loop.
- Free-text LLM boilerplate three times: `routers/conversation.py:98-107`, `services/assistant.py:89-97`, `practice_plans.py:340-350`, each with different error handling.
- `routers/conversation.py:79` vs `:99-114`: LLM usage added to `context["llm_usage"]` two different ways.
- **BUG** `ai.py:111-112`: with the OpenAI provider, usage counts 0 and `LLM_FALLBACK_MODEL` never applies (no transport hooks on that client).
- `script_writer.py:92-94`: `with_retries(3)` around `_llm_json(tries=3)` = up to 9 calls; `ai.py:170` retries every exception including 4xx and bugs.
- `routers/impromptu.py:74-83`: redundant client check plus try around a helper that already returns None.
- Five word tokenisers giving different counts: `live/speech.py:38` `_count_words`, `ai.py:179` `count_words`, `live/talk.py:33`, `live/extra_metrics.py:99`, `live/language.py:60,92`; `live/pipeline.py:83` imports the private one.
- `ai.py:179-192`: text helpers (`count_words`, `parse_json_object`) live in the client module.
- Tests tied to the private name: `tests/test_practice.py:235-236` patches `impromptu._llm_json`; `tests/test_live.py:165-183` fakes the OpenAI client shape to reach coaching's own loop.

### B2. One metric-rules module `live/rules.py`: every threshold and 0–100 score function, used by confidence cues, pillars, coaching and posture advice; the API sends each score's status so the frontend stops copying bands
**Status: backend done** (`live/rules.py`; pace −2.5 and fillers ×12 everywhere incl. fluency; cues carry `status`; pillar ranges and coaching texts derived from the constants; unused `PostureResult.recommendations` removed). Frontend side in F2.
- **DECIDE** Pace scored three ways: `scoring.py:60` (−1.5/wpm), `extra_metrics.py:176` (−2.5/wpm, the documented one, TECHNICAL.md:413), `speech.py:83` (target 135, −0.5) for fluency; plus `coaching.py:106,115` cut-offs 165/110.
- **DECIDE** Fillers: `scoring.py:91` (×10) vs `extra_metrics.py:180` (×12).
- Response latency formula copied exactly: `scoring.py:93` and `extra_metrics.py:203-204`.
- `_clamp` twice with different rounding: `scoring.py:19`, `extra_metrics.py:30` (`coaching.py:66` `_clamp01`).
- Bands scattered: `speech.py:42-49` grade 80/65/50; `scoring.py:165` grade 85/70/55; `scoring.py:135` label 75/50; `extra_metrics.py:37` status 75/55; frontend copies `progress/page.tsx:33,122`, `presentations/[id]/page.tsx:191`, `results/[id]/page.tsx:141` (uses 50 where pillars use 55), `impromptu/page.tsx:266`.
- Posture thresholds copied between `vision.py:301-323` and `coaching.py:220-231`, each writing its own advice text (`PostureResult.recommendations` is never read).
- Pitch 2.0/7 (`coaching.py:256-264`, `extra_metrics.py:184-186,310`), loudness −35 dB (`coaching.py:266,273`, `extra_metrics.py:190,314`), hedging (`coaching.py:277` vs `extra_metrics.py:200,326`), eye/posture/tension/latency ranges (`coaching.py:195,214,244,290` vs `extra_metrics.py:335-356`).
- Text that silently goes stale: `coaching.py:132,136` "1.2 s" (= `speech.BLOCK_MIN_SECONDS`), `extra_metrics.py:348` "11 cues: …", `extra_metrics.py:45` comment says monotone < 1.5 but code uses 2.0.
- Frontend prose copies of thresholds: `results/[id]/page.tsx:36-48` drills ("under 2 a minute", "120–160").
- Tests that restate constants instead of behaviour: `tests/test_live.py:83,98-99,120-121,326,36`, `tests/test_practice.py:150-151`.

### B3. Typed contracts for the shared JSON: `LiveContext`, `ClientMetrics`, `PracticePlan` (one schema), `DeckInsights`, and one `PronunciationResult` both scorers return
**Status: partly done.** `ClientMetrics`/`SlideTime` validated at the API (readers dropped their own filtering); `SessionType` alias; `MAX_RESUME_CHARS` one constant. Pronunciation: both scorers return `PronunciationResult` (`PHONE_GOP`/`CTC_WORD` constants, `accent_fair_score`), adapter gone. `[-]` LiveContext/analysis Pydantic models and the stage tuples: deferred (large, low bug risk now that readers are few; revisit if the JSON shape changes again).
- `LiveSession.context` keys written in `routers/live.py:109-152`, `routers/conversation.py:79`; read with `.get` in `practice_plans.py:284-312,472-490`, `assistant.py:56-57`, `routers/live.py:165-166`, `live/talk.py:102-151`, `live/pipeline.py:66,390`, `frontend/types/index.ts:70-83` (missing `audience`, `llm_usage`).
- `context["kind"]` ("talk"/"qa") is a hidden subtype; "talk ⇒ Presentation" label logic in `assistant.py:56` and four frontend files.
- "script" has three meanings (`Session.script`, `context["script"]=True`, per-slide text); slide dicts use `index` (`sessions.py:108`, `talk.py:102`) and `slide_index` (`script_writer.py:109`, `routers/live.py:117`).
- Plan shape twice with different limits: `schemas/live.py:25-35` vs `practice_plans.py:66-75`; `MAX_RESUME_CHARS` (`practice_plans.py:30`) must equal `schemas/live.py:22`; progress init copied (`routers/live.py:151-152`, `practice_plans.py:286`).
- `client_metrics` untyped (`schemas/live.py:62`), parsed separately in `extra_metrics.py:284`, `talk.py:83`, `pipeline.py:204`; frontend sends it as `Record<string, unknown>` (`services/live.ts:35`).
- Pronunciation: `pipeline.py:230-239` adapts phone-GOP output; `mispronunciation_count` means phonemes for one scorer and words for the other; `is_correct` is 60 vs 75; magic string `"phone-gop"` compared at `pipeline.py:238,261,268,308`, `extra_metrics.py:302`; accent allowance decided in the pipeline (`pipeline.py:306-311`), not by the scorer.
- `pipeline.py:77-78`: 10-tuple and 4-tuple unpacked by position.
- Five interchangeable serialisers (`vision.as_dict`, `extra_metrics.as_dict`, `speech.to_dict`, `.to_dict` methods); `pipeline.py:178` serialises a scoring result with `vision.as_dict`.
- `pipeline.py:98-104`: display strings "Fluency", "Eye Contact" used as keys into `scoring.WEIGHTS`.

### B4. `services/decks.py` owns decks (owned-deck lookup, slides, title, Q&A plan, practice context) and `storage.py` owns folder layout; routers stop importing routers
**Status: partly done.** `services/decks.py` (`title`, `slides`, `qa_plan`); routers no longer import routers for deck slides; ownerless decks now 404 (`get_owned`). Storage layout and notification link done (see B8). `[-]` slide-text truncation kept: each limit is that LLM call's own prompt budget.
- `routers/live.py:30` imports `deck_slides` from `routers/sessions.py:102-109`; `routers/auth.py:172` imports `LIVE_STORAGE_PREFIX` from `routers/live` inside a function.
- **BUG (security)** `routers/live.py:104`: a deck with no owner can be practised by any user; `sessions.py:35` requires the owner.
- Deck title + `build_qa_plan` + `insights["qa_plan"]` copied: `routers/live.py:108`, `services/pipeline.py:131-134`.
- Storage folder layout rebuilt by hand: `sessions.py:55,148`, `routers/live.py:34,231,264`, `routers/auth.py:181`, `live/pipeline.py:407`, `tests/test_privacy.py:66,90`.
- `storage.py:19,49`: `session_id` param is really a folder path; `storage.py:35` imports the HTTP layer (`limits.save_limited` raises `HTTPException`).
- Notification link `/results/{id}` built at `live/pipeline.py:399`, deleted by string match at `routers/live.py:262`.
- Slide text truncated three times in sequence: `script_writer.py:24` (900), `deck_insights.py:26` (700), `sessions.py:108` (1500).
- `routers/live.py:102`: `_deck_context(mode=, use_script=)` params the only caller always sets.

### B5. Split `practice_plans.py` (531 lines, five concerns) by reason to change; features keep their logic in services, routers stay thin
**Status: mostly done.** `practice_plans.py` → `documents.py`, `plans.py`, `partner.py` (free + planned partner, from the router too), `feedback.py`; impromptu logic → `services/impromptu.py` (now also returns `verdict`); discarded LLM greeting and name-only paths removed; `_LLMQuestion` extends the API's `PlanQuestion`. pdftotext shared (B10).
New homes: `services/documents.py` (PDF/DOCX text, shared with slides), `services/plans.py` (interview + Q&A plans), `services/partner.py` (the live partner for all modes: free chat + planned), `services/feedback.py` (post-session content feedback), `services/impromptu.py`.
- `practice_plans.py:36-45` and `slide_processor.py:152-165`: same `pdftotext` + whitespace logic.
- The free-chat partner lives in `routers/conversation.py:34-114` (prompts, history window, nudge), the planned partner in `practice_plans.py:250-360`.
- Session types listed four times: `schemas/live.py:10` (unused), `:39`, `conversation.py:44-51`, `practice_plans.py:252`.
- Interview/Presentation branches spread through `practice_plans.py:307-312,325,357,471-487`.
- `routers/impromptu.py`: prompt, schema and scoring in the router; inline schemas also in `routers/assistant.py:18-25`, `routers/notifications.py:19-31`.
- `script_writer.py:19` (stable) depends on `practice_plans` (volatile) just for `invented_terms`.
- `INTERVIEW_SYSTEM` asks the LLM for a greeting that `practice_plans.py:209` throws away; `_finish(name)` and `_compose_intro`'s name branch only live on for tests (`tests/test_practice.py:203-208`).
- `practice_plans.py:216-217,233-237`: `insights is None` branches no caller reaches.
- `practice_plans.py:529`: one `except Exception` over 65 lines.

### B6. Vision owns every camera signal: one Pose pass (posture + gestures), one Face Mesh pass (eye contact + gaze timeline), shared landmark constants, and a lock around the shared models
**Status: done.** `vision.gaze_samples` → `eye_contact` + Gaze Tunneling from one Face Mesh pass; `vision.analyze_body` = posture + gestures from one Pose pass (gestures moved from extra_metrics); one `_with_timeout`; an `asyncio.Lock` (`_MODELS`) lets one analysis at a time use the models.
- **BUG** `config.py:29` runs 2 analysis jobs at once, but Face Mesh/Pose singletons (`vision.py:144,246`) aren't thread-safe; the pipeline's "run one at a time" (`pipeline.py:218-221,346-349`) and "speech before vision to avoid OOM" (`:69-70`) only hold within one job.
- Pose runs twice on the same 60 frames: `vision.analyze_posture` and `extra_metrics.analyze_gestures:136-170` (which imports private `vision._pose`).
- Face Mesh runs twice over the video: `vision.analyze_eye_contact:171-191` (60 frames) and `vision.gaze_timeline:215-241` (2 fps). **DECIDE** computing eye contact from the timeline samples changes eye-contact numbers slightly.
- Landmark indices and the 0.5 visibility threshold copied (`vision.py:36,38`, `extra_metrics.py:125,153`); shoulder-midpoint maths copied (`vision.py:286-287`, `extra_metrics.py:150-151`).
- Thread-pool-with-timeout copied (`vision.py:96-106`, `:200-212`).
- Gaze tunnelling: gaze source in vision, orchestration in pipeline, maths in extra_metrics; `pipeline.py:79` gates it on `eye` as a proxy; `pipeline.py:223-225` fails without a user warning unlike every other stage.

### B7. One audio module (`live/audio.py` takes media's silence/peak/duration code); user-facing errors separate from ffmpeg errors
**Status: done.** `media.py` = command runner + `ffmpeg()`; `live/audio.py` owns 16 kHz WAV, FLAC, duration, peak, silences; recording/ffmpeg failures reach users as plain `JobError` text, never stderr.
- ffmpeg command lines built in four places: `media.py:61,81`, `live/audio.py:16-20`, `live/asr.py:91`.
- `media.py:44-100` (`wav_duration`, `peak_db`, `detect_silences`) used only by `live/`; `live/audio.py` is a 30-line shallow module.
- **BUG** `media.py:13,40`: `MediaError` carries raw ffmpeg stderr; `live/pipeline.py:409-411` and `services/pipeline.py:68-75` show `str(e)` to the user. `pipeline.py:58,61` also raises it for user messages ("too short").
- `pipeline.py:59` must pass `speech.INTER_WORD_PAUSE_SEC` for the fluency maths to be right; the rule belongs to speech.
- `pipeline.py:83`: talk time computed backwards as words ÷ rounded rate; two "fillers per minute" (talk time for the cue, recording length for the pillar) that users see side by side.
- `pipeline.py:380`: work files written into the storage folder.
- `media.py:68` `noise_db`, `language.py:72` `threshold`, `talk.py:35` `limit`, `storage.py:16` `base_path`: parameters nobody passes.

### B8. One job-failure helper and a job runner that knows nothing about models
**Status: done.** `tasks.JobError` + `tasks.fail_job` replace the 4 copied failure blocks; each pipeline has `recover_after_restart()` (the live one also removes never-used rows, so `GET /live` is read-only); deck pipeline renamed `deck_pipeline.prepare_deck`; `PipelineError` gone. Storage layout: `storage.deck_folder` / `live_folder`; storage no longer imports the HTTP layer; `JSONType` in `database.py`; `NEVER_USED` / `results_link` in the model.
- Rollback/refresh/fail/notify/commit copied four times: `live/pipeline.py:409-421`, `services/pipeline.py:68-83`.
- `tasks.py:16-17,54-70`: the generic runner imports `Session`/`LiveSession` to fail interrupted jobs.
- `services/pipeline.py:32` `PipelineError` never raised; `:49-52` name and docstring describe removed stages; two modules named `pipeline`.
- `routers/live.py:181-186`: `GET /live` deletes stale rows as a side effect of a read (moves next to the startup recovery).
- Each stage's required packages listed in the pipeline (`pipeline.py:278,294,299,318,341`, `speech.py:244`) instead of the module that needs them.

### B9. Thin routers: one `get_owned()` lookup, Pydantic `from_attributes` responses, limits at the trust boundary
**Status: done** (hand mappers kept: they normalise legacy NULLs). `auth.get_owned` replaces 4 lookups (unknown `live_id` now 404s); `ConversationRequest` limits (`messages` ≤ 50, `mode: SessionType`), TTS text ≤ 4096; `check_cloud_consent` folded in. Also: `_clear_refresh_cookie`, `learner.first_name`, `limits.MB`, `config.DEFAULT_SECRET_KEY`, `JSONType` in database.py.
- Owned-row-or-404 written four times: `routers/live.py:64`, `sessions.py:32`, `notifications.py:54-58`, `conversation.py:74-76`.
- **BUG** `conversation.py:73-86`: an unknown or someone else's `live_id` silently becomes a free chat (should 404); the handler mutates the request body.
- **BUG (trust boundary)** `schemas/live.py:85` `messages` and `:93` TTS `text` have no `max_length` (truncated by hand at `conversation.py:102,127,132`).
- Hand-written mappers `from_attributes` would replace: `routers/auth.py:40-47`, `routers/live.py:48-61`, `notifications.py:34-36`, `sessions.py:76-77,87-99`.
- `auth.py:109,190`: same `delete_cookie(...)` twice; `auth.py:52` register calls `limiter.hit` by hand (login's email key is genuine); `auth.py:85-88` `check_cloud_consent(None)` branch no caller uses.
- `routers/live.py:77-78` vs `assistant.py:74`: two "first name" rules.
- `conversation.py:146` `15*1024*1024` vs `limits.MB`; `main.py:25` copies the default secret literal from `config.py:32`; `notifications.py:17` re-truncates to the column size.
- `models/session.py:13` `JSONType` used by every model, defined in the deck model.

### B10. Delete surplus (verified unused)
**Status: done**, except stored-but-unread analysis detail fields (kept: they are research data for offline evaluation) and `User.role`/`language` (kept by decision). Removed: schema re-exports, `ALL_FILLERS`, `ASRResult.language/confidence`, `/stt` `engine`, resume `chars`, `mispronunciation_count`, legacy refresh-token body + `RefreshRequest`, seed backfill; `phone_gop` now uses `settings.espeak_bin`; `slide_processor` is functions (`render_slides`, `slide_texts`) sharing `documents.pdf_text`/`tidy_lines`; Manglish clause-end rule (decision).
- `schemas/__init__.py:3-5` re-exports; `schemas/live.py:10` `SESSION_TYPES`; `/stt` `engine` and `/interview/resume` `chars` fields; `schemas/session.py:19,43` unused `from_attributes` (until B9 uses it).
- `speech.py:110` `ALL_FILLERS`; `extra_metrics.py:14,21` logger; `coaching.py:70` `_trend(name)`; `asr.py:19,121,128-131` `ASRResult.language/confidence`; `phone_gop.py:298-302` counts thrown away; `pipeline.py:91,119` latency computed twice.
- `language.py:57` `"no need"` can never match. **DECIDE** `"one", "what", "also", "already", "got"` as Manglish particles label ordinary English "mixed" and skip pronunciation for those words.
- `config.py:47` `espeak_bin` only checked by health; `phone_gop.py:107` hard-codes `espeak-ng`.
- `slide_processor.py`: stateless class + singleton, wrong name (handles PDF).
- `database.py:35-36` redundant close; `conversation.py:54-58` `_llm` used once.
- `scripts/seed_demo.py:157-167` one-off backfill; `:78,93` minutes computed twice.
- **DECIDE** `models/user.py:20-21` `role`, `language` columns unused (dropping needs an Alembic migration); legacy refresh-token shims `schemas/auth.py:32`, `routers/auth.py:94,98`, `frontend/services/api.ts:19-27`, `services/auth.ts:24,30`.

### Backend special cases kept (genuine)
Groq Malay re-transcription (`pipeline.py:256-272`, `asr.py:187-197`), FLAC→WAV fallback, optional-model warnings, OpenCV frame-read timeouts and WebM fps quirks, the posture confidence cap, skipped tests for missing ffmpeg/LibreOffice/poppler, storage `try/except` around private-mode browsers, offline LLM fallbacks.

---

**Backend verified:** 79 tests, ruff clean, deployed, one real analysis end to end (throwaway account, synthetic no-face recording: STT, phone GOP, prosody, pillars, cue status, coaching). Face/pose maths not exercised (no face video available without using someone's recording).

---

## Frontend

### F1. One practice-mode registry `lib/modes.ts` (route, label, colour, partner, start URL, setup route) read by nav, home, onboarding, Mate, labels and the session page
- Route/function list six times: `TopNav.tsx:25-40`, `SideRail.tsx:14-19`, `home/page.tsx:18-47`, `MateChat.tsx:23`, `onboarding/page.tsx:68-72,267` (still says three), backend `services/assistant.py:36-47` (no `/impromptu`).
- Mode label maps five times with dead `Pronunciation` keys: `session/script.ts:43`, `results/[id]:22-23`, `progress:25`, `home:49`, `TaskList.tsx:25-30`; "talk ⇒ Presentation" at `session:1174`, `results:354`, `progress:51`, `home:145`; subtitle twice and drifted (`results:355-358`, `progress:43-47`).
- `/session?mode=…` built by hand in `conversation:38`, `interview:116`, `script:80`, `presentations/[id]:61`, `results:52`; "start, push, show error" three times (`interview:111-121`, `script:75-82`, `presentations/[id]:56-66`).
- `session/page.tsx:36` re-types the valid modes; "Alex" hard-coded at `:839,917,1263,1307,1362` (backend `practice_plans.py:137`); mode colours in render `:803-806`, `lib/utils.ts:18-20` keyed by hex, interview layout hard-codes them again.
- `script.ts` `Record<string,…>` forces dead `??` fallbacks (`page.tsx:314,321,597`).

### F2. One session-view helper `lib/sessionView.ts`: `overallScore`, title, subtitle, status (from the API's status, B2)
- **BUG** overall score: `progress:35-41` and `results:55-59` fall back to the mean of pillars; `useMyStats.ts:25`, `home:52`, `presentations/[id]:185`, `deckPipeline.ts:30` don't, so one session shows a number on Progress and "—" on Home.
- Pillar labels/keys copied though the API sends them: `progress:26-31`, `results:32`, `types:133`; `progress:148` `AREA_METRIC` hand map (pauses/length areas have no metric, so the focus card silently vanishes).
- `progress:157-163` re-implements `useMyStats` fetching; `results:323-325` repeats `load()`.

### F3. Split the 1,608-line session page by what changes together
`useLiveMedia` (camera, mic, recorder, one clock) · `useTurnTaking` (one `phase` state; STT, reply, TTS, interrupt, backchannels, check-ins) · `useTalkSlides` · `<CameraStage>` (tracking, lighting, posture tip) · `<ChatPanel>` shared by Interview and Conversation · thin page orchestrator. Session-only stores and `lib/lighting.ts` move next to it.
- **BUG** `store/useSessionStore.ts:16` `isCameraOn` defaults to true: a camera-permission error is invisible on a fresh load (`page.tsx:521-528,947,1018`).
- **BUG** talk mode: unmuting (`page.tsx:705-706,719`) attaches the speech listener, so the AI can start replying during a presentation.
- **BUG** talk mode: muting pauses the recorder (`:201`), so slide timings (`:78`) drift from the recording (`live/talk.py:80`).
- **BUG** talk mode: `VolumeMeter speaking={userSpeaking}` (`:1590`) is always false.
- **BUG** `:571` `liveService.start(...).catch(() => null)`: a failed start lets the user record a whole session, then `:648` redirects to `/login` and the recording is lost.
- Six ref-sync effects (`:173-178`) plus hand writes; forward-reference refs `startSpeechRef`, `triggerAIReplyRef`, `replyWhenQuietRef`; three clocks (`:67,132,135`).
- Dead: `lastPrevRef`, discarded `setFillerCount`, `fillerCntRef`, `stopSpeech` alias, `modeRef`; TTS-stop block ×3 (`:216,484,634`); mic bar ×2; chat list duplicated (`:1302-1380` vs `:1472-1579`); parallel `stateColor`/`stateInk`.
- `:181-189` global `console.error` monkey-patch; `:608` eslint-disable deps; magic delays `:229,487`, `isBusy` poll `:414`.
- `useFaceTracking` drives WPM through `onTick` and depends on the page's `activeRef` (`hooks.ts`).
- Lighting thresholds copied `page.tsx:983-986` vs `lib/lighting.ts:74-80`; `:436` WAV byte maths assumes `voiceTurns` layout; fillers counted two ways (`:406` vs `:752`); `fmt` and impromptu `mmss` vs `lib/format.ts`.

### F4. One auth module: token + user in one place, `requireSignIn()`, one logout, one `useHydrated`
- `isSignedIn()` + `push("/login?next=")` five times (`conversation:37`, `interview:112`, `script:44`, `presentations/[id]:57`, `impromptu:103`); `presentations/page.tsx` none and its 401 drops `next`.
- `services/api.ts:34-36` `signedOut()` clears the token but not the persisted user (`useUserStore`).
- `useSyncExternalStore` "hydrated" hack three times (`settings:15`, `profile:63`, `PrivacyControls:30`); `PrivacyControls:75-76` re-implements logout with a different target; `ConsentGate:29-30` is the only place the user is refreshed.
- `useUserStore` `isAuthenticated` never read; `profile`/`setProfile`/`UserProfile` duplicate `user`.
- **BUG** `onboarding/page.tsx:120` `updateProfile(...).catch(() => null)` then navigates: answers can be lost silently.
- Onboarding and profile option lists duplicated (`onboarding:27-66`, `profile:16-44`); must match backend `learner.py`, `schemas/auth.py:10-11`.
- `services/auth.ts:43,53` raw `api.fetch` bypassing 401 refresh; `uploadWithProgress` (`api.ts:80-102`) re-implements the refresh flow.

### F5. One deck module `lib/decks.ts`: typed in-progress statuses, status labels, title from filename, one `useDeck(id)` poller
- `services/presentation.ts:46` `DECK_IN_PROGRESS` copies backend `models/session.py:16` and is `Set<string>`.
- Status → text four times: `presentations/page.tsx:28-36,47-53`, `GenerationProgress.tsx:7-10`, `TaskList.tsx:84` (labels already differ).
- `.replace(/\.(pptx|pdf)$/i,"")` five times (`script:27,93`, `presentations/[id]:95`, `TaskList:74`, validation `presentations/page:158`).
- Three polling loops at three intervals (`presentations/page:152,184`, `[id]:23`); `presentations/page.tsx:83` compares a colour literal from `deckPipeline.ts:13`.
- Swallowed load errors shown as "none": `home:65`, `presentations/page:145-146`, `[id]:43`.

### F6. Grow the kit (`Row`, `ChoiceChip`, `Tabs`, `PasswordInput`, `Notice`) and build login, register, onboarding, presentations, interview, profile on it
- login/register duplicate input class, error box, eye toggle, submit (`login:16-18,36-76`, `register:10-12,37-81`); hand `rgba` error boxes and `#C2342C` (`NotificationBell:82`, `presentations/page:56`).
- Selected-chip style four times (`interview:30-52`, `profile:46-58`, `conversation:54-56`, onboarding ×3); tabs twice (`presentations/page:319-327`, `TaskList:144-153`); `.glass-card` + hand buttons vs kit `Card`.
- `settings/page.tsx:11` imports `Row` from the privacy feature; `ClayArt.tsx:7` imports `useIsDesktop` from `AuthShell` (which doesn't use it).
- localStorage + event store three times (`TaskList:96`, `Mascot:25-32`, `lib/theme.ts`); "is dark" three times; reduced-motion check four times; animation timings tied to CSS (`interview:90,101`, `DeleteButton:28`, `presentations/page:188`).

### F7. Services and types match the API
- `services/live.ts:5-23,91-132`: browser TTS model loading inside the HTTP service; `speak(voice="nova")` param never passed (backend `config.py:70` `coach_tts_voice` therefore unused, `conversation.py:125-126` `"_" in voice` guess).
- `services/live.ts:2` imports `blobFilename` from the deck service; `presentationService.health()` is app-wide; `MateChat` calls `api.post` directly.
- Types: one `LiveSession` for list and detail (`routers/live.py:159-172` `_summary` returns far less); `warnings?` on the wrong object; `pronunciation_flags` never produced; `details.confidence` untyped and re-declared (`results:114-123,479`); `ImpromptuResult` should be a union (forces `!` at `impromptu:301-303`); `BackendHealth`, `LiveContext` drift.
- `useMyStats` `thisWeek`/`byMode` never read; `setTimeout(…,0)` lint dodges (`useMyStats:63`, `progress:159`, `NotificationBell:37`); `.catch(() => setSignedIn(false))` shows a network error as signed-out.

### F8. Reference page states what the code does
- `methodology/page.tsx:97` lighting "90–190, ≥30" vs code 205/18; `:253` TTS chain is out of date; `:256` vs `:49-52` pronunciation contradicts itself; weights `:100,104` copied by hand from `scoring.py` (two languages, so a pointer comment on both sides).

### F9. Delete surplus
- `app/(app)/assessment/page.tsx` unreachable (only old notification rows) → a `next.config.ts` redirect.
- `StepDot total`, `DeckInsightsPanel defaultOpen`, `UploadCard`/`HoopShot` `processingLabel` default, `HoopShot` optional `steps`/`fill`, `ClayScene variant` default, `ClayArt` logo BG, `(auth)/layout.tsx` pass-through, redundant `press-effect`, `openItem` async, `SlideImage` key twice, `widgets.tsx` `PartnerBot theme`, `HeaderPulse color` default, exported-but-local `MpStatus`/`PostureIssue`/`postureIssue`.

---

## Comments (extra)
Restating banners and labels to remove, stale ones to fix: listed per file in the audit notes; swept file by file as each fix lands, then a final pass. Examples: `main.py:14,45,54`, `models/session.py:33,44,55`, `onboarding` step banners, `session/page.tsx` section labels (`:27,122,149,155,172,…`). Wrong: `home:86`/`TopNav:24` "three functions", `live/pipeline.py:3,9`, `live/__init__.py:4-6`, `extra_metrics.py:6-7,45`, `scoring.py:4-6,29`, `slide_processor.py:28,113`, `session/page.tsx:160,280,1397,1469`, `types:183`, `format.ts:1`, `schemas/live.py:61`.

## Tests (extra, done last)
- Shared fixtures to `conftest.py`: `client` duplicated in five files, `_sign_in` duplicated though `sign_in` exists, `_tone_wav` imported from `test_e2e` by three files, `test_script_writer.py:4` imports from `test_talk`.
- Tests next to their code: live-analysis tests in `test_practice.py:141-200`; auth/profile/upload tests in `test_live.py:210-282,356-372`; ai privates tested in `test_asr_silence_gaze.py:136-158`.
- Rewrite to behaviour: constant-restating asserts (B2 list), `test_deck_insights.py:30`, `test_learner.py:18-25` prompt wording, `test_asr_silence_gaze.py:109,112` price defaults, `test_phone_gop.py:74` table contents.
- Private-tied tests: `test_practice.py:110` `_fallback_qa_plan`, `:203-208` `_compose_intro` dead path, `test_asr_silence_gaze.py:54-61` `_transcribe_openai`.
- `test_phone_gop.py:9-10`: module-level torch skip also skips the pure-Python tests.
