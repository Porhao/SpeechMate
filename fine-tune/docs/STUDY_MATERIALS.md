# Rater, Annotator and UAT Materials

The instructions and questionnaire for the human-rated studies in `EVALUATION.md`. Every result goes into a CSV in `fine-tune/templates/` (headers already filled in), and `study_stats.py` reads them.

**Rule for all three:** raters, annotators and participants must not see the app's scores for the clip they are judging.

---

## 1. Rater sheet: confidence and pronunciation (`ratings.csv`)

**Who:** 2–3 raters, ideally not the researcher. Give each the clips in a **different random order**.

**Instructions to read to raters:**
> You will hear (and for some clips, see) short recordings of Malaysian speakers. For each one, give two scores from 1 to 7. Rate how the person *comes across*, not their grammar or vocabulary. A Malaysian accent is not an error: judge clarity, not how native-like the speaker sounds. Use the whole scale. Don't go back and change earlier scores.

| Construct | Question | 1 | 4 | 7 |
|---|---|---|---|---|
| `confidence` | How confident does this speaker sound and look? | very nervous, hesitant | neutral | very confident, at ease |
| `pronunciation` | How clear is the pronunciation? | hard to understand | understandable with effort on some words | completely clear |
| `overall` *(supervisor only, 1–10)* | Overall, how effective is this as spoken communication? | poor | adequate | excellent |

**Which clips:** confidence uses the videos (`eval/video/`); pronunciation uses the audio clips. Score at least 30 of each.

**One row per score:** `clip_id, rater, construct, score`. The `clip_id` is the file name without extension: the speaker code for a video (`s07, R1, confidence, 5`) and the `eval/real` number for an audio clip (`012, R1, pronunciation, 6`).

**Before starting:** rate 3 practice clips together (not counted) and discuss any disagreement of 3 or more points, so raters use the scale the same way.

---

## 2. Annotator guide: fillers and disfluencies (`annotations.csv`)

**Who:** you, plus a second annotator on at least 20% of clips (for agreement).

Listen to each audio clip (Audacity or VLC shows the time) and mark every event:

| `type` | Mark when | Example |
|---|---|---|
| `filler` | a sound or word used only to fill a pause | "um", "uh", "er", "erm", "ah", "hmm" |
| `repetition` | a sound, word or phrase said again without meaning to | "I I think", "the the" |
| `block` | a stuck silence or strain before a word, mid-sentence | "I want to … (stuck) … go" |
| `prolongation` | a sound held unusually long | "sssso", "I'm verrry" |

**Not events:** discourse particles (`lah`, `kan`, `lor`, `mah`); "like" or "you know" used as normal speech; ordinary pauses between sentences.

**One row per event:** `clip_id, type, t_sec, annotator`, where `t_sec` is when the event **starts**, to 0.1 s (`012, filler, 3.4, A1`). Annotate from the audio, not from the app's transcript.

---

## 3. UAT questionnaire (`uat.csv`)

**Who:** about 34 participants who ticked the app box on the consent form.

### Study 1: feedback quality (grounded vs generic)

1. The participant does one **Interview** session in SpeechMate (about 5 minutes).
2. They receive two versions of feedback on the same session, in a counterbalanced order (half see A first), labelled only "Feedback A" and "Feedback B":
   - `grounded`: SpeechMate's results page;
   - `generic`: the session transcript pasted into a plain chatbot (Gemini) with only "Give feedback on this interview answer", printed in the same layout.
3. They rate each version on these items, 1 = strongly disagree, 5 = strongly agree:

| `item` | Statement |
|---|---|
| `specific` | The feedback refers to specific things I actually said or did. |
| `actionable` | I know exactly what to do differently next time. |
| `accurate` | The feedback correctly describes my performance. |
| `trust` | I trust this feedback. |
| `useful` | This feedback would help me improve. |

One row per rating: `p01, grounded, specific, 4`.

### Study 2: deferral (deferred vs real-time)

Pre-registered in `TECHNICAL.md` §IV.C, but it needs a "real-time alerts" mode in the app that **does not exist yet**. Run it only if that mode is built. Otherwise report it as future work.

If run: each participant does two **Conversation** sessions on different topics, one per condition (counterbalanced). After each session they rate, 1–5:

| `item` | Statement |
|---|---|
| `anxiety` | I felt nervous while speaking. *(adapted from FLCAS)* |
| `distracted` | Things on the screen distracted me while I was speaking. |
| `flow` | I could focus on what I wanted to say. |

### End of session (both studies)

Ask these open questions; quote them only in anonymised form:
- What was most useful about SpeechMate's feedback?
- What was confusing, wrong or missing?
- Would you use it to prepare for a real interview or presentation? Why or why not?

---

## Generic-feedback prompt (Study 1, keep it fixed)

```
Give feedback on this interview answer.

<transcript>
```

Use the same model (Gemini 3.5 Flash-Lite), with no system prompt and no other context, for every participant.
