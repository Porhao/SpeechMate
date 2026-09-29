# System Architecture

## High-level flow

```
                          ┌─────────────────────────────┐
                          │        USER INPUT            │
                          │  .pptx file + voice sample   │
                          │  + optional requirement text │
                          └──────────────┬───────────────┘
                                         ▼
                    ┌──────────────────────────────────────┐
                    │       IDEAL PRESENTATION AGENT         │
                    │  1. Slide → PNG conversion             │
                    │  2. VLM reads each slide → script      │
                    │  3. Voice cloning → narration audio    │
                    │  4. Assemble slides+audio → MP4         │
                    └──────────────┬─────────────────────────┘
                                   ▼
                    ┌──────────────────────────────────────┐
                    │        Stored per-session artifacts    │
                    │  slide_pngs[], scripts[], ideal_audio[]│
                    │  ideal_video.mp4                       │
                    └──────────────┬─────────────────────────┘
                                   ▼
                     User watches video, records own
                     practice audio/video of the same deck
                                   ▼
                    ┌──────────────────────────────────────┐
                    │            COACH AGENT                 │
                    │  1. Multimodal comparison               │
                    │     (slide + ideal script + ideal audio │
                    │      + user audio)                      │
                    │  2. Structured OIS feedback generation   │
                    │  3. Conversational follow-up (chat)      │
                    └──────────────┬─────────────────────────┘
                                   ▼
                          Feedback shown to user
                          + persisted chat history
```

## The two agents are separate services, not one monolith
Treat `IdealPresentationAgent` and `CoachAgent` as independent backend modules/services with their own job queues. They share a database (session, deck, slide, script records) but have no direct coupling — the Coach Agent only *reads* what the Ideal Presentation Agent produced.

Reasons to keep them separate:
- They have very different runtime profiles: Ideal Presentation Agent is slow/batch (video rendering, TTS), Coach Agent is closer to request/response (though still async due to LLM calls).
- Lets you build and test Phase 1 completely before touching Phase 2.
- Mirrors the paper's own framing of "dual-agent" — useful to keep them conceptually distinct in code, not just prose.

## Processing model: async job queue, not synchronous request/response
Slide-to-video generation takes minutes (VLM calls per slide + TTS + video encoding). Do **not** do this inside an HTTP request handler.

Recommended pattern:
1. `POST /sessions` creates a session + uploads file → returns `session_id` immediately, status = `queued`.
2. A background worker (Celery/RQ/arq, or a simple asyncio task queue for v1) picks up the job, runs the 4-stage pipeline, updates `status` at each stage (`processing_slides`, `generating_scripts`, `synthesizing_audio`, `assembling_video`, `complete`, `failed`).
3. Frontend polls `GET /sessions/{id}` or subscribes via SSE/WebSocket for live progress — this powers the "transparent pipeline" progress UI (see `06-frontend-ui-spec.md`).

For a solo-dev v1, a simple in-process asyncio task queue (or even a synchronous script triggered by a cron/worker dyno) is fine — don't over-engineer distributed queueing before you need it. Upgrade to Celery + Redis only once this becomes a real bottleneck.

## Per-slide granularity is the core unit of work
Every stage of the Ideal Presentation Agent operates per-slide, not per-deck:
- 1 PNG per slide
- 1 VLM call per slide → 1 script segment
- 1 TTS call per script segment → 1 audio clip
- Final assembly stitches N slide+audio segments into one video

This means the pipeline is naturally parallelizable across slides (fan-out VLM/TTS calls, fan-in for assembly) and naturally resumable (cache completed slides, retry only failed ones instead of redoing the whole deck).

## External dependencies and failure isolation
Each external call (VLM API, voice cloning API, video encoding) is a potential point of failure. Wrap each in:
- A timeout
- A retry with backoff (2–3 attempts)
- A fallback path where one exists (see `03-ideal-presentation-agent-spec.md` for the TTS fallback specifically)
- A per-slide error state, so one bad slide doesn't kill the whole deck's generation

## Storage layout
```
/storage/{session_id}/
  original.pptx
  voice_sample.wav
  slides/
    slide_1.png, slide_2.png, ...
  scripts/
    slide_1.json   # {text, word_count, model, generated_at}
  audio/
    slide_1.wav
  ideal_video.mp4
  practice/
    {practice_id}/
      user_audio.wav (or user_video.mp4)
      feedback.json
      chat_history.json
```
Use object storage (S3-compatible: AWS S3, Cloudflare R2, or Supabase Storage since you're already using Supabase) rather than local disk once this leaves your laptop — local disk is fine for local dev only.
