# Project Overview — PresentCoach Clone

## What this is
A dual-agent AI system that helps a user practice a presentation. It has two halves:

1. **Ideal Presentation Agent** — takes the user's slide deck + a voice sample, and produces a benchmark video: the slides narrated in the user's own cloned voice.
2. **Coach Agent** — takes the user's own recorded practice run and compares it against the benchmark, returning structured, conversational feedback.

The point is to close the loop: *see what good looks like → rehearse → get targeted feedback → rehearse again*. This is inspired by the paper "PresentCoach: Dual-Agent Presentation Coaching through Exemplars and Interactive Feedback" (Chen et al., HKUST-Guangzhou, 2025, arXiv:2511.15253). This project is an original re-implementation, not a copy of their code (they didn't publish any) — read the paper's public description for concepts, but all engineering decisions here are our own.

## Why build this
- Concrete portfolio piece combining agentic AI orchestration, multimodal generation (VLM + voice + video), and full-stack product engineering — all things already in scope of my skill set (n8n automation, LLM orchestration, FastAPI, Next.js).
- Good testbed for practicing agent-to-agent pipelines and structured LLM output (OIS feedback format) rather than freeform chat.

## Scope decisions for v1
To avoid building the whole paper at once, this is split into two phases:

- **Phase 1 (MVP):** Ideal Presentation Agent only. Input: `.pptx` + voice sample. Output: narrated benchmark video. No coaching yet.
- **Phase 2:** Coach Agent. Input: user's own practice recording + Phase 1 outputs. Output: structured OIS feedback + a follow-up chat.
- **Phase 3 (stretch):** Audience Agent (simulated listener reactions), longitudinal progress tracking, multi-session history.

Do not build Phase 2/3 pipes before Phase 1 is fully working end-to-end (upload → video playback). Get one deck through the whole pipeline before generalizing.

## Non-goals for v1
- No body language / webcam / gesture analysis (paper explicitly scopes this out too — audio + slides only).
- No mobile app — web only.
- No multi-tenant auth/billing system — single-user or simple auth is enough to start.
- No real-time / streaming feedback — batch processing per practice session is fine.

## Read order for the rest of these docs
1. `01-architecture.md` — system diagram, data flow, the two agents
2. `02-tech-stack.md` — concrete model/library choices and why
3. `03-ideal-presentation-agent-spec.md` — detailed pipeline for Phase 1
4. `04-coach-agent-spec.md` — detailed pipeline for Phase 2
5. `05-data-models-api.md` — DB schema + REST API contract
6. `06-frontend-ui-spec.md` — the 3-stage user journey and screens
7. `07-implementation-roadmap.md` — build order, milestones, what to stub first

## Core design principles to keep in mind while building
- **Exemplar before evaluation.** Never let the Coach Agent run before an Ideal Presentation video exists for that deck — it has nothing to compare against.
- **Structured over freeform feedback.** The Coach Agent's primary output must be Observation → Impact → Suggestion, under ~150 words, not a wall of generic advice.
- **Graceful degradation.** Voice cloning fails sometimes (bad sample, provider outage) — always have a standard-TTS fallback so the pipeline never hard-fails.
- **Progressive disclosure UI.** Don't show all controls at once — the user only sees what matches their current stage (upload → generating → practicing/coaching).
