# Frontend UI Spec — Three-Stage User Journey

Progressive disclosure: only show controls relevant to the user's current stage. Don't render all three stages' UI on one page at once.

## Stage 1: Setup & Configuration
Route: `/new` (or the app's home/upload screen)

Elements:
- File upload for `.pptx` (drag-and-drop + browse, show filename + slide-count preview once parsed if feasible client-side, otherwise just filename)
- Slide preview area — once the file is selected, show a lightweight preview if possible (rendering full slide images client-side is unnecessary work; a placeholder icon + filename is fine for v1)
- Voice sample control: record-in-browser (`MediaRecorder`, a short fixed prompt like "Please read this sentence aloud") OR upload an existing audio file. Make this clearly optional — show a note like "Skip to use a standard voice instead."
- Requirement text field: free text for audience/purpose (e.g., "for a non-specialist audience, English course presentation")
- "Generate" button — disabled until at minimum the pptx is uploaded
- On submit: `POST /sessions`, then navigate to the progress view with the returned `session_id`

## Stage 2: Generation Progress
Route: `/sessions/{id}/generating` (or a modal/panel state on the same page)

Elements:
- A **named, multi-step progress indicator**, not a generic spinner. Steps map directly to backend status values:
  - "Parsing slide content" (`processing_slides`)
  - "Generating narration script" (`generating_scripts`)
  - "Synthesizing audio track" (`synthesizing_audio`)
  - "Assembling video" (`assembling_video`)
  - "Complete" (`complete`)
- Poll `GET /sessions/{id}` every ~3-5s; update the active step and mark completed steps with a check.
- If `status == "failed"`, show `error_detail` plainly and offer a retry action.
- If a soft fallback occurred (e.g., voice cloning failed, standard voice used), surface this as a small non-blocking notice once generation completes — don't hide it, but don't block progress on it either.
- On `complete`, auto-navigate (or show a clear CTA) to Stage 3.

## Stage 3: Interactive Coaching & Practice Environment
Route: `/sessions/{id}/practice`

This is the main working screen — the paper's UI splits it into clear zones; replicate that:
- **Video panel:** the generated ideal presentation video (`<video>` element, standard controls).
- **Script panel:** the per-slide narration script text, ideally synced/highlighted to the currently playing slide segment if you track segment timestamps; otherwise a simple scrollable list of `slide N: script text` is fine for v1.
- **Recording controls:** record (or upload) the user's own practice audio via `MediaRecorder`. Clear record/stop/re-record affordances. On submit: `POST /sessions/{id}/practice`.
- **Coach panel:** once a practice recording is submitted and analyzed:
  - Show the **Encouragement** line first, prominently.
  - Show the **OIS feedback** as a structured card (or cards, if multiple observations) — Observation / Impact / Suggestion as visually distinct sub-sections, not one paragraph blob.
  - Below that, a **chat input** for follow-up questions, with the running chat history rendered as a normal message thread.
  - Poll `GET /sessions/{id}/practice/{practice_id}` after submission until `status == "complete"`, showing a lightweight "analyzing your practice..." state in the meantime.

## Design system notes
- **State-aware, not everything-at-once:** irrelevant controls for the current stage should not render at all (not just be disabled) — this was explicitly called out in the paper as reducing cognitive load, and it's cheap to do with route-based or state-based conditional rendering.
- **Multi-modal redundancy is a feature, not clutter:** presenting the same content as video + text script + (later) written feedback serves different learning preferences deliberately — don't cut the script panel just because the video exists, they serve different users/moments.
- Keep visual design plain/functional for v1 — this is a functionality-first build. Defer polish (animations, custom theming) until the pipeline itself works end-to-end.

## What to stub first when building
1. Build Stage 1's upload form against a mocked `POST /sessions` that just returns a fake ID — verify the form/validation works before the real backend exists.
2. Build Stage 2's polling UI against a mocked endpoint that steps through statuses on a timer — verify the progress UI renders each state correctly before wiring real polling.
3. Build Stage 3's video+script panel against a hardcoded video URL + fake script JSON — verify layout before the real pipeline produces real files.
4. Only wire all three to the real backend once each stage's UI shell is proven with fake data — this lets frontend and backend work proceed in parallel.
