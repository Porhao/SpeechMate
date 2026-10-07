# Confidence model

Code: `app/services/live/scoring.py` (`CONFIDENCE_CUES`, `confidence_cue_scores`, `estimate_confidence`). Tests: `tests/test_live.py`.

## What it measures

Confidence is an inner state; no sensor reads it. What can be measured is **perceived confidence**: how confident a speaker comes across to a listener. The model scores the cues listeners react to, all of which SpeechMate already measures.

| Cue | Channel | Weight | Score rule (0–100) | Measured by |
|---|---|---|---|---|
| Speaking pace | voice | 10% | 100 inside 120–160 wpm, −1.5 per wpm outside | words ÷ own talking time |
| Hesitation pauses | voice | 12% | 100 up to 20/min, −4 per extra pause/min | 0.25–3 s gaps between words |
| Word repetitions | voice | 8% | −15 per repetition/min | "I I think" in the transcript |
| Stutter blocks & stretches | voice | 7% | −25 per event/min | 1.2–3 s silences mid-answer, prolonged sounds |
| Filler words | voice | 8% | 100 up to 2/min, −10 per extra filler/min | um, uh, like, macam, ... |
| Time to start answering | voice | 5% | 100 up to 1.5 s, −12 per extra second | browser: end of AI turn → first sound |
| Confident expression | face | 10% | the expression model's confidence level | facial-expression model on 12 frames |
| Relaxed face | face | 8% | 100 − facial tension | share of fearful / angry / sad expressions |
| Upright posture | body | 11% | posture score | MediaPipe Pose: head and shoulder alignment |
| Steady body | body | 7% | body stability | MediaPipe Pose: torso movement |
| Eye contact | body | 14% | % of frames looking at the lens | MediaPipe Face Mesh iris position |

**Score** = weighted average of the cues that were measured. **High** ≥ 75, **Medium** ≥ 50, else **Low**.

## Design decisions

- **Rates, not counts.** Pauses, repetitions, blocks and fillers are per minute of the user's own talking time. An earlier version used raw counts, so a 5-minute session looked less confident than a 1-minute one with the same habits.
- **Turn changes are not hesitations.** In a conversation the AI's turns are silence in the user's recording. Gaps of 3 s or more count neither as pauses nor as blocks, nor as talking time.
- **Missing cues are left out, not guessed.** The weights are renormalised over what was measured, and the result reports its `coverage` (share of the total weight measured). Under 30% coverage there is no score at all.
- **Explainable.** Every result carries its `cues` (value, score, weight), shown on the results page weakest first, so the user sees *why* and what to work on.
- **No double counting of pace.** The old version mixed the fluency score (which already includes pace) with pace again.

## Limits, and how to validate it

- The weights and thresholds are a reasoned starting point from the speaking-assessment literature and from SpeechMate's own recordings (normal speech has ~15–20 short pauses a minute). **They are not fitted to data yet.**
- Facial-expression models are trained mostly on posed, non-Malaysian faces; a neutral face can read as "sad". That is one reason face cues carry only 18% of the weight.
- Cultural norms differ: steady eye contact is read differently across cultures, and Malaysian English has its own rhythm.

**Validation study (recommended for the FYP evaluation):**
1. Collect 30–50 recorded answers (the recording sessions in `fine-tune/SPEAKER_SCRIPT.md` work).
2. Ask 2–3 people to rate each one for "How confident does this speaker sound and look?" on a 1–7 scale, without seeing SpeechMate's score. Check that the raters agree with each other (ICC, or Spearman between raters).
3. Compare their average rating with the model's score (Spearman correlation). Report it, and per-cue correlations to show which cues matter.
4. If you have enough clips, refit the weights with a simple linear regression on the cue scores, using cross-validation, and keep the rules readable.
