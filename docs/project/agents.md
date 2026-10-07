# Guide for AI coding agents

Read this before changing anything. It's the rules and the workflow that are easy to get wrong in this repo.

## Hard rules

1. **No git commands** (status, commit, checkout, anything) unless the author explicitly allows it in the current conversation.
2. **Never invent data**: no placeholder names, scores or sample stats in the UI. Unmeasured = unavailable.
3. **Scope is three functions**: Conversation, Mock interview, Presentation practice (+ Q&A). Don't bring back pronunciation mode, coach chat, dashboard or reports pages.
4. **Next.js 16 is not the Next.js you know**: read `frontend/node_modules/next/dist/docs/` before using an API (see `frontend/AGENTS.md`).
5. **Don't restart the backend while an analysis is running**: it kills in-process background jobs. Check first:
   `docker compose exec -T db psql -U speechmate -d speechmate_db -c "select id from live_sessions where status='analyzing'"`.
6. **Memory is tight** (WSL ~7.6 GB by default): don't load the analysis models in a second process inside the backend container; it gets OOM-killed and can take the backend down.

## Workflow

| Task | How |
|---|---|
| Run everything | `docker compose --profile ollama --profile tts up -d --build` (repo root; `backend/` has its own compose file, don't use it) |
| Deploy a change | Code is copied into images, no bind mounts: `docker compose up -d --build --no-deps frontend` (or `backend`); without `--no-deps` compose may restart the backend too |
| Backend tests | Copy the working tree into the container and run pytest (exact commands in Testing.md) |
| Frontend checks | `npx tsc --noEmit && npx eslint .` in `frontend/` |
| See the UI | Playwright image; load from `http://localhost:3000` (CORS) and route to the host IP (Testing.md) |
| Demo login | `demo@speechmate.dev` / `Demo1234!` (seeded locally) |

## Where things are

| Need | Look in |
|---|---|
| Product intent | `docs/project/PRD.md` |
| Colours, components, 3D, motion | `docs/project/Design_system.md`, `frontend/DESIGN.md` |
| Services, flows, endpoints | `docs/project/Architecture.md` |
| Tables and JSON shapes | `docs/project/Database.md` |
| Security and privacy rules | `docs/project/Security.md` |
| Conventions | `docs/project/Code_style.md` |
| How a metric is computed | the Reference page data (`frontend/app/(app)/methodology/page.tsx`) and `backend/app/services/live/` |
| Confidence model | `backend/docs/confidence-model.md` |
| Speech recognition and fine-tuning | `docs/manglish-transcription-spec.md`, `fine-tune/` |

## When you change…

- **A metric or threshold** → update the Reference page row (method, range, worked example) and add a test with the worked number.
- **The analysis JSON** → readers must tolerate older sessions missing the new key; update Database.md.
- **Turn-taking** (`lib/voiceTurns.ts`, session page) → the AI must never reply while the user is speaking or while their words are still being transcribed (`isBusy`).
- **UI** → tokens only, kit components, both themes, 390 px wide, keyboard reachable, reduced motion.
- **Anything user-visible** → plain-language copy (Code_style.md).

## Done means

Tests and checks pass, it's deployed, and you looked at it in a browser. Say plainly what you didn't verify.
