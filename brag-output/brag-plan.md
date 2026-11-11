# Brag Plan: SpeechMate

**Run note:** /brag full workflow, stretched on request from its 15–25 s format to a 4:42 product presentation + demo. The scene-by-scene script with its rationale is [`demo-video-script.md`](demo-video-script.md); this plan records the creative decisions.

## What is this app?
An AI speaking coach for Malaysian speakers (English, Bahasa Malaysia, Manglish) with mock interviews, presentation practice with Q&A, and daily conversation, with feedback only after you speak.

## The angle
The author's own story: practising alone or in front of a mirror and getting no feedback. Then the reveal of four characters (Mate plus one AI partner per feature) that turn practice into a learning loop.

## Hook (first 2–3 seconds)
A mirror rehearsal, then silence, then *"…so how did I do?"*

## Key moments
- The interview questions are tailored to *your* job and resume. The generic questions get struck through.
- The deck is understood first, then your talk is checked against each slide: "Knowing the content ≠ saying what it means."
- The agent loop: Know the learner → Plan → Practise → Check → Coach → Practise again, each step with its character.

## Outro / punchline
"No more practising to the mirror." The mirror shot returns with Mate beside you, then the SpeechMate wordmark and "Practise, and finally know what to improve."

## User flow worth showing
Profile → interview form → generated plan → live interview → results. Then upload deck → insights → present → per-slide results → Q&A. Then conversation → language tips. Animated: the learner uses rebuilt screens; see the section below.

## Tone
- Preset: `polished`
- Creative direction: personal FYP product presentation + live demo
- Interpretation: calm narrated pacing, one idea per beat, warm clay colours, no hype language

## Format: landscape, 1920x1080, 30 fps
## Duration: 282.2 s (4:42). This deliberately overrides brag's 15–25 s law at the user's request.

## Visual identity (from the project)
- Background: `#FFFAF0` (cream canvas), night `#0A1A1A` for the camera shots
- Text: `#0A0A0A`, accent ink `#1A3A3A`
- Feature colours, as in the app: Interview teal `#1A3A3A`, Presentation lavender `#B8A4ED`, Conversation pink `#FF4D8B`; plus mint `#A4D4C5`, peach `#FFB084`, ochre `#E8B94A`
- Display font: Inter 600, −0.035em (the app's `.font-display`)
- Strongest visual element: the plush bot characters, rendered from the app's own `bot-avatars` configs (Mate = blob, interviewer = mech, presenter = droid, chat buddy = cat), in the default / working / sleeping states

## Share copy (draft)
See share-copy.txt.

## Audio direction
- Role: warm bed under a narrated voiceover
- Voice: Kokoro-82M, voice `af_heart` (the app's Kokoro container), with English narration and English + Malay captions
- Music: vol-12 quiet under the story → vol-1 from the SpeechMate reveal → vol-12 to close, all at about 0.12–0.14 under the voice
- Music cue guidance: vol-1 preset (120.19 BPM). Strong cue 17.02 s is beat-locked to the wordmark reveal (s03 + 1.35 s)
- Audio-reactive treatment: none. With music at 0.14 under constant narration, the modulation would not be perceptible. Skipped on purpose
- SFX posture: sparse. Card place/slide on cards and chapter wipes, soft drops on chips, bells on the two wordmark moments
- Restraint rule: no effect over a spoken key line; nothing louder than the voice

## Storyboard
| # | Scene | Length | Content |
|---|---|---|---|
| 1 | Mirror | 23.9 s | camera slot; "…so how did I do?" |
| 2 | Not just me | 24.0 s | chips (graduates, anxiety, stage fright, practising alone) → 64% / 53% cards count up → Practise safely / See where to improve / Keep getting better |
| 3 | Introducing SpeechMate | 29.9 s | wordmark (beat-locked) + Mate wakes → EN / BM / Manglish chips → three feature cards with their bots → "Never interrupts you" |
| 4 | Profile | 11.6 s | Mate + 4 profile fields + slot |
| 5 | Mock interview | 44.7 s | teal chapter card → generic questions struck through → form fields + slot → plan points + slot → bot wakes, live slot, follow-up chip |
| 6 | Results | 23.3 s | four pillars → per-answer feedback → 3 drills chip, slot |
| 7 | Presentation | 46.1 s | lavender chapter card → upload + insights → present (bot listens) → covered / left out / match → big-type point |
| 7b | Q&A | 9.5 s | presenter bot working, slot |
| 8 | Conversation | 13.1 s | pink chapter card → chat buddy + Manglish chip + You said / Try saying card, slot |
| 9 | Agentic AI | 37.6 s | ring of six agent cards with characters, Mate in the centre, "It can't invent a problem", the loop sweep |
| 10 | Close | 18.6 s | 4.9% · 7.3% / Deleted / Explained tiles → mirror + Mate → wordmark + tagline |

## Voiceover script
The narration lines (English + Malay captions) are in `tools/narration.py`, which is the source of truth for the voice and the captions.

## Demo content: what is real and what is illustrative (2026-11-09 revision)
The demo is fully animated: the learner character (tools/person.py) uses rebuilt SpeechMate screens, and there are no footage slots left.
- **Real app output, shown word for word:** the interview question plan (POST /api/interview/plan for a fictional candidate, "Graduate Data Analyst at Nusantara Retail Group"); the deck insights, structure, key points and Q&A question for "Five Strategies for Effective Time Management" (already analysed in the local DB); the profile brief (the exact output format of services/learner.py); Mate's suggestion chips (MateChat.tsx); and all page labels and buttons. Stored in tools/real_outputs.json.
- **Illustrative, tagged on screen:** interview scores and stronger answer, per-slide match results, and the conversation's language tip. Each sits on a screen marked "ILLUSTRATIVE VALUES" or "ILLUSTRATIVE". The interview follow-up line and the chat partner's opening line are also written for the demo.
- **Real-life scenes:** the learner seen from behind, rehearsing to their mirror reflection (s01); three people practising alone (s02); the mirror again with Mate (s10).

## Revision 2026-11-10: concise narration, a continuous app walkthrough
- Narration cut from about 720 to about 300 words (`tools/narration.py`); the video is 4:02, with most of its time now spent in the demo.
- The demo is one browser window that stays on screen: login → home → profile → interview form → question plan (real) → live interview → results → deck upload → deck insights (real) → presenting → slide match → Q&A (real question) → conversation → language tips → progress.
- Pages are rebuilt from screenshots of the running app (nav pill, left rail, Mate in the corner, two-line option tiles, step cards, results layout). Clicks press and ripple, inputs get focus rings and a typing caret, and every page change has a loading bar and an address-bar update. Mate reacts with its real bubbles ("Done!", "Nice one!").
- Generator: `tools/demo.py` (it reuses helpers from `tools/build.py`).

## Revision 2026-11-10 (b): clearer voiceover, solid mascot, smoother picture
Feedback: out of sync, mascot stuck and see-through, voiceover hard to follow, text badly placed, demo unclear, video feels stuck.
- **Voiceover rewritten** (`tools/narration.py`) in plain words that describe each step as it happens on screen (~520 words). The voice now covers 247 s of the 310 s video (was 150 s of 297 s), so the demo no longer plays on in silence. Video: 5:10.
- **Captions** are paged to one line (≤ 62 characters, English + Malay) in step with the voice's word timings (`page_caption` in `tools/build.py`, self-test `selftest_pages`).
- **Mascot:** 12 bot frames (default / working / sleeping of all four characters) had been captured mid-fade at 49–84 % opacity, so Mate turned see-through whenever it changed pose. Alpha rescaled so every frame is solid (originals in `out_backup_2026-11-10/bots`). Pose changes are now instant swaps, not cross-fades, and every character breathes slowly (`tools/life.py`).
- **Zooms** centre their focus point and keep the window filling the frame above the captions, instead of pinning its left edge and sliding off the top and right (`zoom_xy`, self-test `selftest_zoom` in `tools/demo.py`). New zoom-ins on the sign-in form, profile, interview form and chat, where the app text was too small to read.
- **Camera:** each app scene breathes in and out by 1.8 % (starts and ends at rest, so cuts don't jump): no frame is ever fully still.
- **Step badge** on every app scene, e.g. "Mock interview · Step 2 of 5 · Question plan".
- **Music** extended for the longer cut (track 4 cross-fades in under the close).
- Previous render and sources: `out_backup_2026-11-10/`.
