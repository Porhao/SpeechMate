# SpeechMate Manglish ASR Fine-tune

A LoRA fine-tune of Mesolitica's Malaysian Whisper large-v3-turbo-v3. It is trained to transcribe Malaysian speakers, including English/Malay code-switching (Manglish), verbatim, for SpeechMate's coaching metrics.

**Status (8 Oct 2026): trained, evaluated on public data, NOT deployed.** It beats the model SpeechMate ships on every public test group. It has not yet been tested on real Malaysian speakers, which is the go/no-go condition (§10). The app still runs the original Mesolitica model.

| Test group (never trained on) | Shipped model | **This fine-tune** |
|---|---|---|
| English, 200 real speakers (FLEURS en_us) | 9.4% WER | **6.7%** |
| Manglish, 200 synthetic-voice clips (Synth-Manglish) | 14.5% WER | **6.7%** |
| Silent or noise-only clips that produced text | 0 / 10 | **0 / 10** |

Contents:
1. [Model details](#1-model-details)
2. [Intended use](#2-intended-use)
3. [Training data](#3-training-data)
4. [Training procedure](#4-training-procedure)
5. [Evaluation](#5-evaluation)
6. [Limitations and risks](#6-limitations-and-risks)
7. [Licences and attribution](#7-licences-and-attribution)
8. [Reproduce it](#8-reproduce-it)
9. [Deploy it in SpeechMate](#9-deploy-it-in-speechmate)
10. [Go / no-go checklist](#10-go--no-go-checklist)
11. [Adding your own recordings](#11-adding-your-own-recordings)
12. [Problems found and how they were fixed](#12-problems-found-and-how-they-were-fixed)
13. [File map](#13-file-map)

Related: the plan and rationale are in [`docs/manglish-finetune-plan.md`](docs/manglish-finetune-plan.md). Every run, including failed ones, is in [`RESULTS.md`](RESULTS.md). The benchmark write-up is [`../docs/benchmarks/stt-routing-and-finetune-2026-10-06.md`](../docs/benchmarks/stt-routing-and-finetune-2026-10-06.md).

---

## 1. Model details

| Item | Value |
|---|---|
| Base model | [`mesolitica/Malaysian-whisper-large-v3-turbo-v3`](https://huggingface.co/mesolitica/Malaysian-whisper-large-v3-turbo-v3): Whisper large-v3-turbo (32-layer encoder, 4-layer decoder, about 809M parameters), already fine-tuned by Mesolitica on Malaysian speech. It is the model SpeechMate ships. |
| Method | LoRA adapters on the attention projections (`q_proj`, `k_proj`, `v_proj`, `out_proj`) of encoder and decoder. The base weights are frozen. |
| LoRA settings | rank `r` = 32, `lora_alpha` = 64, dropout 0.05 |
| Trainable parameters | 13.1M of 822M (1.6%) |
| Training precision | bf16 (no 8-bit or 4-bit quantisation needed: 2.2 GiB peak VRAM) |
| Output format | Whisper **timestamp mode**: `<|startoftranscript|><|ms or en|><|transcribe|><|0.00|> text <|end time|><|endoftext|>`. This matches how faster-whisper decodes in the app. |
| Language | Per-clip language token in training (`en` or `ms`, the clip's main language). **Auto-detected** at inference, as in the app. |
| Prompt | Trained without an initial prompt. It works with or without the app's verbatim Manglish prompt (6.7% vs 6.8–7.0% WER). |
| Artifacts | `out/adapter/` (LoRA, 28 MB, best epoch), `out/merged/` (full Hugging Face model, fp16, 1.6 GB), `out/ct2/` (CTranslate2 int8 for faster-whisper, 782 MB: **what the app would load**) |
| Runtime in the app | faster-whisper 1.0.3, CPU, int8, 8 threads, beam 5, VAD. About 4.4 s per clip (clips average about 9 s), the same speed as the shipped model. |

## 2. Intended use

**For:** transcribing a SpeechMate user's practice answers (conversation, mock interview, presentation Q&A) verbatim, so pace, filler, repetition and language-mix metrics are computed from what was actually said.

- Malaysian English, Bahasa Melayu and code-switched Manglish.
- Short turns (up to 30 s), 16 kHz mono, laptop or phone microphones.

**Not for:**
- Clean "corrected" transcripts. It deliberately keeps fillers and Manglish particles.
- Languages other than English and Malay.
- Long-form audio without VAD segmentation.
- Anything that identifies speakers.

## 3. Training data

All training data is public and CC BY 4.0. No real user recordings were used yet.

| Source | Clips | Hours | Share | What it adds |
|---|---|---|---|---|
| [Synth-Manglish](https://huggingface.co/datasets/emhaihsan/Synth-Manglish) (18 of 21 TTS voices) | 2,118 | 6.29 | 61% | Manglish vocabulary and code-switching ("traffic gila babas from city sini, nasib baik aku tak missed flight") |
| [FLEURS](https://huggingface.co/datasets/google/fleurs) `ms_my` + `en_us` train splits (450 + 450) | 900 | 2.89 | 28% | **Guard data:** real Malay and real English speakers, so plain Malay and English don't degrade |
| Noisy copies of 10% of the above (white or brown noise, 5–20 dB SNR) | 301 | 0.90 | 9% | Robustness to background noise |
| Generated near-silence (empty transcript) | 132 | 0.19 | 2% | Teaches "output nothing" on silence |
| **Total (train)** | **3,451** | **10.28** | | 2,348 tagged `en`, 1,103 tagged `ms` |

**Dev set** (picks the best epoch): 208 clips, 0.56 h. It holds 120 clips from 3 Synth-Manglish voices held out of training (`nurin`, `rizal`, `johari`), 80 FLEURS validation clips (40 Malay, 40 English) and 8 silent clips. It's split **by voice**, so no dev voice is heard in training.

**Preprocessing** (`scripts/prepare_public.py`):
- **Audio:** decoded with ffmpeg to 16 kHz mono. Clips over 30 s (Whisper's window) or under 1 s of speech are dropped.
- **Spelling normalised to [`STYLE_GUIDE.md`](STYLE_GUIDE.md):** `la`→`lah`, `wei`→`weh`, `loh`→`lor`, `aiyoh`→`aiyo`, `ok`/`okey`→`okay`. Synth-Manglish had 430 "la" vs 237 "lah" and 830 "wei" vs 211 "weh". The model learns whatever spelling it's shown, so one spelling per word matters.
- **Language tag:** the share of Malay words, by the app's own lexicon (`backend/app/services/live/language.py`). Above 35% is `ms`, otherwise `en`. The cut-off is low because the lexicon misses many Malay words.
- **FLEURS:** one clip per sentence, since FLEURS repeats each sentence across speakers.

## 4. Training procedure

Script: `scripts/train_lora.py` (Hugging Face `Seq2SeqTrainer` + PEFT).

| Setting | Value |
|---|---|
| Learning rate | 1e-4 (lower than the 3e-4 default because the base is already tuned), 50 warm-up steps |
| Batch | 2 per step × 8 accumulation = 16 clips |
| Epochs | 3 (648 steps); **best epoch by dev WER kept** (`load_best_model_at_end`) |
| Labels | Timestamp tokens: `<|0.00|>` + text + the clip's end time. Silent clips: just the prefix + `<|endoftext|>`. |
| Memory | Gradient checkpointing (non-reentrant), bf16 |
| Hardware | NVIDIA RTX 4060 Laptop (8 GB), WSL2, 7.6 GB RAM |
| Time | 82 min, 2.20 GiB peak VRAM |

| Epoch | Dev WER | Words produced on 8 silent dev clips |
|---|---|---|
| 0 (base model) | 19.5% | 8 |
| 1 | 4.6% | 0 |
| **2 (kept)** | **4.1%** | **0** |
| 3 | 4.3% | 0 |

Dev WER is in-domain (same TTS system and spelling conventions as training), so it is only used to pick the epoch. §5 gives the real comparison.

**Smoke tests before this run** (FLEURS Malay, 204 clips, 200 steps) confirmed the pipeline on whisper-small, vanilla large-v3-turbo and Mesolitica. Mesolitica improved while vanilla turbo got worse (`RESULTS.md`), which is why Mesolitica is the base.

## 5. Evaluation

**Test set:** `eval/paper/`, built by `scripts/make_paper_eval.py`. None of these clips is in training. Every model ran through SpeechMate's own transcription function (`backend/app/services/live/asr.py: whisper_segments`), with the app's settings (CTranslate2 int8 on CPU, auto language, VAD, beam 5). Script: `scripts/eval_finetune.py`. WER: lower-cased, punctuation removed, words `[a-z0-9']+`.

| Group | Clips | Shipped (Mesolitica, app prompt) | Fine-tune, no prompt | Fine-tune, app prompt | Whisper large-v3 (plain) |
|---|---|---|---|---|---|
| English-only (FLEURS en_us test, real speakers) | 200 | 9.4% | **6.7%** | 6.8% | 5.3% |
| Mixed (Synth-Manglish, held-out voices) | 200 | 14.5% | **6.7%** | 7.0% | 15.4% |

**Silence safety:** 0 of 10 clips produced any text with either model. The clips were 8 silent dev clips, 8 s of digital silence and 8 s of white noise.

**Examples of what changed (English):**
- "about **us** that still look like a dinosaur" → "about **birds**…"
- "**Goods** seem to have been first domesticated" → "**Goats**…"
- "**Free** juices are pricey" → "**Fruit** juices…"

**How to read these numbers:**
- **English gain:** real word fixes on real speakers. But FLEURS en_us *train* clips were in the training mix (same recording style), so it's near-domain.
- **Mixed gain:** in-domain. The test voices are held out, but they come from the same TTS system and sentence style. The references keep the corpus's raw spellings ("wei", "la") while the model writes the style guide's ("weh", "lah"), so the fine-tune is slightly *penalised* here.
- **Plain Whisper large-v3** is the model behind VoiceStudio's transcription. It's best on US English but worse than both Mesolitica models on Manglish.
- **Not measured yet:** real Malaysian speakers, natural fillers and hesitations, noisy real-world speech. Malay-only (100 FLEURS ms_my clips) is set up in `eval/paper/` but the run was stopped before finishing (§12).

## 6. Limitations and risks

| Limitation | Effect | What would fix it |
|---|---|---|
| **No real Malaysian speakers in training or test** | The Manglish gain may partly be "learned the TTS voices" | Your own recordings (§11), then `bench_stt.py --real` |
| Synthetic Manglish has almost no fillers ("um" appears 5 times in 2,457 texts) | Filler behaviour is unproven. The app's filler metrics depend on it. | Real recordings with fillers, transcribed with `STYLE_GUIDE.md` |
| It learns the style guide's spellings | Output says "lah", "weh", "okay", even if a reference spells them differently | Intended. Keep references in the same style. |
| Numbers | Written as digits ("3 lagi bom"), like Whisper and Mesolitica. FLEURS references sometimes spell them out. | Style guide §6 chooses digits |
| Language tag by lexicon | Some Malay-framed sentences may be tagged `en` | A real language-ID model, if it matters |
| Base model licence unknown | Mesolitica's model card states no licence. This affects both the shipped model and this fine-tune. | Ask Mesolitica before any distribution |
| Training hardware is tight | 7.6 GB RAM: training or evaluation at the same time as the app stack can get processes killed | Run when the app is idle; raise WSL memory |

## 7. Licences and attribution

| Item | Licence | Use here |
|---|---|---|
| Synth-Manglish (emhaihsan) | CC BY 4.0 | Training (18 voices), dev (3 voices), mixed test group |
| Google FLEURS | CC BY 4.0 | Train splits as guard data, validation as dev, test splits as English/Malay test groups |
| Mesolitica Malaysian-whisper-large-v3-turbo-v3 | **Not stated** | Base model. **Open question:** ask before distributing |
| OpenAI Whisper large-v3 / turbo | MIT | Comparison and smoke tests |

CC BY 4.0 requires attribution. Credit Synth-Manglish and FLEURS in the report and wherever the model is shared.

## 8. Reproduce it

Three Python environments, kept separate so the app's pinned versions stay exact:

| venv | For | Install |
|---|---|---|
| `.venv` | Data prep, training, merge | `python3 -m venv .venv && .venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cu128 && .venv/bin/pip install -r requirements.txt pandas` |
| `.venv-app` | Evaluation with the app's own code (faster-whisper 1.0.3, transformers 4.53.3, torch 2.6.0 CPU) | `.venv-app/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.6.0" "transformers==4.53.3" "faster-whisper==1.0.3" "numpy<2" soundfile pydantic-settings "pydantic[email]" "openai>=1.40"` |
| `.venv-convert` | CTranslate2 conversion (the converter needs transformers ≥ 4.56) | `.venv-convert/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.6.0" "transformers==4.56.2" ctranslate2 "numpy<2" protobuf sentencepiece` |

Steps (from `fine-tune/`; **stop using the app while these run**, see §6):

```bash
# 1. Data: 10.3 h public training set → data/   (~20 min, streams ~2 GB from Hugging Face)
.venv/bin/python scripts/prepare_public.py
#    optional: add your own recordings (§11)
.venv/bin/python scripts/prepare_own.py --test s01 s02

# 2. Train (~80 min on an RTX 4060)
LR=1e-4 .venv/bin/python scripts/train_lora.py mesolitica/Malaysian-whisper-large-v3-turbo-v3

# 3. Merge + convert → out/merged/, out/ct2/
.venv/bin/python scripts/export.py

# 4. Evaluate against the shipped model (~85 min on CPU)
.venv/bin/python scripts/make_paper_eval.py
.venv-convert/bin/ct2-transformers-converter --model mesolitica/Malaysian-whisper-large-v3-turbo-v3 \
    --output_dir out/ct2_base --quantization int8 --copy_files tokenizer.json preprocessor_config.json --low_cpu_mem_usage
cd /tmp && WHISPER_CPU_THREADS=8 <repo>/fine-tune/.venv-app/bin/python <repo>/fine-tune/scripts/eval_finetune.py
```

Run the evaluation from a folder **without** a `.env` (for example `/tmp`). The app's config reads `.env` from the working directory, and `backend/.env` would override the model under test.

## 9. Deploy it in SpeechMate

Only after the go/no-go checks (§10) pass.

1. **Copy the model into the app's model volume, under a name containing `malaysian-whisper`.** The name matters: `asr.is_malaysian_model()` checks it, and only then does the app skip the code-switch routing. Routing sends mixed speech to a wav2vec2 model that **more than doubles WER** (15.4% → 36.7%, benchmark report). Run from the repo root:
   ```bash
   docker run --rm -v speechmate_model_cache:/models -v "$PWD/fine-tune/out/ct2":/src alpine \
     sh -c 'mkdir -p /models/ct2/malaysian-whisper-speechmate-ft-v1 && cp /src/* /models/ct2/malaysian-whisper-speechmate-ft-v1/'
   ```
2. **Point the app at it** in `backend/.env`:
   ```
   WHISPER_MODEL_SIZE=/models/ct2/malaysian-whisper-speechmate-ft-v1
   STT_LANGUAGE=
   ```
   Leave `STT_LANGUAGE` empty (auto-detect, as trained). The app's verbatim prompt can stay: it costs 0.1–0.3 points.
3. **Restart the backend when nothing is analysing** (`docs/project/agents.md`):
   `docker compose up -d --no-deps backend`
4. **Roll back** by setting `WHISPER_MODEL_SIZE=/models/ct2/malaysian-whisper-large-v3-turbo-v3` and restarting.

## 10. Go / no-go checklist

From the plan (§11). Ship only if all hold on a test set of **real speakers** the model never trained on:

- [x] Beats the shipped model on public data (English 9.4% → 6.7%, mixed 14.5% → 6.7%)
- [x] Silence safety: no text on silent or noise-only clips
- [x] Same speed as the shipped model (CPU int8)
- [ ] **Beats the shipped model on real Malaysian speakers** (`bench_stt.py --real`, own recordings)
- [ ] Not worse on Malay-only speech (100 FLEURS ms_my clips are set up; run `eval_finetune.py` to finish)
- [ ] Keeps fillers at least as well as the shipped model (filler retention in `bench_stt.py --real`)
- [ ] Gains hold across speakers, not just one
- [ ] Base-model licence answered by Mesolitica

## 11. Adding your own recordings

The missing ingredient is real Malaysian speech. The kit is ready:

| File | What it's for |
|---|---|
| [`OWN_DATA_GUIDE.md`](OWN_DATA_GUIDE.md) | Step by step, from consent to training (10 speakers × 25 min target, 2 held out as test speakers) |
| [`SPEAKER_SCRIPT.md`](SPEAKER_SCRIPT.md) | The printable 36-question session script |
| [`RECORDING_PROMPTS.md`](RECORDING_PROMPTS.md) | Prompt blocks and why each exists |
| [`STYLE_GUIDE.md`](STYLE_GUIDE.md) | How to transcribe (fillers, particles, Malay spellings, numbers) and how to mark disfluencies for F1 |
| `templates/clips.csv` | The per-speaker clip sheet |
| `scripts/prepare_own.py` | Turns recordings into training rows plus a locked test set (`eval/real/` + `refs.json`). `--selftest` checks it. |

Then retrain (§8 step 2), re-export, and score both models on `eval/real/` with `backend/scripts/benchmark/bench_stt.py --real`.

## 12. Problems found and how they were fixed

| Problem | Symptom | Fix |
|---|---|---|
| Mesolitica only works in timestamp mode | Without timestamps it never stops ("…2 jam. 3.5.5.5.5…"), giving a fake 52.7% WER | Train and evaluate in timestamp mode (`train_lora.py`). The app was never affected: faster-whisper uses timestamp mode. |
| Train/inference mismatch | The first script trained in no-timestamp mode, while the app transcribes in timestamp mode | Same fix: labels carry `<|0.00|> … <|end|>` |
| transformers 5 vs 4 files | The converter failed on `dtype` in `config.json` and on the tokenizer format | `export.py` renames `dtype`→`torch_dtype` and copies the base repo's original tokenizer files; conversion runs in `.venv-convert` (transformers 4.56.2) |
| App's code-switch routing was broken | torch 2.4.1 + transformers 4.53 refuse to load the routing model's `.bin` weights (CVE-2025-32434), so routing silently fell back to Whisper | `backend/requirements-ml.txt` now pins torch 2.6.0 (backend rebuilt; TTS checkpoint still loads) |
| Out of memory | The evaluation running alongside the app stack got Ollama and the backend killed, interrupting a session's analysis | Run training and evaluation only when the app is idle. The interrupted session can be re-analysed from its results page. |
| Background jobs and session restarts | A 2-hour tool timeout and a session restart killed evaluation runs | Long jobs are started detached (`setsid nohup`), and the evaluation scripts resume from saved results |

## 13. File map

```
fine-tune/
  README.md                 this document
  RESULTS.md                every run (incl. failed), evaluation tables, licences
  docs/manglish-finetune-plan.md   plan, phases F0-F9 with status, design decisions
  STYLE_GUIDE.md            transcription rules + disfluency marking
  RECORDING_PROMPTS.md  SPEAKER_SCRIPT.md  OWN_DATA_GUIDE.md  templates/clips.csv
  requirements.txt          training venv
  scripts/
    prepare_smoke.py        F4 smoke-test data (204 FLEURS Malay clips)
    prepare_public.py       10.3 h public training set → data/
    prepare_own.py          your recordings → data/ + eval/real/
    train_lora.py           LoRA training (smoke: `<model> 200`; full: `LR=1e-4 … <model>`)
    export.py               merge adapter + convert to CTranslate2 int8 → out/merged, out/ct2
    make_paper_eval.py      500-clip test set → eval/paper/ (English, Malay, mixed)
    eval_finetune.py        shipped vs fine-tune vs Whisper large-v3, through the app's code
    eval_routing.py         code-switch routing on vs off (paper)
  data/   (git-ignored)     clips/, train.csv, dev.csv, own/<speaker>/
  eval/   (git-ignored)     paper/ (clips, manifest, results), real/ (own test speakers)
  out/    (git-ignored)     adapter/, merged/, ct2/, ct2_base/, run logs
```

The audio, models and venvs are git-ignored (about 33 GB in total). Everything can be rebuilt with §8.
