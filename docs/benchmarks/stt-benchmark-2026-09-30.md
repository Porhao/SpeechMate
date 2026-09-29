# Speech-to-text benchmark — 30 Sep 2026

Which Whisper model SpeechMate should use to transcribe Malaysian speakers, on the
development machine (CPU only, WSL 2 with 7.6 GB RAM, faster-whisper int8).

## Test set (303 s of audio, 33 utterances)

| Category | Source | Utterances |
|---|---|---|
| Malay, real speakers | Google FLEURS `ms_my` **test** split (read speech by Malaysian speakers) | 25 |
| English, Malaysian accent | Local Malaysian TTS (`mesolitica/Malaysian-TTS-0.6B-v1`, voices husein / idayu / haqkiem) | 4 |
| Manglish (code-switched) | Same TTS | 4 |

Every configuration runs exactly as the app does: VAD filter, the app's initial prompt,
`condition_on_previous_text=False`, beam size 5. WER = word error rate after lower-casing
and removing punctuation.

## Results

| Model | Language token | WER Malay | WER English | WER Manglish | **WER all** | Time per 5 s turn | RAM |
|---|---|---|---|---|---|---|---|
| Whisper `medium` (previous setting) | `en` | 59.5% | 6.0% | 17.0% | 51.3% | 2.20 s | +1174 MB |
| Whisper `medium` | `ms` | 12.1% | 50.0% | 14.9% | 15.6% | 2.41 s | +1398 MB |
| Mesolitica `malaysian-whisper-small-v3` | `ms` | 9.5% | 90.0% | 34.0% | 18.6% | 0.90 s | +117 MB |
| **Mesolitica `Malaysian-whisper-large-v3-turbo-v3`** | `ms` | **7.4%** | **4.0%** | 17.0% | **7.9%** | 2.77 s | +653 MB |

Per-utterance transcripts: `stt-benchmark-2026-09-30.json`.

## Findings

- **Standard Whisper can't serve both languages with one setting.** With `en` it translates
  Malay speech into English (59.5% WER on Malay); with `ms` it translates English into
  Malay ("During the interview I was nervous…" → "Pada temu bual, saya rasa ngeri…").
- **Mesolitica small-v3** is fast and good on Malay but also translates English into Malay.
- **Mesolitica large-v3-turbo-v3 keeps each language as spoken** — English stays English,
  Malay stays Malay, Manglish stays mixed — and is best or joint-best in every category,
  with about half the RAM of `medium`. **Adopted as SpeechMate's default.**

## Tuning turbo-v3 for speed (same test set)

Both experiments reproduce the table above exactly for the default setting (7.9% WER).

| Setting | WER all | Time per 5 s turn |
|---|---|---|
| Beam size 5 (default) | **7.9%** | 2.97 s |
| Beam size 1 (greedy) | 8.3% | 2.70 s |

Beam size barely matters for speed: turbo has a 32-layer encoder but only a 4-layer decoder,
and beam search only affects the decoder. The encoder, which always processes a 30 s
window even for a short turn, dominates. **Kept beam size 5.**

| CPU threads (beam 5) | WER all | Time per 5 s turn |
|---|---|---|
| 4 (faster-whisper default) | 7.9% | 2.89 s |
| **8** | 7.9% | **2.27 s** |
| 12 | 7.9% | 2.24 s |
| 16 | 7.9% | 3.28 s |

**Adopted: 8 threads (`WHISPER_CPU_THREADS=8`)** — 21% faster with identical accuracy;
beyond ~12 threads they start competing and it gets slower.

## Caveats

- The English and Manglish clips are synthetic: the TTS samples its output and sometimes
  adds or changes words (e.g. every model heard "presenten … okey, okey" where the text said
  "presentation tadi okay"), which inflates those WERs equally for all models. Only 4 clips
  each — treat those two columns as indicative. The Malay column (real speakers) is the most
  reliable.
- FLEURS is read speech; spontaneous conversation is harder. A held-out set of real
  recordings of the app's own users, split by language, is the next step (TODO Phase 5).

## Reproduce

```bash
docker compose --profile ollama --profile tts stop          # free RAM and CPU
backend/scripts/convert_whisper.sh mesolitica/malaysian-whisper-small-v3
backend/scripts/convert_whisper.sh mesolitica/Malaysian-whisper-large-v3-turbo-v3
# FLEURS + synthetic clips, then the benchmark (see backend/scripts/benchmark/)
docker run --rm -v speechmate_model_cache:/models -e HF_HOME=/models/huggingface \
  -v "$PWD/backend:/app" -w /app speechmate-backend bash -c \
  "pip install -q pyarrow 'transformers==4.56.2' && bash scripts/benchmark/prepare_data.sh; \
   pip install -q 'transformers==4.53.3' && python scripts/benchmark/make_synth.py && python scripts/benchmark/bench_stt.py"
```
