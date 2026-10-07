# Speech recognition: code-switch routing and the first fine-tune (2026-10-06)

**Findings.**
1. **Routing was broken in the app.** The pinned torch 2.4.1 cannot load the code-switch model's `pytorch_model.bin` under transformers 4.53 (CVE-2025-32434 guard). Every routed clip silently fell back to the Whisper transcript. Fixed: `backend/requirements-ml.txt` now pins torch/torchaudio 2.6.0 (the TTS codec checkpoint still loads). The other app models ship safetensors and were unaffected.
2. **Routing detects code-switching correctly, but the second engine is worse than Whisper.** On mixed speech, routing more than doubles WER.
3. **A LoRA fine-tune of the shipped model beats it** on both groups below, and stays silent on silence and noise. It is not deployed: it still needs real Malaysian speakers (`bench_stt.py --real`).

## Test set (400 clips, none used in training)

| Group | Clips | Source | Speech |
|---|---|---|---|
| English-only | 200 | FLEURS `en_us` test split (CC BY 4.0) | Real speakers, human transcripts (US English) |
| Mixed English/Malay | 200 | Synth-Manglish (CC BY 4.0), 3 voices held out of training | Synthetic TTS voices |

Built by `fine-tune/scripts/make_paper_eval.py`; per-clip results in `fine-tune/eval/paper/`.

## 1. Routing on vs off

Plain Whisper **large-v3** (routing only runs with a standard Whisper; it is skipped for the shipped Malaysian model), run through the app's own `asr._transcribe_local` (`fine-tune/scripts/eval_routing.py`).

| Group | WER routing off | WER routing on | Routing triggered | Detected language (mean confidence) |
|---|---|---|---|---|
| English-only | 5.3% | 5.3% | 0 / 200 | en 200 (0.99) |
| Mixed | **15.4%** | **36.7%** | 200 / 200 | ms 196, en 4 (0.96) |

Example (mixed): Whisper "…challenge arwah Sudirman kot, energi dia…" vs code-switch model "…challen arwasudirman kod energy dia…".

## 2. Shipped model vs fine-tune

CT2 int8 on CPU, auto language, VAD, as the app runs (`fine-tune/scripts/eval_finetune.py`).

| Group | Shipped (Mesolitica turbo-v3, app prompt) | Fine-tune, no prompt | Fine-tune, app prompt |
|---|---|---|---|
| English-only | 9.4% | **6.7%** | 6.8% |
| Mixed | 14.5% | **6.7%** | 7.0% |
| Silent/noise clips with any text | 0 / 10 | 0 / 10 | – |

Fine-tune: LoRA on Mesolitica turbo-v3, 10.3 h public data (Synth-Manglish + FLEURS ms/en guard data + noise + silence), details in `fine-tune/RESULTS.md`.

## Limitations

- The mixed group is synthetic, and from the same TTS system as the fine-tune's training data, so the fine-tune's mixed gain is in-domain.
- FLEURS `en_us` train clips were in the training mix, so the English gain is near-domain.
- No real Malaysian speakers yet. Real-user WER and filler F1 need the recordings in `fine-tune/RECORDING_PROMPTS.md`.
