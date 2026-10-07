# Testing

Manual test scripts per feature (accounts, conversation, interview, presentation, progress, fallbacks) are in the root [`TESTING.md`](../../TESTING.md). This page covers automated checks and how to run them.

## Backend (pytest)

61 tests in `backend/tests/`: units for every metric (fluency, fillers, stutter, confidence cues, scores), the live-session API end to end with fake models, deck insights, practice coaching, TTS, notifications, and ASR safety (silence → empty transcript, context echo dropped).

The code is baked into the Docker image, so run the **working tree** inside the running container:

```bash
cd backend
D=/tmp/bt_$(date +%s)
docker compose -f ../docker-compose.yml exec -T backend mkdir -p $D
for x in app tests scripts pytest.ini; do docker compose -f ../docker-compose.yml cp $x backend:$D/; done
docker compose -f ../docker-compose.yml exec -T backend pip install -q pytest pytest-asyncio aiosqlite imageio-ffmpeg
docker compose -f ../docker-compose.yml exec -T -w $D backend python -m pytest -q -p no:cacheprovider
```

Rules:
- Every new metric or rule gets a test with a **worked number** (e.g. `test_confidence_is_per_minute_not_per_session`).
- Regressions get a test named after the bug (`test_fluency_ignores_turn_gaps_in_a_conversation`).
- Tests never call real models or the LLM: monkeypatch `_whisper_model`, LLM clients, etc.

## Frontend

```bash
cd frontend
npx tsc --noEmit        # types (ignore stale .next/dev errors for deleted routes)
npx eslint .            # lint, incl. React hooks rules
```

There is no unit-test runner on the frontend; keep logic small and covered by types, and verify behaviour in a browser.

## Browser checks (Playwright)

Screenshots and flows run in the Playwright image against the running stack. The browser must load the app from `http://localhost:3000` (the only CORS origin); route requests to the host IP from inside the container:

```python
ctx.route("http://localhost:3000/**", lambda r: r.fulfill(response=r.fetch(url=r.request.url.replace("localhost", HOST_IP))))
```

Use `--use-fake-device-for-media-stream` for camera/mic. Abort `POST /api/live` in tests so no real sessions are created in the demo account.

## Fine-tune data

`fine-tune/scripts/prepare_own.py --selftest` checks the recording-to-dataset conversion (formats, silence, rejects, idempotent re-runs).

## Evaluation (research)

| Component | Method | Doc |
|---|---|---|
| Speech recognition | WER by language (`backend/scripts/benchmark/bench_stt.py`, `--real` for own recordings) | `docs/benchmarks/` |
| Confidence | Spearman vs. 2–3 blind raters | `backend/docs/confidence-model.md` |
| Feedback quality | UAT Likert: specific, actionable, accurate | `docs/AI_MATRIX.md` |

## Before you deploy

- [ ] Backend tests pass; `tsc` and `eslint` clean.
- [ ] Nothing is `analyzing` (a backend restart interrupts analyses): check `live_sessions.status`.
- [ ] `docker compose up -d --build --no-deps <service>`, then load `/home`, a session and a results page.
