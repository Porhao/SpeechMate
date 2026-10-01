# Fine-tuning runs

One row per run, failed ones included (plan §5).

| Date | Run | Base | Data | Settings | Dev WER before → after | Silent words (dev) | Time / peak VRAM | Notes |
|---|---|---|---|---|---|---|---|---|
| 2026-10-02 | F4 smoke | `openai/whisper-small` | FLEURS ms_my validation: 204 train, 42 dev (incl. 4 + 2 near-silent) | LoRA r32, lr 3e-4, bf16, bs 2 × accum 8, 200 steps (~15 epochs) | 28.5% → 25.4% (step 100) → 26.3% (step 200) | 2 → 2 | 515 s / 0.84 GiB | Pipeline works. Overfits by step 200, as expected on 204 clips. Silent clips not fixed by 4 examples; the app's VAD normally catches them first. |
| 2026-10-02 | F4 smoke | `openai/whisper-large-v3-turbo` | Same as above | Same as above | 12.5% → 12.1% (step 100) → 13.2% (step 200) | 0 → 0 | 1371 s / 2.20 GiB | Fits easily in bf16 (no 8-bit needed); ~6.8 s/step. Already strong on read Malay, so little to gain; overfits by step 200. |
| 2026-10-02 | F4 smoke (stopped) | Mesolitica `Malaysian-whisper-large-v3-turbo-v3` | Same as above | Same as above, **no-timestamp labels and decoding** | 52.7% before training | 0 | - | **Failed eval:** without timestamp mode the model never emits end-of-text and loops ("5.5.5..."), although the words are right. The app is unaffected (faster-whisper uses timestamp mode). Fixed `train_lora.py` to train and evaluate in timestamp mode. The two rows above used no-timestamp mode. |
| 2026-10-02 | F4 smoke | Mesolitica `Malaysian-whisper-large-v3-turbo-v3` | Same as above | Same as above, **timestamp mode** (labels and decoding) | 12.6% → 12.0% (step 100) → 11.2% (step 200) | 1 → 0 → 0 | 1382 s / 2.20 GiB | Timestamp fix works: no looping. Still improving at step 200 (vanilla turbo overfit by then). Part of the remaining WER is digits vs spelled-out numbers ("3" vs "tiga"). |
| 2026-10-02 | F4 smoke | `openai/whisper-large-v3-turbo` | Same as above | Same as above, **timestamp mode** | 13.0% → 14.0% (step 100) → 14.3% (step 200) | 0 → 0 → 0 | 1370 s / 2.20 GiB | Fair comparison with the Mesolitica row: vanilla got slightly worse while Mesolitica improved (12.6% → 11.2%). The gap is about 1-3 words on 42 read-Malay clips, so it is a hint, not proof. |

## Licences

| Item | Licence | Use |
|---|---|---|
| Google FLEURS | CC BY 4.0 | Smoke test only (validation split; the STT benchmark uses the test split) |
| `openai/whisper-small` | MIT | Smoke-test base |
| Mesolitica `Malaysian-whisper-large-v3-turbo-v3` | **Not stated: ask (F0)** | Candidate base; also the shipped model |
