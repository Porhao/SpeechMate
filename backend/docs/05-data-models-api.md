# Data Models & API Contract

## Database schema (Postgres)

### `sessions`
One row per uploaded deck + its Ideal Presentation Agent output.
```sql
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),          -- if/when auth is added; nullable for single-user v1
  original_filename TEXT NOT NULL,
  pptx_storage_path TEXT NOT NULL,
  voice_sample_storage_path TEXT,              -- nullable: user may skip voice cloning
  requirement_prompt TEXT,                     -- audience/purpose free text
  status TEXT NOT NULL DEFAULT 'queued',       -- queued|processing_slides|generating_scripts|synthesizing_audio|assembling_video|complete|failed
  error_detail TEXT,
  voice_cloning_used BOOLEAN,                  -- set once Stage 3 completes/falls back
  slide_count INT,
  video_storage_path TEXT,                     -- set on completion
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### `slides`
One row per slide within a session.
```sql
CREATE TABLE slides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  slide_index INT NOT NULL,
  png_storage_path TEXT,
  script_text TEXT,
  script_word_count INT,
  audio_storage_path TEXT,
  status TEXT NOT NULL DEFAULT 'pending',      -- pending|rendered|scripted|synthesized|failed
  error_detail TEXT,
  UNIQUE(session_id, slide_index)
);
```

### `practice_sessions`
One row per practice/coaching attempt against a session.
```sql
CREATE TABLE practice_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  audio_storage_path TEXT NOT NULL,
  recording_granularity TEXT NOT NULL DEFAULT 'whole_deck',  -- whole_deck|per_slide
  status TEXT NOT NULL DEFAULT 'queued',       -- queued|transcribing|analyzing|complete|failed
  transcript TEXT,
  metrics JSONB,                                -- {wpm, pause_count, filler_word_count, duration_sec, ...}
  feedback JSONB,                                -- {encouragement, observations: [{observation, impact, suggestion}]}
  audience_feedback JSONB,                       -- Phase 3, nullable
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### `chat_messages`
```sql
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  practice_session_id UUID REFERENCES practice_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,                            -- user|assistant
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## REST API contract

### Ideal Presentation Agent endpoints
```
POST /sessions
  multipart/form-data: pptx (file), voice_sample (file, optional), requirement_prompt (string, optional)
  → 201 { session_id, status: "queued" }

GET /sessions/{id}
  → 200 {
      session_id, status, slide_count,
      slides_progress: { rendered: N, scripted: N, synthesized: N },  // optional finer-grained progress
      error_detail
    }

GET /sessions/{id}/video
  → 200 (video stream / signed URL) — only valid once status == "complete"

GET /sessions/{id}/scripts
  → 200 { slides: [{ slide_index, script_text, word_count }] }
```

### Coach Agent endpoints
```
POST /sessions/{id}/practice
  multipart/form-data: audio (file), recording_granularity (string, optional, default "whole_deck")
  → 201 { practice_id, status: "queued" }
  → 409 if session.status != "complete"

GET /sessions/{id}/practice/{practice_id}
  → 200 {
      practice_id, status, metrics, feedback, audience_feedback
    }

POST /sessions/{id}/practice/{practice_id}/chat
  json: { message: string }
  → 200 { role: "assistant", content: string }

GET /sessions/{id}/practice/{practice_id}/chat
  → 200 { messages: [{ role, content, created_at }] }
```

## Notes on the contract
- All long-running operations (session creation, practice submission) return immediately with a `queued` status and an ID — frontend polls or subscribes for updates. Never block an HTTP request on a multi-minute pipeline.
- `error_detail` should be human-readable enough to surface directly in the UI for a first version (e.g., "Voice cloning failed after 3 retries — used fallback voice" is a *warning*, not necessarily a `failed` status — distinguish soft-fallback warnings from hard failures).
- Keep `feedback` and `metrics` as JSONB rather than separate normalized tables — this data is read as a unit, rarely queried/filtered by its internal fields, and its shape may evolve (e.g., adding Audience Agent fields in Phase 3) without a migration.
