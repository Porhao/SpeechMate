# Deploying SpeechMate to Vercel

Pipeline: `.github/workflows/deploy-vercel.yml`, run by hand from GitHub → Actions → "Production Deployment to Vercel" → Run workflow.
It runs three jobs in order: Alembic migrations against Supabase, then the backend, then the frontend.

## One-time setup

### 1. Supabase (Postgres)
1. Create a free project at supabase.com.
2. Project Settings → Database → Connection string. Use the **session pooler** or **direct** string (port 5432),
   not the transaction pooler (6543), and change the scheme to `postgresql+asyncpg://`:
   `postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
3. Free projects pause after about a week without traffic; un-pause from the dashboard.

### 2. Vercel (two projects from this one repo)
1. Import the GitHub repo twice at vercel.com/new:
   - `speechmate-frontend`: Root Directory `frontend`, framework Next.js.
   - `speechmate-backend`: Root Directory `backend`, framework FastAPI (only after the port below).
2. In each project, turn **off** automatic Git deployments if you only want the pipeline to deploy
   (Settings → Git → Ignored Build Step: `exit 0`).
3. Create a token: vercel.com/account/tokens.
4. Find the IDs: run `vercel link` in each folder and read `.vercel/project.json` (`orgId`, `projectId`).

### 3. Environment variables (Vercel → Project → Settings → Environment Variables, "Production")

Frontend:

| Name | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://speechmate-backend.vercel.app/api` (your backend's production domain) |

Backend (same values as `backend/.env`):

| Name | Value |
|---|---|
| `DATABASE_URL` | the Supabase string from step 1 |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ORIGINS` | `["https://speechmate-frontend.vercel.app"]` |
| `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `TRANSCRIPTION_MODEL` | Groq key, `https://api.groq.com/openai/v1`, `whisper-large-v3` |
| `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | Gemini endpoint, key, `gemini-3.5-flash-lite` |
| `USE_LOCAL_ML` | `false` |

### 4. GitHub (repo → Settings → Secrets and variables → Actions)

| Secret | Value |
|---|---|
| `VERCEL_TOKEN` | the token from 2.3 |
| `VERCEL_ORG_ID` | `orgId` |
| `VERCEL_FRONTEND_PROJECT_ID` | frontend `projectId` |
| `VERCEL_BACKEND_PROJECT_ID` | backend `projectId` |
| `DATABASE_URL` | the Supabase string (used by the migration job) |

Variable (Variables tab, not Secrets): `DEPLOY_BACKEND=true` once the backend port is done. Until then
the backend job is skipped and only migrations and the frontend run.

## The backend port (needed before `DEPLOY_BACKEND=true`)

The backend runs in a Docker container today. A Vercel Python function has no system programs,
no lasting disk, a 500 MB size cap and a 300 s time limit on Hobby, and work started after the
response is not guaranteed to finish. What has to change:

| Today | On Vercel | Change |
|---|---|---|
| `tasks.spawn(...)` runs the session analysis, coach feedback and example-video pipelines after the response | Frozen after the response | Run the job inside its own request (a "process" call the frontend makes and waits on), within 300 s |
| `ffmpeg` (every recording is converted to 16 kHz WAV; example videos) | Not installed | `imageio-ffmpeg` ships a static ffmpeg binary as a pip package; point `FFMPEG_BIN` at it |
| LibreOffice + `pdftoppm` (.pptx → slide images) | Not installed | Accept PDF only and render pages with PyMuPDF |
| `./storage` (recordings, slides, videos) | Lost between requests | Vercel Blob (free on Hobby within its limits) |
| Kokoro container (partner voice) | No containers | Kokoro in the browser (`kokoro-js`), below |
| `requirements-ml.txt` (torch, MediaPipe, wav2vec2, librosa: 4.7 GB image) | Too big | Dropped. Pronunciation, eye contact, posture, emotion and prolongation metrics then report "unavailable" (the code already handles this), and the Malaysian TTS narrator is gone |

## AI partner's voice: Kokoro in the browser

Kokoro-82M (Apache-2.0, the model you use now) also runs in the user's browser through
`kokoro-js` (Transformers.js, WebGPU or WASM). No server: the model (~80 MB at q8) downloads
once and the browser caches it. The same voices work (`af_heart`, `bf_emma`, …). WebGPU needs a
Chromium browser with a real GPU; others use WASM (q8), which is slower. Implemented in
`frontend/services/live.ts` (`conversationService.speak`): until the model has loaded, replies use the
backend's `/api/tts/speak`, and failing that the browser's built-in voice.
