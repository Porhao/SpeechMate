# Deployed cloud speech recognition: Groq whisper-large-v3 (2026-10-15)

This benchmarks the speech recognition the app actually uses (`OPENAI_BASE_URL=https://api.groq.com/openai/v1`, `TRANSCRIPTION_MODEL=whisper-large-v3`). It uses the same request as `backend/app/services/live/asr.py`:
- `verbose_json` with word timestamps;
- the shared verbatim Manglish prompt;
- automatic language detection.

The test set is the same 400 held-out clips as `stt-routing-and-finetune-2026-10-06.md`, plus 100 real Malay clips and 10 silent or noise-only clips.

- **Script:** `fine-tune/scripts/eval_groq.py`
- **Per-clip output:** `fine-tune/eval/paper/groq_results.csv`
- **Statistics:** `python3 fine-tune/scripts/paper_stats.py` (5,000 bootstrap draws, exact sign test)

The run stayed within Groq's free tier:
- 511 requests, against a limit of 2,000 per day;
- 94.2 min billed audio, against limits of 7,200 s per hour and 28,800 s per day;
- the script paces itself under 20 requests per minute and stops itself at 6,500 billed seconds or 600 requests.

At the listed price ($0.111 per audio hour, 10 s minimum billed per request) the run would have cost $0.17.

## Accuracy (WER, 95% CI)

| Group | Groq whisper-large-v3 | Same weights run locally | Shipped Malaysian model (local) | Groq vs local v3 | Groq vs shipped |
|---|---|---|---|---|---|
| English: 200 FLEURS en_us (real speakers) | **4.9%** [4.1, 5.8] | 5.3% [4.4, 6.2] | 9.4% [7.2, 12.0] | −0.4 pts [−1.1, +0.2], p = 0.75 | −4.6 pts [−7.2, −2.4], p = 8×10⁻⁹ |
| Mixed: 200 Synth-Manglish, held-out voices (synthetic) | **16.5%** [14.7, 18.4] | 15.4% [14.0, 17.0] | 14.5% [13.1, 16.0] | +1.0 pts [−0.1, +2.5], p = 0.72 | +2.0 pts [+0.7, +3.5], p = 0.003 |
| Malay: 100 FLEURS ms_my (real speakers) | **7.3%** | — | — | — | — |

- **Same as local.** The cloud service matches the same weights run locally; neither difference is significant. The earlier local results for Whisper large-v3 therefore carry over to the deployed system.
- **English.** It is clearly better on English than the Malaysian model that used to ship.
- **Manglish.** It is slightly but significantly worse than the Malaysian model on Manglish (+2.0 points, 86 clips worse vs 50 better).
- **Language detection:**
  - English: English 200/200.
  - Mixed: Malay 194, English 6.
  - Malay: Malay 92, Indonesian 8.
- **No translation.** No English or mixed clip came back translated.

## Silence (no voice-activity filter in front)

| Clip | Output |
|---|---|
| 8 s digital silence | "you" |
| 8 s white noise | "I'm gonna go to the bathroom. Okay. Okay. Okay. …" |
| 6 of 8 silent dev clips | "Subtitles by the Amara.org community" (4), "Okay." (2) |

**8 of 10 silent or noise-only clips produced text.** The earlier local runs scored 0/10 because faster-whisper's VAD dropped the silence first. The app's current guards are:
- **live turns:** the browser sends a turn only after at least 0.35 s of sound above an adaptive noise floor (`frontend/lib/voiceTurns.ts`);
- **analysis:** rejects recordings with under 1 s of non-silence.

**Fix applied (same day).** `asr.keep_speech` drops a segment when its `no_speech_prob` is ≥ 0.4, or ≥ 0.2 and its text is a stock phrase or two words or fewer. Subtitle credits ("Amara.org", "thanks for watching") are always dropped. Calibrated on Groq's own scores:

| Clips | `no_speech_prob` | Result |
|---|---|---|
| 10 silent / noise | 0.24 – 0.72 | 10/10 removed |
| 10 speech (English, Malay, Manglish; one contains a genuine "Okay.") | 0.001 – 0.097 | 10/10 kept |

It applies to live turns (`/api/stt`), session analysis and rehearsal transcripts. The live endpoint now returns an empty transcript for the silent and noise clips above, and the speech clip unchanged.

## Latency and word timings

| Request | n | Median | p90 | p95 | Max |
|---|---|---|---|---|---|
| One clip (4–26 s; like one live turn) | 500 | 0.56 s | 1.30 s | 6.66 s | 8.51 s |
| One 189 s recording (like a session analysis upload, 6.0 MB WAV) | 1 | 3.2 s | | | |

- **Word timings:** every clip with text returned them (needed for pause and stutter timing). The 189 s file returned all 327.
- **Local comparison:** the local Malaysian model took 2.3–2.7 s per 5 s turn on CPU (`stt-benchmark-2026-09-30.md`).
- **Tail latency:** about 5% of requests took 5–9 s, probably queueing at the provider. These waits are excluded from the 429 retries, which are counted separately.

## Cost per session

Groq bills $0.111 per audio hour with a 10 s minimum per request. A session sends:
- each spoken phrase as a live turn (each billed at least 10 s);
- the user's own speech once more for the analysis. The recorder is paused during AI turns, so this is only the user's speech.

$$ \text{cost} = \frac{\$0.111}{3600}\Big(\sum_{\text{phrases}} \max(10\,\text{s}, d_i) + T_{\text{user}}\Big) $$

| Session (assumed: phrases about 5 s each) | User speech | Requests | Billed audio | Cost | Free-tier sessions per day |
|---|---|---|---|---|---|
| 5-min conversation | 2.5 min | 31 | 450 s | **$0.014** | about 64 (limited by both the daily audio and request limits) |
| 10-min mock interview | 6 min | 61 | 960 s | **$0.030** | about 30 |

- **10 s minimum.** Because each short phrase is billed as 10 s, the live turns cost more than the analysis. Sending whole turns instead of phrases would roughly halve the cost.
- **Unverified assumption.** The 5 s phrase length is assumed; measure it from real sessions.
- **Upload limit.** Groq accepts at most 25 MB per direct upload (free tier). The analysis sent 16 kHz 16-bit WAV (32 kB/s), which capped recordings at about 13 minutes of user speech. **Fixed:** uploads are now lossless FLAC, measured at 35% of the WAV size, so the cap is about 37 minutes.
- **Usage is now logged per session** (`analysis.details.usage`): speech-to-text requests, audio and billed seconds and cost, plus Gemini calls and tokens. Real sessions will replace the assumed 5 s phrase length above.

## Limitations

- The mixed group is synthetic, and the English group is read speech. Real Malaysian conversational speech is still untested.
- Groq may change its serving stack without notice. These results are for 2026-10-15.
- LLM (Gemini) cost and latency per session are not measured here.
