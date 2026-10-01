# Transcription Style Guide (Manglish recordings)

Every clip in the test set and the training set follows these rules. The model learns your spelling habits. The smoke test showed this: after training on FLEURS it wrote "tiga" instead of "3". So **consistency matters more than any single choice**. When a case isn't covered, decide once, add it to §11, and apply it everywhere.

**Golden rule: write what the speaker said, not what they meant.** Don't fix grammar, don't translate, don't tidy up.

---

## 1. Recording

| Item | Rule |
|---|---|
| Consent | Signed consent from every speaker *before* recording (plus ethics approval if your university requires it). Record their speaker ID, not their name. |
| Format | 16 kHz mono WAV. Convert phone recordings: `ffmpeg -i in.m4a -ar 16000 -ac 1 001.wav` |
| Length | 3-30 s per clip. Split on a pause and never mid-word. **Over 30 s is rejected.** |
| Devices | What users actually use: laptop mic, phone. Some background noise is fine (and wanted). |
| Content | Interview answers, presentation openings, casual chat. Unscripted is better: read-aloud speech has no fillers or code-switching. |
| Mix | Aim for some clips mostly English, some mostly Malay, most mixed. Plus a few seconds of silence or room noise per speaker (transcript: empty). |

The full prompt list and session plan are in `RECORDING_PROMPTS.md`.

## 2. Fillers and hesitations (keep all of them)

The app's filler counter (`backend/app/services/live/speech.py`) only recognises these exact spellings, so use them:

| Sound | Write |
|---|---|
| short "um" / long "ummm" | `um` / `umm` |
| "uh" / long "uhhh" | `uh` / `uhh` |
| "er" / "err" / "erm" | `er` / `err` / `erm` |
| "em", "aa", "ah", "hmm" | `em`, `aa`, `ah`, `hmm` |

Don't invent others ("uhm", "ehh", "mmm"): pick the closest from the table.

**Discourse fillers** ("like", "you know", "I mean", "actually", "basically", "literally", "well", "right", "so yeah", "okay so", "macam", "sebenarnya") are counted only at the start of a clause or when followed by a comma. **So use the comma** when they are used as fillers:

- Filler: `So, like, I think the data was wrong.` ✓
- Not a filler: `I like the data.` (no comma)

## 3. Manglish particles

Write particles as **separate words**, always with the same spelling. The app's particle counter misses attached forms like "kenyanglah".

| Spoken | Write | Never |
|---|---|---|
| lah, la | `lah` | la, laa, kenyanglah |
| lor, loh | `lor` | loh |
| mah | `mah` | ma |
| leh | `leh` | lei |
| meh | `meh` | |
| kan | `kan` | kann |
| weh, wei | `weh` | wei |
| aiyo, aiyoh | `aiyo` | aiyoh |
| wah | `wah` | waa |

Example: `Okay lah, I try first lor.`

## 4. Malay spelling

Write **the form that was said**. Use the colloquial short form if they said it, and the full form if they said that. Colloquial spellings to use:

| Said | Write |
|---|---|
| tak / tidak | `tak` / `tidak` (whichever was said) |
| takde, tak de, tak ada (fast) | `takde` |
| nak / hendak | `nak` / `hendak` |
| dah / sudah | `dah` / `sudah` |
| je, aje / sahaja | `je` / `sahaja` |
| kat / dekat | `kat` / `dekat` |
| ni, tu | `ni`, `tu` |
| camne, macam mana | `macam mana` (unless clearly "camne") |
| sikit | `sikit` |
| ke (question) | `ke` |
| ape, apa | `apa` |
| boleh, bole | `boleh` |
| okay, ok, okey | `okay` (English or Malay) |

Full words use standard Malay (DBP) spelling. **Reduplication** (repeated words): write them with a hyphen, `kanak-kanak`, `sama-sama`. Scoring splits on the hyphen anyway.

## 5. English

- British spelling, the Malaysian standard: `colour`, `organise`, `programme` (but `program` for software).
- Contractions as said: `don't`, `I'm`, `gonna`, `wanna`.
- Manglish grammar stays: `Got one problem only`, `Already done what`. Don't correct it.

## 6. Numbers, names, abbreviations

| Case | Rule | Example |
|---|---|---|
| Numbers spoken as quantities, years, times, scores | **Digits** (Whisper's habit) | `I scored 3.8`, `in 2024`, `at 3 pm`, `2 orang` |
| "one" or "satu" as a word, not a count | Words | `the one I like`, `satu hari tu` (one day) |
| Abbreviations spoken as letters | Capitals, no dots | `FYP`, `UM`, `CGPA`, `KL` |
| Names | Normal spelling | `Universiti Malaya`, `Petronas` |
| Brands and tech words | Usual spelling | `wifi`, `PowerPoint`, `Excel` |

## 7. Disfluencies and noise

| Case | Rule | Example |
|---|---|---|
| Repeated whole words (stutter) | **Keep every repeat**: the stutter metric needs them | `I I I think the the result` |
| Cut-off word fragment | **Drop it** | "prob- problem" → `problem` |
| Restart mid-sentence | Keep both parts | `I went to the, we went to KL.` |
| Laughs, coughs, breaths, background talk | Don't write them, no tags | |
| A word you can't make out after 3 listens | Don't guess. **Drop the clip** (or cut that part out). | |
| Silent or noise-only clip | Empty transcript `""` | |

## 8. Punctuation and capitals

Keep it light: a capital at the start of a sentence, `.` or `?` at the end, and commas around fillers (§2) and at clear pauses. Scoring lowercases and strips punctuation, so beyond the filler commas this only affects readability.

## 9. Files

**Test set** (scored by `bench_stt.py --real`): put `001.wav`, `002.wav`, ... and `refs.json` in one folder.
```json
{"001": "Um, so basically, saya rasa the project okay lah.", "002": ""}
```

**Training set** (`fine-tune/data/`): put the clips in `data/clips/` and one row per clip in `train.csv` or `dev.csv`.
```csv
file_name,transcript,language,speaker,source
s03_007.wav,"Um, so basically, saya rasa the project okay lah.",en,s03,own-recording
```
- **language** is the language of most of the words: `en` or `ms`. For a tie, use the language of the sentence grammar. Silent clips use the speaker's main language.
- **speaker** is a stable ID (`s01`, `s02`, ...). The splits are by speaker, so get it right.
- **Test speakers never appear in train or dev.** Choose the test speakers first.

## 10. Checking

- Listen to every clip in full, even when pre-filling with a model's output. Model drafts anchor you to their mistakes: "Actually" vs "Ashley", fillers silently dropped.
- A second person re-checks a random 10%. If they disagree with more than about 1 word in 20, find which rule caused it and fix the rule here.

## 11. Decisions log

Add new cases here as they come up (date, case, rule).

| Date | Case | Rule |
|---|---|---|
| 2026-10-02 | Initial guide | §1-10 |
