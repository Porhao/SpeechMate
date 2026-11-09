# SpeechMate Evaluation Session: Short Script

About 10 minutes per speaker: 9 short audio clips plus one 1–2 minute video. This is the **test-only** version of `SPEAKER_SCRIPT.md`. The app uses Groq's Whisper, so no training data is needed, only enough real speech to measure it. The file numbers match the full script, so `prepare_own.py` and `STYLE_GUIDE.md` work unchanged.

Before starting, check that the speaker has signed the consent form (`CONSENT_FORM.md`) and has a speaker code (`s01`, `s02`, ...).

## Read this to the speaker first

> Thanks for helping! I'm testing how well SpeechMate understands the way people in Malaysia really speak.
>
> - There are no right or wrong answers. Just talk like you normally would.
> - Mixing English and Malay is good. So are "um", "lah", "kan" and so on.
> - Please **don't say** your full name, IC number, phone number or home address.
> - Aim for **10 to 30 seconds** per answer.
> - You can skip any question, and you can stop at any time.

## Audio clips (phone voice recorder, about 30 cm away, one recording per number)

| File | Group (written to `groups.csv` for you) | Ask |
|---|---|---|
| 001 | mixed | (casually, in Manglish) What did you do last weekend ah? |
| 002 | mixed | Where's your favourite place to makan? Why that place? |
| 009 | english | (like an interviewer) Tell me about yourself. |
| 014 | english | Tell me about a problem you solved at work, uni or in a project. |
| 017 | english | Give a short introduction to your project or job, as if presenting to a class (stop at about 30 s). |
| 023 | malay | (in Malay) Cerita sikit pasal keluarga awak. |
| 025 | malay | Terangkan macam mana nak pergi rumah awak dari stesen LRT atau MRT terdekat. |
| 032 | noisy | Repeat any question they liked, with a fan, TV or café-noise video playing at normal volume. |
| 035 | silent | 5–8 seconds of the speaker sitting quietly. |

## Video (for the confidence and body-language ratings)

| File | What |
|---|---|
| `video.mp4` | Phone on a stand at eye level, head and shoulders in frame, good light in front of the speaker. Ask: "Introduce yourself and tell me about something you're working on, as if at an interview." **1–2 minutes**, one take. |

Only record video if the speaker ticked the video box on the consent form.

## After the session

- [ ] Copy the files into `fine-tune/data/own/<code>/`: `001.m4a`, `002.m4a`, ... and `video.mp4`.
- [ ] Copy `fine-tune/templates/clips_eval.csv` into the same folder as `clips.csv` and write the transcripts (`STYLE_GUIDE.md`). Leave 035 empty.
- [ ] Copy `video.mp4` to `fine-tune/eval/video/<code>.mp4` for the rating study.

Then follow `EVALUATION.md` from step 1, with every speaker as a test speaker: `prepare_own.py --test s01 s02 ...`.
