# Local speech-to-text: removed (2026-10-14)

SpeechMate now sends all speech-to-text to a cloud, OpenAI-compatible Whisper API (Groq `whisper-large-v3`).
The local model (faster-whisper running Mesolitica's Malaysian Whisper) and the code-switching re-check
(`mesolitica/wav2vec2-xls-r-300m-mixed`) were deleted. This file records what was removed and how to bring it back.

The last commit with the local path is `6f89bed`. Every file below can be recovered from it:

```
git show 6f89bed:backend/app/services/live/asr.py > /tmp/asr_local.py
git checkout 6f89bed -- backend/scripts/convert_whisper.sh   # restores a deleted file
```

## Current setup (cloud only)

`backend/.env`:

```
OPENAI_API_KEY=gsk_...                          # Groq key: no quotes, no trailing characters
OPENAI_BASE_URL=https://api.groq.com/openai/v1
TRANSCRIPTION_MODEL=whisper-large-v3
STT_LANGUAGE=                                   # empty = auto-detect (keeps Manglish as spoken)
```

All three callers use the API: live turns (`POST /api/stt` in `routers/conversation.py`), session analysis
(`services/live/asr.py`, `verbose_json` with word timestamps), and rehearsal transcripts
(`services/coach/transcription.py`). With no key, `/api/stt` returns 503 and the session page lets the user type.

Note: the audio leaves the machine. Groq `whisper-large-v3` has not been benchmarked on our Manglish set.
The local Mesolitica model scored 6.1% WER on it, and standard Whisper `medium` scored 51.3%
(`docs/benchmarks/stt-benchmark-2026-09-30.md`).

## What was removed

| Where | What |
|---|---|
| `backend/app/services/live/asr.py` | `_whisper_model`, `_codeswitch_model`, `whisper_segments` (VAD, silence-hallucination filter, context prompt), `_transcribe_local`, `is_malaysian_model`, `whisper_language` (now `stt_language`), the local-first branch in `transcribe` |
| `backend/app/services/coach/transcription.py` | `_transcribe_local` and the local-first branch |
| `backend/app/routers/conversation.py` | `_local_stt` and the local branch in `/stt` |
| `backend/app/services/live/_ml.py` | `local_stt()` |
| `backend/app/routers/health.py` | `local_ml.faster_whisper` |
| `backend/app/config.py` | `cloud_stt`, `whisper_model_size`, `whisper_cpu_threads` |
| `backend/requirements-ml.txt` | `faster-whisper==1.0.3` (torch/transformers stay: pronunciation, emotion, TTS) |
| `backend/.env`, `.env.example` | `CLOUD_STT`, `WHISPER_MODEL_SIZE`, `WHISPER_CPU_THREADS` |
| Deleted files | `backend/scripts/convert_whisper.sh`, `backend/scripts/benchmark/bench_stt.py`, `backend/scripts/benchmark/prepare_data.sh`, `backend/tests/test_asr_silence.py` |
| Frontend | session page checks only `providers.openai`; methodology page text; comments in `voiceTurns.ts`, `services/live.ts` |
| `README.md`, `docs/project/Testing.md` | Speech-recognition rows and the "everything local" claim |

Not touched: `fine-tune/` (LoRA fine-tune of the local model) and `docs/benchmarks/`. They are research
records. The fine-tune eval scripts (`eval_routing.py`, `eval_finetune.py`) import the removed
`asr.whisper_segments` / `asr._transcribe_local`, so they only run against `6f89bed` or after a restore.
The model weights in the `speechmate_model_cache` Docker volume (`/models/ct2/...`) were also left in place.

## How to bring the local model back

1. Restore the code from `6f89bed`:
   ```
   git checkout 6f89bed -- backend/app/services/live/asr.py backend/app/services/coach/transcription.py \
     backend/app/services/live/_ml.py backend/app/routers/health.py \
     backend/scripts/convert_whisper.sh backend/scripts/benchmark backend/tests/test_asr_silence.py
   ```
   Then re-apply by hand (these files changed for other reasons since):
   - `backend/app/config.py`: add back `cloud_stt: bool = False`, `whisper_model_size: str = "small"`, `whisper_cpu_threads: int = 0`.
   - `backend/app/routers/conversation.py`: add back `_local_stt()` and, in `/stt`, `if local_stt(): return {... "engine": "faster-whisper"}` before the API call. Rename `stt_language()` calls back to `whisper_language(None)`.
   - `backend/requirements-ml.txt`: add `faster-whisper==1.0.3`.
   - `frontend/app/(app)/session/page.tsx`: `health.local_ml?.faster_whisper || health.providers?.openai`.
2. Convert the Malaysian model (writes into the model-cache volume):
   ```
   ./backend/scripts/convert_whisper.sh mesolitica/Malaysian-whisper-large-v3-turbo-v3
   ```
3. `backend/.env`:
   ```
   CLOUD_STT=false
   WHISPER_MODEL_SIZE=/models/ct2/malaysian-whisper-large-v3-turbo-v3
   WHISPER_CPU_THREADS=8
   ```
4. Rebuild with ML packages: `docker compose up -d --build backend` (the Dockerfile's `INSTALL_ML` defaults to `true`).
5. Check: `curl localhost:8000/api/health` shows `"faster_whisper": true`, then run the tests inside the container.

Expect about 2–3 s per turn on CPU with 8 threads (`docs/benchmarks/stt-benchmark-2026-10-01.md`).
