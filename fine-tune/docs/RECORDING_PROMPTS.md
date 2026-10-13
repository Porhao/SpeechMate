# Recording Session Prompts

One session takes about 25 minutes and produces 35-40 clips per speaker. Ten speakers give about 2 hours of audio. The prompts follow SpeechMate's three uses (conversation, mock interview, presentation practice). They are mixed so you get English-heavy, Malay-heavy and mixed clips, plus fillers, particles, numbers, noise and silence. Transcribe everything with `STYLE_GUIDE.md`.

## Before you start

- [ ] Consent form signed. Speaker code assigned (`s01`, `s02`, ...) and written on the form.
- [ ] Recording 16 kHz mono, or convert afterwards (`STYLE_GUIDE.md` §1). Check one test clip plays back clearly.
- [ ] Tell the speaker:
  - "There are no right answers, just talk like you normally would with friends."
  - "Mixing English and Malay is good. So are 'um', 'lah' and so on."
  - "Please don't say your full name, IC, phone number or address."
  - "Aim for 10-30 seconds per answer. I'll stop you if it runs long."

**Your own style sets theirs.** Ask casual prompts in Manglish yourself. If you ask in formal English, they answer in formal English.

## Session plan

| Block | Prompts | ~Clips | ~Minutes | What it gets |
|---|---|---|---|---|
| A. Warm-up chat | A1-A8 | 8 | 5 | Natural code-switching, particles, fillers |
| B. Mock interview | B1-B8 | 8 | 6 | English-leaning answers under mild pressure (most fillers) |
| C. Presentation + Q&A | C1-C4 | 6 | 5 | Longer explanations, technical words, split into clips |
| D. Malay-leaning | D1-D5 | 5 | 3 | Mostly-Malay speech with English words mixed in |
| E. Numbers and names | E1-E4 | 4 | 2 | Digits, prices, dates, abbreviations |
| F. Noisy repeats | 3 earlier prompts | 3 | 2 | Same kinds of speech with background noise |
| G. Silence | G1-G2 | 2-3 | 1 | Empty-transcript clips |

Skip or swap any prompt that doesn't suit the speaker. Variety across speakers is good.

## A. Warm-up chat (ask in Manglish)

| # | Prompt |
|---|---|
| A1 | What did you do last weekend ah? |
| A2 | Where's your favourite place to makan? Why that place? |
| A3 | Tell me about a time you got lost or something went wrong on a trip. |
| A4 | How do you usually get to uni or work? Got jam or not? |
| A5 | What's one thing you're stressed about this week? |
| A6 | Recommend me a show, movie or game, and convince me lah. |
| A7 | What would you do if you got one month holiday with no work? |
| A8 | Describe your hometown to someone who's never been there. |

## B. Mock interview (ask like an interviewer, in English)

| # | Prompt |
|---|---|
| B1 | Tell me about yourself. |
| B2 | Why are you interested in this role, or the field you're studying? |
| B3 | What's your biggest strength? Give me an example. |
| B4 | Tell me about a weakness and what you're doing about it. |
| B5 | Describe a time you worked in a team and there was a conflict. |
| B6 | Tell me about a problem you solved at work, uni or in a project. |
| B7 | Where do you see yourself in five years? |
| B8 | Do you have any questions for us? (Any made-up question is fine.) |

## C. Presentation practice and Q&A

| # | Prompt |
|---|---|
| C1 | Give a one-minute introduction to your final-year project, your job, or something you know well. Talk as if you're presenting to a class. (Expect about 60 s: split it into 2-3 clips on pauses.) |
| C2 | Explain how to cook a dish you know, step by step. |
| C3 | Q&A follow-up on C1: "Why did you choose that approach?" |
| C4 | Q&A follow-up on C1: "What would you do differently next time?" |

## D. Malay-leaning (ask in Malay)

| # | Prompt |
|---|---|
| D1 | Cerita sikit pasal keluarga awak. |
| D2 | Apa pendapat awak tentang harga barang sekarang? |
| D3 | Terangkan macam mana nak pergi rumah awak dari stesen LRT atau MRT terdekat. |
| D4 | Kalau awak boleh ubah satu benda di Malaysia, apa dia dan kenapa? |
| D5 | Cerita pasal cikgu atau pensyarah yang paling awak ingat. |

## E. Numbers and names

| # | Prompt |
|---|---|
| E1 | What did you spend money on yesterday? Roughly how much for each thing? |
| E2 | When is your birthday, and what's the plan for your next one? (Day and month only, not the year.) |
| E3 | What are your class or work hours? Walk me through a typical day with times. |
| E4 | Name a few companies, apps or brands you use every day, and what for. |

## F. Noisy repeats

Repeat three earlier prompts the speaker liked (for example A2, B1, D2) under one condition each:
1. A fan, TV or café-noise video playing in the background at normal volume.
2. A phone held at arm's length, or a laptop mic about 1 m away.
3. Outdoors, or near a window with traffic.

Note the condition in the log.

## G. Silence

| # | What | Transcript |
|---|---|---|
| G1 | 5-8 s of the speaker sitting quietly (normal room) | `""` |
| G2 | 5-8 s of only the noise from F1 | `""` |

## After the session

1. **Name files** `<speaker>_<clip>.wav`, numbered in recording order: `s03_001.wav`, `s03_002.wav`, ...
2. **Fill in the log**, one row per clip. It makes the `language` column and the test-set choice easy later:

```csv
file_name,prompt,device,condition,notes
s03_001.wav,A1,laptop,quiet,
s03_015.wav,C1 part 2,laptop,quiet,split on pause at 31 s
s03_034.wav,A2,phone,cafe-noise,
```

3. **Split** any clip over 30 s on a pause, and cut out any personal details.
4. **Choose the test speakers before transcribing anyone's training clips.** The first 2-3 speakers (30-50 clips) are good candidates: they become `refs.json` for `bench_stt.py --real` and never go into training.
