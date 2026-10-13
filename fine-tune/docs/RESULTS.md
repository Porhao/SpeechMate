# Fine-tuning runs

One row per run, failed ones included (plan §5).

| Date | Run | Base | Data | Settings | Dev WER before → after | Silent words (dev) | Time / peak VRAM | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-10-02 | F4 smoke | `openai/whisper-small` | FLEURS ms_my validation: 204 train, 42 dev (incl. 4 + 2 near-silent) | LoRA r32, lr 3e-4, bf16, bs 2 × accum 8, 200 steps (~15 epochs) | 28.5% → 25.4% (step 100) → 26.3% (step 200) | 2 → 2 | 515 s / 0.84 GiB | Pipeline works. Overfits by step 200, as expected on 204 clips. Silent clips not fixed by 4 examples; the app's VAD normally catches them first. |
| 2026-10-02 | F4 smoke | `openai/whisper-large-v3-turbo` | Same as above | Same as above | 12.5% → 12.1% (step 100) → 13.2% (step 200) | 0 → 0 | 1371 s / 2.20 GiB | Fits easily in bf16 (no 8-bit needed); ~6.8 s/step. Already strong on read Malay, so little to gain; overfits by step 200. |
| 2026-10-02 | F4 smoke (stopped) | Mesolitica `Malaysian-whisper-large-v3-turbo-v3` | Same as above | Same as above, **no-timestamp labels and decoding** | 52.7% before training | 0 | - | **Failed eval:** without timestamp mode the model never emits end-of-text and loops ("5.5.5..."), although the words are right. The app is unaffected (faster-whisper uses timestamp mode). Fixed `train_lora.py` to train and evaluate in timestamp mode. The two rows above used no-timestamp mode. |
| 2026-10-02 | F4 smoke | Mesolitica `Malaysian-whisper-large-v3-turbo-v3` | Same as above | Same as above, **timestamp mode** (labels and decoding) | 12.6% → 12.0% (step 100) → 11.2% (step 200) | 1 → 0 → 0 | 1382 s / 2.20 GiB | Timestamp fix works: no looping. Still improving at step 200 (vanilla turbo overfit by then). Part of the remaining WER is digits vs spelled-out numbers ("3" vs "tiga"). |
| 2026-10-02 | F4 smoke | `openai/whisper-large-v3-turbo` | Same as above | Same as above, **timestamp mode** | 13.0% → 14.0% (step 100) → 14.3% (step 200) | 0 → 0 → 0 | 1370 s / 2.20 GiB | Fair comparison with the Mesolitica row: vanilla got slightly worse while Mesolitica improved (12.6% → 11.2%). The gap is about 1-3 words on 42 read-Malay clips, so it is a hint, not proof. |
| 2026-10-06 | F5 public data | Mesolitica `Malaysian-whisper-large-v3-turbo-v3` | `prepare_public.py`: 3,451 train clips, 10.3 h (Synth-Manglish 2,118 + FLEURS ms/en 900 + 301 noisy copies + 132 silent); dev 208 (3 held-out voices + FLEURS validation + 8 silent) | LoRA r32, **lr 1e-4**, bf16, bs 2 × accum 8, 3 epochs (648 steps), timestamp mode, best epoch kept | 19.5% → 4.6% (ep 1) → **4.1% (ep 2, kept)** → 4.3% (ep 3) | 8 → 0 → 0 → 0 | 4942 s (82 min) / 2.20 GiB | Big dev gain, but in-domain: dev voices are the same TTS system and sentence style, and share the style-guide particle spellings. Not yet evidence for real speakers: needs `bench_stt.py --real` on own recordings. Adapter in `out/adapter/`. |

## F6: shipped vs fine-tune on eval/paper (2026-10-06)

400 clips never trained on, run through the app's `asr.whisper_segments` (CT2 int8, CPU, auto language, VAD). `scripts/eval_finetune.py`, per-clip output in `eval/paper/finetune_results.csv`.

| Group | Shipped (Mesolitica turbo-v3, app prompt) | Fine-tune, no prompt | Fine-tune, app prompt | Plain Whisper large-v3 (`eval_routing.py`) |
|---|---|---|---|---|
| English-only: 200 FLEURS en_us test (real speakers) | 9.4% | **6.7%** | 6.8% | 5.3% |
| Mixed: 200 Synth-Manglish, held-out voices (synthetic) | 14.5% | **6.7%** | 7.0% | 15.4% |

- English gains are real word fixes ("about us" → "about birds", "Goods" → "Goats"), but FLEURS en_us *train* was in the training mix, so this is near-domain.
- Mixed gains are in-domain (same TTS system and sentence style as training). The mixed references keep the corpus's raw spellings ("wei", "la"), so the fine-tune's style-guide spellings ("weh", "lah") count against it.
- The prompt barely matters for the fine-tune (+0.1-0.3 points).
- Silence safety (plan §11): 0 of 10 silent or noise-only clips produced any text, for both models (8 dev silent clips + 8 s of silence + 8 s of white noise, app settings with VAD).
- Not yet checked: real Malaysian speakers (`bench_stt.py --real`) and noisy real speech. Go/no-go (plan §11) still needs those.

## Licences

| Item | Licence | Use |
|---|---|---|
| Google FLEURS ([google/fleurs](https://huggingface.co/datasets/google/fleurs)) | CC BY 4.0 | `ms_my` and `en_us` train splits as guard data, validation splits as dev. The test split is reserved for the STT benchmark. |
| Synth-Manglish ([emhaihsan/Synth-Manglish](https://huggingface.co/datasets/emhaihsan/Synth-Manglish)) | CC BY 4.0 | Manglish training data (synthetic TTS voices); 3 voices held out as dev. Particle spellings normalised to `STYLE_GUIDE.md`. |
| Mesolitica Hugging Face datasets (Malaysian-STT-Whisper, semisupervised-*, malaya-speech-malay-stt) | **Not stated** | Not used. Same open question as their model. |
| Semisupervised Manglish (Malaya-Speech docs, CC BY 4.0) | CC BY 4.0 | Not used: the documented download link is dead (404, 2026-10-06). |
| `openai/whisper-small` | MIT | Smoke-test base |
| Mesolitica `Malaysian-whisper-large-v3-turbo-v3` | **Not stated: ask (F0)** | Candidate base; also the shipped model |
