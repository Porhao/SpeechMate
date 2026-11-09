# Running the real-speaker evaluation

The scripts for the human-rated studies in `TECHNICAL.md` §IV.C are ready before the data exists. When the recordings and ratings arrive, each study is one command.

Every result is printed as JSON with a 95% confidence interval and compared with the pre-registered threshold.

## Steps

1. **Record and prepare the clips.** Get consent (`CONSENT_FORM.md`), record each speaker with `EVAL_SPEAKER_SCRIPT.md` (about 10 minutes each) and write the transcripts (`OWN_DATA_GUIDE.md`, step 4). Then run:
   ```
   python fine-tune/scripts/prepare_own.py --test s01 s02 …
   ```
   This writes the held-out test clips to `fine-tune/eval/real/` (`001.wav` …), with their human transcripts in `refs.json`, the original file of each clip in `sources.csv`, and each clip's group in `groups.csv`. Silent clips have the reference `""`. For the confidence ratings, also run the videos: `run_app_on_clips.py --clips fine-tune/eval/video --out fine-tune/eval/video/app`.
2. **Run the clips through the deployed app** (backend running, Groq and Gemini keys set):
   ```
   python fine-tune/scripts/run_app_on_clips.py --clips fine-tune/eval/real --out fine-tune/eval/real/app
   ```
   - It uses a separate evaluation account, never the demo account, and deletes each session after reading it (`--keep` to keep them).
   - It is resumable: clips already in `app/analysis/` are skipped.
   - Each clip costs one speech-to-text request plus one or two LLM calls.
3. **Annotate and rate** (spreadsheets saved as CSV, formats below; empty templates in `fine-tune/templates/`, instructions and questionnaire in `STUDY_MATERIALS.md`). Annotators and raters must not see the app's output.
4. **Compute:**
   ```
   python fine-tune/scripts/study_stats.py asr     --refs fine-tune/eval/real/refs.json --hyps fine-tune/eval/real/app/app_outputs.csv --groups fine-tune/eval/real/groups.csv
   python fine-tune/scripts/study_stats.py events  --gold annotations.csv --system fine-tune/eval/real/app/app_events.csv
   python fine-tune/scripts/study_stats.py ratings --ratings ratings.csv --system fine-tune/eval/real/app/app_scores.csv    # pronunciation (audio)
   python fine-tune/scripts/study_stats.py ratings --ratings ratings.csv --system fine-tune/eval/video/app/app_scores.csv   # confidence, overall (video)
   python fine-tune/scripts/study_stats.py likert  --responses uat.csv
   ```
   `python fine-tune/scripts/study_stats.py selftest` checks the statistics on made-up data with known answers.

## CSV formats

| File | Columns | Notes |
|---|---|---|
| `groups.csv` | `clip_id, group` | written by `prepare_own.py` from the prompt (`english`, `malay`, `mixed`, `noisy`, `silent`); results are reported per group and overall |
| `annotations.csv` | `clip_id, type, t_sec, annotator` | `type` = `filler`, `repetition`, `block`, `prolongation`; `t_sec` = start of the event in the clip. Have a second annotator mark at least 20% of clips so agreement can be reported |
| `ratings.csv` | `clip_id, rater, construct, score` | `construct` = `confidence` (1–7: "How confident does this speaker sound and look?"), `pronunciation` (1–7: "How clear is the pronunciation?"), `overall` (supervisor, 1–10). 2–3 raters, blind to the app's scores |
| `uat.csv` | `participant, condition, item, score` | 1–5 Likert. `condition` = e.g. `grounded` vs `generic` (feedback quality) or `deferred` vs `realtime` (deferral study); `item` = `specific`, `actionable`, `accurate`, `anxiety`, … Each participant rates both conditions (within-subject) |
| `app_outputs.csv`, `app_events.csv`, `app_scores.csv` | written by `run_app_on_clips.py` | the app's transcript, timed disfluencies and scores per clip |

## What each study reports

| Study | Statistic | Pre-registered target | Command |
|---|---|---|---|
| Speech recognition | WER per group, **raw** and **spelling-normalised**; silent clips with any text | below the standard-Whisper baseline; 0 text on silence | `asr` |
| Filler and disfluency detection | precision, recall, F1 (± 0.5 s match), per type and overall, with bootstrap CI over clips | F1 ≥ 0.75 | `events` |
| Rater agreement | ICC(2,1) and ICC(2,k) (two-way random, absolute agreement), with bootstrap CI; Spearman between each pair of raters | ICC(2,k) ≥ 0.75 is "good" (Koo & Li 2016) | `ratings` |
| Validity of app scores | Spearman and Pearson between the app's score and the mean rating, with Fisher CI and permutation p | pronunciation r ≥ 0.7 · confidence ρ ≥ 0.5 · overall r ≥ 0.6 | `ratings` |
| Feedback quality / deferral | mean per condition with CI; paired Wilcoxon signed-rank p and effect size r | mean ≥ 4 / 5 and better than the comparison condition | `likert` |

## Notes on method

- **Spelling-normalised WER** maps the spelling variants in `STYLE_GUIDE.md` to one form ("la" → "lah", "ok" → "okay", "kenyanglah" → "kenyang lah") before scoring. Report both versions: the raw number for comparability, the normalised one for how often the words are actually wrong.
- **Bootstrap CIs** resample clips (or participants) 5,000 times with a fixed seed, so results are reproducible.
- **Event matching** is one-to-one within ± 0.5 s of the annotated start. Change it with `--tolerance`.
- **Wilcoxon** is exact (all sign patterns) up to 20 participants, and uses the normal approximation with tie correction above that.
- **Sample sizes** (from TECHNICAL.md §IV.C):
  - confidence ρ = 0.5 needs about 29 clips;
  - pronunciation r = 0.7 with 30 clips gives a CI of about [0.45, 0.85];
  - a paired study with a medium effect (d = 0.5) needs about 34 participants.
