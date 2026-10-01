# Speech recognition: forced Malay token vs. auto-detect (2026-10-01)

**Finding.** In a full interview test, SpeechMate's analysis **translated US-accented English answers into Malay**:
- Spoken: "I think I am a final year statistics student…"
- Transcribed: "saya rasa saya pelajar statistik tahun terakhir…"

**Cause.** The app forced Whisper's `ms` language token for Mesolitica's Malaysian Whisper. Forced Malay plus no English prompt makes the model translate.

**Fix.** The app now auto-detects the language for this model (`STT_LANGUAGE` empty = auto). Set `STT_LANGUAGE=ms` to restore the old behaviour.

## Results

Settings for both runs:
- Model: `malaysian-whisper-large-v3-turbo-v3`, CTranslate2 int8, CPU
- Decoding: 8 threads, beam 5, VAD filter, the app's initial prompt

| Config | Malay (FLEURS, 25 real speakers) | Malaysian English | Manglish | US/UK English (new) | All | Time per 5 s turn |
|---|---|---|---|---|---|---|
| `language="ms"` (old default) | 7.4% | 4.0% | 17.0% | 0.0% \* | 6.8% | 2.45 s |
| **auto-detect (new default)** | **6.4%** | 4.0% | 17.0% | 0.0% | **6.1%** | 2.53 s |

\* With the benchmark's English initial prompt, forced `ms` happened to keep these short clips in English. The analysis pipeline has no such prompt and translated the 23-second answer above. A direct test of that recording:

| Recording | `language=None` | `language="ms"` |
|---|---|---|
| Kokoro US English interview answer (23 s) | "Um, I think I am a final year statistics student at University Malaya…" | "Um, saya rasa saya pelajar statistik tahun terakhir di Universiti Malaya…" |
| FLEURS Malay clip 0 | identical Malay | identical Malay |

**Conclusion.**
- Auto-detect is never worse.
- It is 1 point better on real Malay speakers.
- It removes the translation failure.
- It costs about 0.1 s per turn.

## Test set

- 25 FLEURS `ms_my` test clips (real speakers).
- 4 Malaysian-English and 4 Manglish clips (local Malaysian TTS, `make_synth.py`).
- 6 US/UK English clips (Kokoro, `make_synth_kokoro.py`).

## Reproduce

```bash
docker compose exec backend python scripts/benchmark/make_synth_kokoro.py   # needs the kokoro service
docker compose exec backend python scripts/benchmark/bench_stt.py --auto
```

Limitations:
- The English and mixed clips are synthetic.
- The real-user WER still needs recordings from the app (see `docs/AI_MATRIX.md` §3).
