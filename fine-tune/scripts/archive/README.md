# Archived evaluation scripts

These produced the October 2026 numbers in `docs/RESULTS.md` (F6) and
`docs/benchmarks/stt-routing-and-finetune-2026-10-06.md`. They run SpeechMate's *local*
speech-to-text code (`asr.whisper_segments`, `asr._transcribe_local`), which was removed on
2026-10-14 (`docs/project/local-stt-removal.md`), so they don't run on the current backend.

To re-run one, check out the backend as of commit `6f89bed` (the last with local speech-to-text)
and follow the command in the script's docstring.

| Script | What it measured |
|---|---|
| `eval_finetune.py` | shipped model vs fine-tune vs Whisper large-v3 on `eval/paper`, through the app's code |
| `eval_routing.py` | code-switch routing on vs off (paper) |

The deployed app (Groq) is measured with `../run_app_on_clips.py` + `../study_stats.py asr`.
