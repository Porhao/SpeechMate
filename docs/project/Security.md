# Security & Privacy

SpeechMate handles **voice, face video, resumes and personal goals**, which is sensitive personal data under Malaysia's PDPA 2010. This page lists what's in place and what's still open.

## In place

| Area | Control | Where |
|---|---|---|
| Passwords | bcrypt with per-password salt | `backend/app/auth.py` |
| Sessions | JWT (HS256) access token 30 min (sent as a Bearer header) + refresh token 7 days in an **httpOnly, SameSite=Lax cookie** scoped to `/api/auth` and **rotated** on every refresh; typed (`access` / `refresh`) so one can't be used as the other. Set `COOKIE_SECURE=true` when served over HTTPS | `routers/auth.py`, `services/api.ts` |
| Rate limits | Login 10 tries / 5 min per email and 30 / 5 min per client; sign-up 10 / 10 min; AI chat 30/min, STT and TTS 60/min, interview plan 6/min, resume 10/min; 429 with `Retry-After` | `app/limits.py` |
| Upload size | Recording 500 MB, practice audio 300 MB, deck 100 MB, voice sample 25 MB (streamed to disk, partial files removed); STT turn 15 MB, resume 5 MB (read with a cap); 413 above the limit | `app/limits.py`, routers |
| Secret | `SECRET_KEY` from `backend/.env` (64-char random); the code default `change-me-in-production` must never ship | `.env` (git-ignored) |
| Authorisation | Every live session, result, notification and owned deck is looked up **by owner**; another user's id returns 404 (tested). Decks uploaded while signed out have no owner and are reachable by id. *Fixed 2026-10-07: deck endpoints had no owner check.* | `_own_session`, `get_session_or_404` |
| CORS | Only `CORS_ORIGINS` (default `http://localhost:3000`) | `main.py` |
| Input validation | Pydantic schemas on every body; turn lists capped (200); deck must be .pptx/.pdf; narrator voice whitelisted | `schemas/`, routers |
| LLM output | JSON validated against schemas; re-prompted once; "stronger answers" checked so they don't invent facts the user never said | `practice_plans.py` |
| Secrets in repo | `.env`, `.env.*`, `fine-tune/data/`, `fine-tune/eval/` git-ignored (recordings never committed) | `.gitignore` |
| Local processing | Speech, vision and LLM run on the user's machine by default; nothing leaves it unless OpenAI/ElevenLabs keys are configured | `config.py` |
| Deletion | Deleting a session removes its recording and analysis (cascade) | `live.py` |

## Open risks (priority order)

| # | Risk | Impact | Fix |
|---|---|---|---|
| 1 | Access token (30 min) still in `localStorage` | An XSS could use it until it expires (the refresh token is now out of reach) | Keep strict output encoding (React escapes by default; the only `dangerouslySetInnerHTML` is the static theme script); later, hold the access token in memory only |
| 2 | Rate limits are in-memory, per process | Reset on restart; not shared across workers; behind a proxy every client shares one IP (per-email login limit still holds) | Redis-backed limiter and `X-Forwarded-For` handling if deployed |
| 3 | Slide images (`/sessions/{id}/slides/{n}/image`) are served to anyone with the deck id | The id is a random UUID, so it's a capability URL; an `<img>` can't send the Bearer token | Signed short-lived image URLs if decks become sensitive |
| 4 | Demo account shown on the login page | Shared account in a deployed build | Set `NEXT_PUBLIC_SHOW_DEMO_LOGIN=false` and don't seed demo data outside dev |
| 5 | Logout clears the cookie but doesn't revoke tokens server-side | A refresh token copied before logout works until it expires (7 days) | Store a token id per user and reject old ones |
| 6 | No account deletion / data export | PDPA access and erasure requests are manual | Add `DELETE /users/me` (cascade + storage) and an export endpoint |
| 7 | Recordings retained indefinitely | More data held than needed | Retention job (e.g. delete raw video after analysis, keep results) |

## Privacy rules for contributors

- Never log transcripts, resume text or tokens. Log ids and counts.
- Recordings of real people (fine-tune data) require **signed consent** and stay out of git.
- New third-party calls must be opt-in by configuration and documented here.
- Anything shown publicly (e.g. the contact dock) uses only what the owner chose to publish.

## Reporting a vulnerability

Contact the project author privately (not in an issue); include steps to reproduce.
