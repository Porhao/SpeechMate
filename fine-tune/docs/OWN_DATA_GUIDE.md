# Your Own Recordings: Step by Step

Why: every fine-tune so far learned from synthetic TTS voices and read speech. To show the model works on **real Malaysian speakers**, which is the open go/no-go check in the plan (§11), you need recordings of real people. This guide is everything needed, from consent to training.

**Target:** 10 speakers × 25 minutes ≈ 2 hours of speech. Start with 3–5 speakers to test the pipeline end to end.

## What I need from you, per speaker

| Item | Where it goes | Format |
|---|---|---|
| Signed consent form | Kept by you, **not** in the project | Paper or PDF, with their speaker code (`s01`, `s02`, ...) |
| The 36 recordings | `fine-tune/data/own/s01/001.m4a`, `002.m4a`, ... | Any of: `.m4a` (phone), `.mp3`, `.wav`, `.webm`, `.ogg`. Any sample rate: the script converts to 16 kHz mono WAV. |
| The clip sheet | `fine-tune/data/own/s01/clips.csv` | Copy of `templates/clips.csv`, with the transcripts filled in |

`data/` and `eval/` are git-ignored, so recordings never get committed.

---

## Step 1. Before anyone records

- [ ] **Ethics approval** from your university, if it requires one for recording people (the plan, F0, says to get it).
- [ ] A **consent form** saying: what is recorded, that it's used to train and test a speech model for your FYP, where it's stored, that they can withdraw, and that no names, IC numbers or contact details are recorded.
- [ ] **Choose your test speakers now: 2 of the 10.** Their clips are only ever used to measure accuracy, never for training. Pick two who differ (for example one mostly-English, one mostly-Malay speaker).

## Step 2. Record a session (25 minutes)

Use **`SPEAKER_SCRIPT.md`**: print it, read the intro to the speaker, then ask the 36 numbered questions.

- **One recording per number.** Stop and start the recorder between questions. That's much easier than cutting one long file later.
- A phone's built-in voice recorder is fine; it's what real users have. Hold it about 30 cm away.
- Keep each answer to **30 seconds or less** (the script rejects anything longer: split long answers into two numbers).
- Blocks F (noise) and G (silence) matter: they teach the model to handle noise and to output nothing on silence.

## Step 3. Put the files in place

```
fine-tune/data/own/
  s01/
    001.m4a  002.m4a  ...  036.m4a
    clips.csv            ← copied from fine-tune/templates/clips.csv
  s02/
    ...
```

The file numbers must match `SPEAKER_SCRIPT.md`. A different extension is fine (`001.wav` matches the `001.m4a` row). Skipped a question? Leave that row in `clips.csv` with an empty transcript and `skipped` in notes; the script reports it and moves on.

## Step 4. Write the transcripts (the slow part)

Open `clips.csv` in Excel or Google Sheets. For each row fill in:

| Column | What to write |
|---|---|
| `transcript` | **Exactly** what they said, following `STYLE_GUIDE.md`. Leave empty only for the silence clips 035–036. |
| `language` | `en` or `ms`: the language of most of the words. Leave blank to use the default (questions 023–027 → `ms`, everything else → `en`). |
| `device`, `condition` | Already filled with the likely values; correct them if you changed anything (`phone` / `laptop`; `quiet` / `background-noise` / ...). |

The five rules that matter most (the full list is in `STYLE_GUIDE.md`):

1. **Write what was said, not what was meant.** No grammar fixes, no translation.
2. **Keep every filler**, spelled exactly `um`, `uh`, `er`, `erm`, `ah`, `hmm`, and put a comma after discourse fillers: `So, like, I think...`
3. **Particles as separate words, one spelling:** `lah`, `lor`, `mah`, `kan`, `weh`, `aiyo`.
4. **Numbers as digits:** `3 pm`, `RM 15`, `2 orang`.
5. **Keep stutters** (`I I think`), drop cut-off fragments (`prob- problem` → `problem`).

Expect about **5–10 minutes of work per minute of audio**. Save as **CSV (UTF-8)**.

## Step 5. Build the data

From `fine-tune/`:

```bash
.venv/bin/python scripts/prepare_public.py        # once: the public data (rewrites train/dev.csv)
.venv/bin/python scripts/prepare_own.py --test s01 s02 --dev s03
```

- `--test`: your test speakers from step 1. Their clips go to `eval/real/` (001.wav ... plus `refs.json`), never into training.
- `--dev`: one speaker used to choose the best training epoch.
- Everyone else goes into `data/train.csv`. Re-running is safe: your rows are replaced, not duplicated.

Lines starting with `!` are clips that were skipped (missing file, no transcript, over 30 s, ...). Fix them and run it again.

## Step 6. Measure the shipped model on real speakers (before training)

```bash
docker compose cp fine-tune/eval/real backend:/models/eval/
docker compose exec backend python scripts/benchmark/bench_stt.py --real
```

This is your **baseline**: word error rate of the current app on your real speakers. Write it in `RESULTS.md`.

## Step 7. Train and compare

```bash
cd fine-tune
LR=1e-4 .venv/bin/python scripts/train_lora.py mesolitica/Malaysian-whisper-large-v3-turbo-v3
```

Then score the fine-tune on the same `eval/real` clips and add a row to `RESULTS.md`. If it beats the baseline from step 6 on real speakers, you have the evidence the plan asks for. (`scripts/eval_finetune.py` currently scores `eval/paper`; pointing it at `eval/real` is a small change to make once you have the recordings.)

---

## Quick checklist

- [ ] Ethics approval and consent form ready
- [ ] Test speakers chosen (2)
- [ ] Each speaker: 36 recordings + `clips.csv` in `data/own/sXX/`
- [ ] Transcripts follow `STYLE_GUIDE.md`; a second person re-checks 10%
- [ ] `prepare_own.py` runs with no `!` lines
- [ ] Baseline measured (step 6) **before** training
