# Speech recognition: one Manglish verbatim prompt for every path (2026-10-02)

**Change** (from `docs/manglish-transcription-spec.md` §6–7). All three local Whisper paths now go through `asr.whisper_segments()`. Before this change they used different settings:

| Path | Before | Now |
|---|---|---|
| `/api/stt` (live AI partner) | Manglish prompt, VAD, `condition_on_previous_text=False`, hallucination filter | Same, with the shared prompt and 500 ms VAD silence |
| Live-session analysis (filler/pace metrics) | **No prompt**, conditioned on previous text, no hallucination filter | Shared settings |
| Practice recordings | English-only filler prompt, conditioned on previous text | Shared settings |

The shared prompt is `"Umm, okay lah, so, uh, macam this week saya busy sikit, you know... but boleh la."`. It contains fillers, so Whisper keeps the user's fillers, and Manglish, so it keeps code-switched words as spoken.

**Fixed:** a fully silent clip crashed faster-whisper 1.0.3 when the language was auto-detected (`max() iterable argument is empty`). This bug existed before the change. A silent clip now returns an empty transcript.

## Results

Settings for both runs: `malaysian-whisper-large-v3-turbo-v3`, int8, 8 threads, beam 5, auto-detect.

| Config | Malay (FLEURS) | Malaysian English | Manglish | US/UK English | All | Per 5 s turn |
|---|---|---|---|---|---|---|
| Old `/stt` prompt, 2000 ms VAD silence | 6.4% | 4.0% | 17.0% | 0.0% | 6.1% | 2.50 s |
| **Shared verbatim prompt, 500 ms** | 6.8% | 4.0% | 19.1% | 0.0% | 6.5% | 2.69 s |

Silence check (8 s of silence and 8 s of white noise, through both `/stt` and the analysis path): empty transcript in every case.

## Reading the numbers

The 2-point Manglish difference is about 1 word over 4 synthetic clips. Most of the changes are spelling:
- "ok" became "okey".
- "kenyang lah" became "kenyanglah". The particle counter misses this form.
- One real gain: "Ashley nak explain" became "Actually, nak explain".

The prompt was chosen for filler retention, and this test set has no fillers. Real recordings with fillers will decide it (spec §8, M1).

Reproduce: `docker compose exec backend python scripts/benchmark/bench_stt.py --prompt`
