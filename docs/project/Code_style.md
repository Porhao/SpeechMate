# Code Style

Match the code around you. These are the conventions it already follows.

## General

- **Small, honest code.** Prefer the platform (CSS, View Transitions, `<details>`, OfflineAudioContext) and libraries already installed over new dependencies or abstractions.
- **Comments explain why**, not what: the reason for a threshold, a bug that a guard prevents, a trade-off (`// Speech, then vision: both at once ran out of memory`).
- **Never invent data.** A metric that wasn't measured is `None`/`null` and shown as unavailable; fallbacks are labelled (`source: "rules"`).
- No dead code: delete unused components and functions rather than commenting them out.

## TypeScript / React (frontend)

- Next.js 16 App Router; check `node_modules/next/dist/docs/` before using an API: this version differs from older docs.
- Client components start with `"use client"`; pages are function components with a header comment saying what the page is for.
- Styling: Tailwind utility classes + CSS tokens (`var(--ink)`); **no hex in components**; shared pieces from `components/ui/kit.tsx`.
- State: local `useState`; refs for values read in callbacks/timers (`aiTypingRef`); zustand only for the signed-in user.
- Effects: no `setState` straight in an effect body (lint rule); derive during render or use `useSyncExternalStore` for browser-only values.
- Browser-only values (localStorage, matchMedia) never decide the server render: gate with `useSyncExternalStore(..., () => null)` or `suppressHydrationWarning`.
- Accessibility: `aria-label` on icon buttons, `aria-pressed` on toggles, `role="status"` on live text.
- Names: components `PascalCase`, hooks `useThing`, constants `UPPER_SNAKE`, files match the default export.
- Checks: `npx tsc --noEmit` and `npx eslint` must be clean.

## Python (backend)

- Python 3.12, FastAPI, async SQLAlchemy 2; type hints everywhere (`str | None`).
- Routers stay thin; logic lives in `app/services/`. Model loaders use `@load_once`.
- Pydantic models validate every request body and every LLM JSON output.
- Errors: user-facing `HTTPException` with a plain-English `detail`; analysis stages append to `warnings` instead of failing the whole run.
- Constants with units in the name (`END_SILENCE_SEC`, `MAX_STT_BYTES`) and a comment on why the value.
- Docstrings: one line on what it does and anything surprising.

## Copy (UI text)

- Plain English for a language learner: short sentences, no jargon ("words a minute", not "wpm"; "Next time", not "Improvement area").
- Speak to the user ("you"); quote their words when giving feedback.
- No exclamation marks in system messages; no emoji in UI chrome.

## Git

- Commits only when the author asks. Small, focused commits with a message saying why.
