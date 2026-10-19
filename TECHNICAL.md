# SpeechMate: Technical Report (paper source)

Source text for the IEEE paper. The section order follows the paper's outline. Every number traces to a file in this repository, named in the text or in Appendix C. Status labels:

- **[E]** implemented and evaluated;
- **[I]** implemented, not yet evaluated;
- **[D]** designed, not implemented;
- **[R]** implemented, then removed (with the reason).

Last updated 2026-10-15. Where this report and V1 of the paper (`docs/SpeechMate_IEEE_Paper V1.pdf`) disagree, this report reflects the current system. Appendix A lists every correction.

---

## Abstract

Weak spoken English is a leading reason Malaysian graduates fail interviews: 64% of surveyed employers cite poor English and 53% weak communication and presentation skills [1], [2]. AI speech-coaching tools exist, but they have three shortcomings for Malaysian learners:
- they judge accent against native-English norms;
- they deliver feedback during speech, which adds cognitive load for anxious speakers;
- they report gaze and vocal disfluency as unrelated numbers.

None advertises support for English–Bahasa Melayu code-switching ("Manglish").

This paper presents **SpeechMate**, a web-based coach with three practice functions: daily conversation, mock interview, and presentation practice with deck-grounded Q&A. Feedback is withheld until the session ends. Speech, voice, language, body-language and content analyses are fused into four interpretable pillars. A perceived-confidence model is built from 11 measured cues, and **Gaze Tunneling** correlates gaze aversion with disfluency on one session timeline. The feedback layer is grounded: every recommendation is chosen from measured issues, every interview question follows a server-enforced plan, and every rewritten "stronger answer" is checked for facts the speaker never said.

We report the speech-recognition design as an empirical study.
- **Model choice:** a Malaysian-adapted Whisper reduced WER from 51.3% (Whisper medium) to 7.9% on Malaysian speech. Automatic language identification then reduced it to 6.1% and removed a failure mode in which English was translated into Malay.
- **Routing:** a dual-engine router that sends code-switched audio to a specialised model detected code-switching perfectly on a 400-clip test set (200/200 mixed, 0/200 English). It nonetheless **more than doubled** WER on mixed speech (15.4% → 36.7%, 95% CI of the increase +19.9 to +22.7 points). The router was therefore removed.
- **Fine-tuning:** a LoRA fine-tune of the Malaysian model reduced WER on held-out synthetic Manglish from 14.5% to 6.7%, and on real US-English speech from 9.4% to 6.7% (the latter borderline: sign test p = 0.056).

The system is evaluated in its cloud configuration: Whisper large-v3 served by Groq for speech recognition and Gemini 3.5 Flash-Lite for language generation, with voice, vision and pronunciation analysis on the server. The ASR experiments above were run locally to choose and stress-test models. The deployed cloud engine was then measured directly on the same held-out clips:
- 4.9% WER on real English speech, 16.5% on synthetic Manglish and 7.3% on real Malay, indistinguishable from the same weights run locally;
- a median 0.56 s per spoken turn;
- about US$0.014 of transcription per 5-minute session.

Without a voice-activity filter in front, however, it invented text on 8 of 10 silent clips. A silence guard calibrated on Groq's own no-speech scores now removes all ten while keeping every speech segment tested.

All results are on read or synthetic speech. Pronunciation, disfluency, gaze, confidence and feedback-quality validation against human raters is pre-registered with fixed acceptance thresholds and not yet run.

**Keywords:** speech coaching, code-switching ASR, Malaysian English, accent-fair assessment, deferred feedback, cognitive load theory, multimodal analytics, LLM grounding.

---

## I. Introduction

Communication competence decides graduate employability in Malaysia: employers name poor English (64%) and weak communication and presentation skills (53%) as the main reasons graduates fail interviews [1], [2]. The barrier is less subject knowledge than delivering it under pressure, in a second language, often while switching between English and Bahasa Melayu [3].

A market of AI speech coaches has grown up around this need. As Section II.F shows, these tools are built around a native-English speaker in a low-anxiety setting:
- they treat a Malaysian accent as an error to correct;
- they present real-time feedback as a selling point;
- they report what the camera sees and what the microphone hears as separate scores.

### A. Problem Statement and Research Gap

Four problems motivate the work.
1. **Conversion under pressure.** Students working across languages hit blocks when turning thought into formal English under pressure. Communication apprehension and disfluency follow [3], [24].
2. **Practice without spontaneity.** Language apps build vocabulary but keep learners on isolated words and rehearsed phrases rather than spontaneous talk [4].
3. **Scripts that capture the gaze.** Practice tools that display a script invite the user to read it. Gaze locks onto the screen ("Gaze Tunneling") and no audience contact is practised [5].
4. **Interruption.** Most trainers fire alerts, warnings or timers mid-speech, competing for the working memory the speaker needs [6], [14].

The literature and product review (Sections II.E–F) identifies five gaps:
- **G1.** No accent-*fair*, as opposed to accent-*corrective*, assessment for Malaysian English.
- **G2.** No feedback-timing design justified by cognitive load for anxious speakers. Every reviewed product treats immediacy as a virtue.
- **G3.** No metric relating gaze behaviour to vocal disfluency on a shared timeline. Products that capture both report them side by side.
- **G4.** No measured treatment of Malay–English code-switched speech recognition in a coaching product, and no openly available Malay–English code-switching ASR benchmark (the closest, [63], releases its test sets on request only).
- **G5.** No grounding of LLM-generated coaching in measured evidence. Generic LLM feedback can praise or criticise things that never happened [37].

### B. Objectives and Contributions

Objectives:
- **O1:** lower up-front load before practice (deck understanding before presenting, question preview before an interview).
- **O2:** assess spoken proficiency on segmental and suprasegmental features with accent-aware treatment.
- **O3:** fuse gaze and disfluency on one timeline.
- **O4:** withhold all performance feedback until the session ends.
- **O5:** make AI-generated feedback traceable to measurements.

Contributions:
1. **An empirical design study of code-switched ASR for a coaching product.** It covers model selection, language-token behaviour, prompt effects and a dual-engine router. We show the router's *detection* is sufficient but its *engine* is not, and derive the condition any future router must meet (Section IV.B). The negative result is reported because it would otherwise be silently reproduced: the router also failed *silently* in deployment because of a dependency guard (Section IV.E).
2. **A grounded-feedback architecture:**
   - server-enforced question plans;
   - recommendation candidates limited to measured issues;
   - a fact check on generated model answers;
   - "unavailable rather than estimated" reporting with explicit evidence coverage.
3. **A deferred, multimodal report** organised as four pillars. It includes an 11-cue perceived-confidence model whose every weight and rule is visible to the user, and the Gaze Tunneling correlation.
4. **A LoRA fine-tuning record** for Malaysian Whisper, including the failed runs and their causes (timestamp-mode looping, overfitting, leakage, orthographic penalties).
5. **A pre-registered evaluation protocol** with acceptance thresholds and sample-size reasoning, fixed before the human-rated studies are run. It comes with a traceability matrix from objective to mechanism to metric.

### C. Outline

- Section II: related work.
- Section III: system design and methodology.
- Section IV: evaluation, including what the data can and cannot support.
- Section V: cost, limitations and threats to validity.
- Section VI: conclusions and future work.

---

## II. Related Work

### A. Presentation Skills and Formative Feedback

Formative feedback is among the strongest influences on learning, but its effect depends on what it targets and how it is timed [25], [26]. Feedback aimed at the task and at the process improves performance. Feedback aimed at the self, or delivered so that it threatens self-image, can lower it: in Kluger and DeNisi's meta-analysis about a third of feedback interventions reduced performance [27].

Good formative feedback has four properties [28]:
- it clarifies the target;
- it is specific;
- it arrives when the learner can act on it;
- it supports self-regulation.

Carless shows that teachers and students systematically perceive the same feedback differently [6]. Butler and Winne place feedback inside self-regulated learning [15].

On timing, the evidence is mixed. Immediate feedback helps procedural, well-rehearsed tasks. Delayed feedback can match or beat it for transfer and for complex tasks [26], [29]. Spoken presentation by an anxious second-language speaker is complex, open-ended, and accompanied by communication apprehension [3], [24], [30]. That is the case for which this work argues delay is preferable (Section III.H). It is a hypothesis to test, not an established result.

**Design consequences:**
- feedback is task- and process-level (what was said and how), never a judgement of the person;
- each item names the evidence, why it matters, one drill and a target relative to the learner's own value [28].

### B. Cognitive Load, Worked Examples and Multimedia

Working memory has a strictly limited capacity. When intrinsic and extraneous load exceed it, performance collapses [14], [31]. Speaking in a second language already carries high intrinsic load (planning, lexical retrieval, monitoring). Any on-screen score, alert or script while speaking adds extraneous load.

Three cognitive-load findings shape the design:
- **Worked examples.** Novices learn more from studying worked examples than from solving equivalent problems [32]. The benefit reverses as expertise grows [33].
- **Multimedia principles.** The coherence, redundancy and signalling principles [34] argue against duplicating speech as on-screen text while the learner speaks.
- **Gaze aversion.** People look away when a task is cognitively demanding, and averting gaze improves recall and response quality [35], [38]. This matters for Gaze Tunneling (Section III.G): looking away while struggling may be adaptive, so the metric is reported as a *relationship to notice*, not a fault.

**Design consequences:**
- deck understanding (summary and each slide's key point) and the interview question preview are offered *before* the session (O1);
- worked examples are given *after* it: a "stronger answer" rebuilt from the learner's own facts, and per-slide "what you covered / what you left out";
- nothing performance-related is shown during speech.

The original design also generated a narrated example presentation of the user's own deck, as a worked example. It was implemented and later withdrawn **[R]** (Section III.B).

### C. Speech Technology and Fair Assessment

Modern ASR (Whisper [39], wav2vec 2.0 [40], XLS-R [41]) reaches low error on standard benchmarks but degrades on under-represented accents and dialects. Koenecke et al. measured large WER gaps by speaker group across commercial systems [22]. Whisper's own model card reports uneven accuracy across languages [39]. Whisper also produces text on silence, which has caused documented harms [42].

No public Malay–English code-switching benchmark exists. Published ballparks (about 21% WER off-the-shelf on code-switched Malay–English) come from unreviewed sources. Code-switched ASR adaptation works for related pairs (Mandarin–English [64]; Singapore languages including Malay–English [63]), but most such models are not released. Malaysian-adapted Whisper models are released without a stated licence [65].

Pronunciation assessment is classically scored by Goodness of Pronunciation (GOP) over a forced alignment [43]. Alignment noise of 30–60 ms predicts GOP only weakly, and mostly for plosives and fricatives [13]. Strict thresholds therefore punish measurement noise as if it were mispronunciation.

For fair assessment, the error measure must not encode the accent as error:
- **ASR:** a Malaysian speaker's English must not be transcribed worse because it is Malaysian (or translated into Malay; Section IV.D).
- **Pronunciation:** the reference must not be native-norm by construction.
- **WER:** spelling variants of the same spoken form ("lah"/"la", "weh"/"wei") must not count as errors (Section IV.E).

### D. Phonological Basis for the Accent-Fairness Set

Applied phonology distinguishes the **nativeness principle** (sound like a native speaker) from the **intelligibility principle** (be understood) [44]. Accent strength, comprehensibility and intelligibility are partly independent: a strong accent can be fully intelligible [45]. The Lingua Franca Core lists which features matter for intelligibility in international English [46]. Assessment for Malaysian learners should therefore penalise only deviations that cost intelligibility.

Documented systematic features of Malaysian English [47]–[49] form the **accent-fairness set**, the deviations that should *not* be penalised:

| # | Feature | Example | Source | Intelligibility risk |
|---|---|---|---|---|
| F1 | Dental fricatives realised as stops (/θ/ → [t], /ð/ → [d]) | *think* → [tɪŋk] | [47], [48] | Low in context |
| F2 | Final consonant-cluster reduction | *last* → [las] | [47], [48] | Low to medium (past tense *-ed*) |
| F3 | Reduced vowel-length contrast (/iː/–/ɪ/, /uː/–/ʊ/) | *ship/sheep* | [49] | Medium for minimal pairs |
| F4 | Final stop glottalisation or unreleased stops | *cat* → [kaʔ] | [47], [48] | Low |
| F5 | Syllable-timed rhythm; reduced vowel reduction in unstressed syllables | — | [47] | Low |
| F6 | Monophthongised diphthongs (/eɪ/ → [e], /oʊ/ → [o]) | *day* → [de] | [47], [49] | Low |
| F7 | Discourse particles (*lah, lor, meh, kan*) | *okay lah* | [47] | None: a lexical feature, not an error |
| F8 | Non-rhotic r: no /r/ after a vowel, centring diphthongs as single vowels | *clear* → [kliː], *shared* → [ʃɛd] | [47] | Low |

Realisations differ between Malay-, Chinese- and Indian-influenced Malaysian English [48]. This is a coverage threat for any single fairness set (Section V.C).

**Implementation status [I] (2026-10-16).** Per-phone deviations are classified against F1–F4, F6 and F8 as *regional variation* (accepted) versus *intelligibility-affecting* (flagged); Section III.E. F5 (rhythm) is not scored. F7 is implemented separately: particles are excluded from filler counts and reported in a language-mix card, never as errors. The two buckets are shown to the user, so fairness is a visible property of the scoring rule.

### E. Speaking Assistants and Presentation Coaching

**Multimodal public-speaking coaches.**
- *Presentation Trainer* [50] gave real-time feedback on voice and body posture and reported that interrupting users mid-speech was disruptive.
- *Rhema* [51] gave in-situ live feedback through smart glasses.
- *ROC Speak* [52] gave *post hoc* semi-automated feedback on recorded video.
- *Cicero* [53] simulated a reactive virtual audience.
- *MACH* [54] ran mock job interviews with a virtual agent and gave post-session multimodal feedback, with measured interview-skill gains.

MACH and ROC Speak show that **post-session feedback is not new**. Our contribution is the explicit cognitive-load argument for withholding *all* in-session performance signals, a second-language and code-switching setting, and grounding the feedback in measurements (G5).

**Newer systems.**
- An LLM speaking assistant for non-native speakers gives real-time text suggestions; it improved response structure but added on-screen load and hallucination risk [21].
- A wearable tri-zone gaze system increased eye contact by 62.5% using real-time voice prompts [18].
- Query-attention approaches estimate audience attention in virtual speech [5].
- *PresentCoach* [55] pairs an "ideal presentation" agent that narrates the user's own slides with a coach agent that compares rehearsals against it and gives Observation–Impact–Suggestion feedback. SpeechMate's presentation function re-implemented this dual-agent design (Section III.B).

Disfluency detection uses deep models such as FluentNet (SE-ResNet + BiLSTM + attention) [17]. These are trained on corpora such as UCLASS and LibriStutter that do not capture real psychological blocks or Malaysian speakers.

### F. Comparison of Current Tools

Product claims below are from vendor pages and reviews as of the review date (2026) [7]–[12]. They should be re-verified at submission.

| Capability | Orai | Speeko | Poised | Yoodli | Elqo | ELSA Speak | BoldVoice | **SpeechMate** |
|---|---|---|---|---|---|---|---|---|
| Phoneme-level pronunciation | – | – | – | – | – | ● | ● | ◑ word-level proxy |
| Accent stance | n/a | n/a | n/a | n/a | n/a | toward US norm | toward US norm | regional allowance ◑, particles ● |
| Camera analysis (eye, posture, expression) | – | – | – | ◑ | ● | – | – | ● |
| Gaze–disfluency relation | – | – | – | – | – (separate scores) | – | – | ● (approximate) |
| Feedback timing | real-time | post | real-time | real-time + post | post | real-time | real-time | **post only** |
| Malay–English code-switching (advertised) | – | – | – | – | – | – | – | ◑ (measured, Section IV) |
| Role-play / mock interview | – | – | – | ● | ◑ | – | – | ● plan-enforced |
| Deck-grounded Q&A | – | – | – | – | – | – | – | ● |
| Runs without cloud | – | – | – | – | – | – | – | ◑ (optional local configuration; deployed in the cloud) |
| Target user | general | general | meetings | enterprise sales | general | learners | learners | Malaysian students |

● full · ◑ partial · – absent or not advertised.

SpeechMate's own row is marked with its *implemented* status, not its design intent. The reason is so a reviewer cannot argue the table overclaims.

---

## III. System Design and Methodology

Development was design-based and iterative: Agile sprints, each delivering one capability. Every AI component was empirically checked as soon as real or realistic data existed. Decisions changed when measurements contradicted the design (routing, language token, narration). Those changes are reported here, not hidden.

### A. System Architecture

The system has three tiers.

**Capture (browser)**
- Next.js 16 / React 19 / TypeScript client.
- MediaPipe Tasks Vision (FaceLandmarker, PoseLandmarker) [71]–[73] for live face and pose tracking, used for the camera stage, lighting advice and Gaze Tunneling samples.
- An adaptive energy voice-activity detector cuts each spoken turn after about 1.6 s of silence and sends it as 16 kHz WAV for transcription.
- A MediaRecorder records the session (audio and video) for post-session analysis.

**Service (FastAPI, Python 3.12)**
- Async SQLAlchemy on PostgreSQL with Alembic migrations.
- JWT authentication (bcrypt; 30-minute access token; rotating httpOnly refresh cookie).
- Routers for live sessions, conversation (speech-to-text, AI partner, text-to-speech), decks, rehearsals and notifications.
- Analyses run as in-process background jobs. The results page polls, and a notification is sent when the job finishes.

**Models**

| Role | Cloud configuration (evaluated and deployed) | Local configuration (development; used for the ASR experiments) |
|---|---|---|
| Speech-to-text | Groq `whisper-large-v3` (OpenAI-compatible API, word timestamps) [66], [39] | Mesolitica Malaysian Whisper large-v3-turbo (faster-whisper, CPU int8) [65] |
| LLM (partner, plans, insights, feedback) | Google `gemini-3.5-flash-lite` (OpenAI-compatible endpoint) [67] | Ollama `qwen2.5:3b` [68] |
| Partner voice | Kokoro-82M [74] | Kokoro-82M |
| Pronunciation | Wav2Vec2 base-960h | same |
| Vision | MediaPipe Face Mesh / Pose, ViT expression classifier | same |
| Prosody | librosa | same |

Every model sits behind an OpenAI-compatible or local interface, so switching configurations is a matter of settings, not code changes.

**Why the cloud configuration is the evaluated one.**
- It is what users get: the deployed web application (Section V.A) needs no GPU, no multi-gigabyte download and no 8 GB of free RAM.
- It removes the latency that made a 3B local model feel slow in conversation (2–15 s per reply on CPU).
- The grounding guards of Section III.I were designed against the weaker 3B local model, so they hold with a stronger cloud model.

The local configuration remains supported (restorable from commit `6f89bed`) and is where the speech-recognition design study of Section IV was carried out, because it allows controlled, repeatable decoding on fixed weights.

**Analysis pipeline (per session)**

```
recording → 16 kHz WAV ─┬─ content feedback (LLM, in parallel)
                        ├─ speech: ASR (word timings) → fluency, fillers, disfluency → pronunciation ‖ prosody
                        └─ vision (after speech, to fit 7.6 GB RAM): frames → eye contact ‖ posture → gestures ‖ expression
 + browser metrics (response latency, Gaze Tunneling, slide timings)
 → 11-cue confidence → overall score → four pillars → coaching plan (LLM, measured candidates only)
 → progress records → notification
```

Speech and vision run one after the other because running both model sets at once exhausted the 7.6 GB development machine (Section III.J).

**Three practice functions on one pipeline**

| Function | Before the session | During | After (in addition to the four pillars) |
|---|---|---|---|
| Daily conversation | pick a topic | free conversation with the AI partner | language corrections ("you said / more natural"), conversation tips |
| Mock interview | role, level, type, background, job description, optional resume → a 6–8-question plan, previewable | the interviewer follows the plan; one follow-up if an answer is short | per answer: relevance, structure (STAR), specificity (1–5), went well, improve, fact-checked stronger answer |
| Presentation practice | deck upload → insights (summary, structure, key point per slide) → Q&A plan | present the deck on camera (user-paced slides, AI silent); then a Q&A drawn from the deck | per slide: key-point coverage, 1–5 match, what was covered or missed, time on slide; per Q&A answer as for interviews |

### B. Dual-Agent Presentation Coaching

The presentation function was designed after PresentCoach [55] as two agents.

1. **Ideal Presentation Agent [R]** (removed 2026-10-07):
   - render each slide;
   - write a 60–100-word narration per slide with a vision–language model (`qwen2.5vl:3b`, given the slide image, its text and the previous slide's script for continuity);
   - synthesise the narration with Mesolitica Malaysian-TTS-0.6B (7 voices);
   - assemble a narrated example video, as a *worked example* of the learner's own talk [32].
2. **Coach Agent [I]**: compare the learner's rehearsal against the deck and give Observation → Impact → Suggestion feedback, a simulated-audience view and a follow-up chat.

*Narration cost on CPU: a few minutes per slide.*

**Current form.**
- The **Deck Agent** reads the deck (`.pptx` via LibreOffice, `.pdf` via pdftotext / pdftoppm) and writes, with an LLM:
  - a summary, main message and structure;
  - each slide's key point;
  - text-heavy-slide suggestions;
  - likely audience questions;
  - a cached Q&A plan of 5–6 questions tied to slides.

  A rule-based fallback works from the slide text alone.
- The **Coach Agent** judges a live "talk" session:
  - the browser records when each slide went on screen;
  - the transcript's word timings are split at those moments;
  - each slide receives (a) rule-based key-word coverage of its key point (weighted double), title and text, labelled covered ≥ 40% · partly ≥ 20% · missed below, and (b) an LLM 1–5 alignment rating with "covered" (quoting the speaker), "missing" and a tip.

**Why narration was withdrawn.** The original purpose of the deck stage was *comprehension*: the AI must understand the deck's content so it can check that what the presenter says is aligned with what the deck means. A narrated example video is a by-product of that purpose, not the purpose itself. It also carried costs that worked against it:
- minutes of CPU time per slide;
- a separate text-to-speech model;
- a risk of anchoring the learner on reciting the AI's script instead of explaining the slide in their own words. This last point is the script-reading habit that Gaze Tunneling targets [5], and the expertise-reversal effect warns that a fully worked example can hinder learners who already know the material [33].

The narration was therefore removed, and the deck stage was reduced to what the alignment check needs: the summary, structure, each slide's key point, and a Q&A plan. Per-slide alignment between the deck's meaning and the speaker's words is now the core output of presentation practice.

The worked-example function now comes from:
- the per-slide key points shown before presenting;
- the "covered / left out" comparison after it;
- the fact-checked stronger answers in the Q&A.

### C. Dual-Engine ASR Routing for Code-Switched Speech

**Design.**
- A fast general model (faster-whisper) transcribes first. Its language-identification confidence doubles as a router signal.
- When the audio is "not confidently English", it is re-transcribed by Mesolitica's `wav2vec2-xls-r-300m-mixed` [23], a CTC model trained on Malay, Singlish and Mandarin-mixed speech.
- The aim was to pay the specialised model's cost only for inputs that need it.

**Outcome [E][R].** Evaluated on 400 held-out clips (Section IV.D): routing detected code-switching perfectly but more than doubled WER on mixed speech. Two further facts:
- With the shipped Malaysian Whisper, routing was skipped by design, because that model already handles mixed speech.
- In deployment, a dependency guard (torch 2.4.1 vs transformers 4.53, CVE-2025-32434) had made every routed clip *silently* fall back to Whisper (Section IV.E).

The router and the local ASR stack were removed on 2026-10-14. The code remains recoverable from commit `6f89bed` (`docs/project/local-stt-removal.md`).

**Current ASR.** One OpenAI-compatible transcription call with:
- word-level timestamps (`verbose_json`), needed for pause and stutter timing;
- automatic language detection, which keeps code-switches as spoken;
- a short verbatim Manglish prompt containing fillers: *"Umm, okay lah, so, uh, macam this week saya busy sikit, you know... but boleh la."* This encourages the model to keep fillers and mixed words rather than normalise them away.

The same settings are used for live turns, session analysis and rehearsal transcripts.

### D. Code-Switch Characterisation

The language mix is estimated with a documented lexicon: 193 common Bahasa Malaysia function words, pronouns, verbs and everyday terms, plus 14 Manglish discourse particles.

- **Method:** every token is checked against the lexicon; anything else counts as English.
- **Outputs:** the English and Malay ratios; *code-switching* when both languages are at least 15%; the particles found.
- **Uses:** the language-mix card, and the condition for the accent allowance (Section III.E).

This is a whole-transcript heuristic, not a trained language-identification model. Proper nouns, rare Malay words and mixed compounds can misclassify, and switching is not located within an utterance. It is used to *describe* a session, never to score it.

A trained token-level language identifier would allow per-switch analysis (one switch at a hard word versus alternating throughout). This is future work.

### E. Accent-Fair Pronunciation Assessment

**Implemented [I] (2026-10-16): GOP over a CTC forced alignment, with an explicit fairness rule** (`backend/app/services/live/phone_gop.py`).

1. **Expected phonemes.** Each word is phonemised by espeak-ng, a phrase at a time, so function words take their natural weak forms ("a" → /ɐ/). The British English voice is used because Malaysian English, like British English, is non-rhotic (F8); a US norm would mark every "clear" and "car" down.
2. **Acoustic evidence.** `facebook/wav2vec2-xlsr-53-espeak-cv-ft` [80], a multilingual phoneme recogniser with the same espeak phoneme inventory, gives frame-level phoneme posteriors. Audio is processed in chunks of consecutive words (≤ 12 s, split at gaps > 0.8 s) using the speech-recognition word timings, so memory stays bounded.
3. **Alignment.** torchaudio's CTC forced alignment places each expected phoneme.
4. **GOP.** For phoneme $p$ aligned to frames $T_p$:
   $$ \text{GOP}(p) = \frac{1}{|T_p|}\sum_{t \in T_p} \frac{\max_{q \in E(p)} P(q \mid o_t)}{\max_{q \ne \varnothing} P(q \mid o_t)} \in (0, 1] $$
   Here $E(p)$ is $p$ plus its *equivalent realisations*: reduced vowels for one another, r-coloured vs plain schwa, weak and strong forms of function words, and the US/UK variants of the same vowel. No variety of English is the reference, so a US accent is not marked down against British phonemes either.
5. **Deviation and classification.** A phoneme with GOP < 0.5 is a deviation. The best competing phoneme (or "dropped" when the CTC blank dominates its frames) decides the category:
   - **ok** — an unstressed vowel reduced to a schwa-like vowel (normal fluent speech);
   - **regional** — matches F1–F4, F6 or F8: th → t/d; final cluster simplified ("las'", "an'"); vowel length or quality; final stop as a glottal stop (word-final only); monophthongised diphthong; non-rhotic r. Reported to the user, and the phoneme scores at least 85;
   - **intelligibility-affecting** — anything else (e.g. /v/ → /w/). It lowers the word score and is named in the coaching: "*vest* (/v/ sounded like /w/)".
6. **Malay words are not scored.** Each chunk is aligned a second time against the words' Malay phonemisation (espeak's Malay voice). A word whose Malay form fits the audio better (by more than 0.05) is left out. Lexicon words and particles are skipped outright. Code-switching is not an error, and this scorer judges English pronunciation.
7. **Scores.** A word's score is the mean of its phoneme scores (regional phonemes credited); words under 60 are listed as unclear. The session score is the mean word score. No blanket accent allowance is added, since the rule above handles it. The old word-level CTC scorer (with its +5% allowance) remains as the fallback when word timings or the phoneme model are unavailable.

**Check on real audio (development, not validation).** Run through the deployed pipeline:

| Clip | Score | Reported |
|---|---|---|
| FLEURS US-English speaker | 95.5 | regional: "shared" (F8), "and" → "an'" (F2); unclear: one vowel in "culture" |
| Malaysian-voice English ("The supervisor asked me to explain the method…") | 79.0 | regional: "the" → [də] ×2 and "method" → [mɛtəd] (F1), vowel length ×2 (F3); unclear: /p/ in "supervisor", final /k/ in "asked" |

**Development iterations, a native-norm bias found and removed.** The first version (US-English citation forms, no equivalents) scored the US-English speaker 73. It flagged correct speech: weak forms ("a" as /ɐ/), non-rhotic vowels ("clear"), reduced unstressed vowels ("singular"). Phrase-level phonemisation, the British voice, equivalent realisations and the unstressed-vowel rule raised the clean speakers to 95–98 without hiding real deviations.

**Thresholds** (0.5 deviation, 60 unclear word, 85 regional credit, 0.05 Malay margin) are reasoned, not calibrated. Validity rests on the pre-registered correlation with human ratings (r ≥ 0.7, Section IV.C), and on checking per-category agreement: do raters also hear the flagged sounds as unclear?

**Cost.** About 1.3 GB model, loaded once; about 0.4 s per 5–10 s of speech on CPU after loading. The backend's resident memory with the model loaded was about 1.0 GiB.

### F. Multimodal Fusion

**Speech measures** (word timings from ASR; ffmpeg silence detection as a fallback):
- **Pace:** words per minute.
- **Fluency:** $100 - 0.5\,|\text{wpm} - 135| - \min(2 \cdot \text{pauses}, 30)$.
- **Pauses:** gaps of 0.25 s or more.
- **Disfluency:**
  - repetition: the same word twice within 0.6 s;
  - block: a mid-utterance silence of 1.2–3 s;
  - prolongation: a steady-energy voiced segment of at least 0.35 s;
  - gaps of 3 s or more are turn changes and count neither as pauses nor as blocks.
- **Fillers, counted in context:**
  - hesitations (*um, uh, err*) always count;
  - discourse markers (*like, you know, actually, macam, sebenarnya*) count only at a clause start or next to a comma;
  - particles and conjunctions (*lah*, *tapi*) never count.
- **Vocabulary richness:** MATTR over 50-word windows [56].
- **Hedging:** hedges per 100 words.
- **Prosody:** pitch variation in semitones from YIN [57]; loudness and steadiness in dBFS.

**Vision measures** (60 evenly sampled frames):
- **Eye contact:** MediaPipe Face Mesh iris position relative to the eye corners classifies each frame as camera (horizontal ratio 0.35–0.65), left, right or down (vertical ratio above 0.62). The score is the percentage of frames classed as camera.
- **Posture:** head tilt, shoulder level and torso stability from Pose.
- **Gestures and head steadiness:** from wrist and nose movement relative to the shoulders.
- **Expression:** a ViT [75] classifier trained on FER2013-style data [76] on MediaPipe face crops, giving an emotion distribution and tension (the fearful + angry + sad share).

**Perceived confidence (11 cues)** (`backend/docs/confidence-model.md`). Confidence is an inner state, so the model scores *perceived* confidence from cues listeners react to:

| Channel | Cue (weight) |
|---|---|
| Voice | pace (0.10), hesitation pauses per minute (0.12), repetitions per minute (0.08), blocks and prolongations per minute (0.07), fillers per minute (0.08), time to start answering (0.05) |
| Face | confident expression (0.10), relaxed face (0.08) |
| Body | upright posture (0.11), steady body (0.07), eye contact (0.14) |

How the score is formed:
- Each cue maps to 0–100 by a stated rule. The score is the weighted mean over the cues *actually measured*.
- Coverage is reported, and **no score is given under 30% coverage**.
- Rates are per minute of the user's own talking time. An earlier count-based version made longer sessions look less confident.
- Face cues carry only 18% of the weight, because expression classifiers are trained mostly on posed, non-Malaysian faces.
- The weights are a reasoned starting point and are **not fitted to data**. A validation study with Spearman ρ ≥ 0.5 against blind raters is pre-registered (Section IV.C).

**Overall score and pillars.**
- **Overall:** $0.25\,\text{fluency} + 0.25\,\text{pronunciation} + 0.20\,\text{confidence} + 0.15\,\text{eye contact} + 0.15\,\text{posture}$, renormalised over the components measured.
- **Pillars:** each metric maps to 0–100 against a stated comfortable range (for example, pace 120–160 wpm with −2.5 per wpm outside). Metrics are grouped into four pillars (Voice & delivery, Language & clarity, Body language, Confidence & presence). Each pillar is the mean of its measured metrics; status is Strong ≥ 75, Okay ≥ 55, otherwise Work on this.

**Content measures** (the LLM, constrained as described in Section III.I):
- **Interview / Q&A:** each answer is paired with its planned question and rated 1–5 for relevance, structure (STAR, or answer-first for Q&A) and specificity. The output includes what went well, one improvement and a stronger answer built only from the speaker's facts.
- **Conversation:** up to five corrections; Malaysian English expressions are not treated as errors.
- **Presentation:** per-slide alignment, as described in Section III.B.

### G. The Gaze Tunneling Metric

**Data (computed on the server after the session).** Both series come from the session recording, on one timeline (the recorder pauses audio and video together during the AI's turns):
- **Gaze:** the video is streamed at about 2 frames per second. Each frame with a face is classified by MediaPipe iris position as *at the camera* or *away* (the same rule as the eye-contact score). Frames are mapped to seconds by their position in the stream, scaled to the audio's length.
- **Disfluencies:** hesitations (*um, uh, err…*) located by the speech-recognition word timestamps, plus the repetitions, blocks and prolongations from the disfluency detector, each at its own start time.

**Definition.** Divide the session into windows of $w = 5$ s. For window $k$:
- $x_k$ is the share of gaze samples in the window that are *away*; a window with no face takes the session mean;
- $y_k$ is the number of disfluency events in the window.

Gaze Tunneling is the Pearson correlation

$$ r = \frac{\sum_k (x_k-\bar{x})(y_k-\bar{y})}{\sqrt{\sum_k (x_k-\bar{x})^2 \sum_k (y_k-\bar{y})^2}} $$

**Significance (circular-shift permutation test).** $r$ is recomputed with $y$ rotated against $x$ by every offset $1 \ldots n-1$. This keeps each series' own clustering (adjacent windows are autocorrelated, and $y$ is sparse), which a plain t-test on $r$ ignores. The p-value is

$$ p = \frac{1 + \#\{k : r_k \ge r\}}{n} . $$

Because the smallest attainable $p$ is $1/n$, the metric is computed only with at least 20 windows (100 s of the user's speech) and at least 3 disfluencies, and when a face was seen in at least half the windows. Otherwise it is left out, not estimated.

**Labels and scoring:**
- *strong link*: $r > 0.4$ and $p < 0.05$;
- *some link*: $r > 0.15$ and $p < 0.05$;
- otherwise *no clear link*.

It enters the Confidence & presence pillar as $100 - 100\max(r, 0)$ only when $p < 0.05$. A chance-level correlation costs nothing.

**Interpretation.** The metric asks *whether looking away and stumbling coincide*, supporting feedback such as "you tend to look away exactly when you lose your words". It does not imply direction. Gaze aversion can be a strategy for managing cognitive load [35], [38], so a link is shown as a pattern to notice, not a fault.

**Revision history (worth reporting, Section IV.E, S9).** The first implementation ran in the browser:
- it stamped each disfluency when its *transcript arrived*, after the 1.6 s end-of-turn silence and transcription latency, with every event in a turn sharing one timestamp;
- it used a head-orientation heuristic for gaze;
- it labelled any $r > 0.15$ as a link without a significance test.

At 5 s windows these lags misplaced events by one or more windows. On a 1-minute session the critical $r$ at the two-sided 5% level is about 0.58, so most "links" it reported were chance. It was replaced by the server-side computation above (2026-10-15).

**Limits.** A webcam recovers head and eye orientation, not the true point of regard. The tri-zone (audience / left / slide) treatment of [18] is not implemented; the system distinguishes camera, left, right and down **[D]**. Gaze classification accuracy against manually coded video is still to be measured (Section IV.C). The streaming reader has been checked on a WebM recording (no hang; 20 s of video in 1.3 s), but **not yet on recordings of real faces**.

### H. Deferred Feedback and Learner Data Handling

**Deferred feedback [I].** During a session the screen shows only:
- the timer;
- the turn state (listening, thinking, speaking);
- the question count;
- lighting and contrast advice (camera set-up, not performance).

Live score bars were removed. The AI partner never replies while the user is speaking or while their words are still being transcribed.

All performance feedback appears on the results page after the session:
1. an overall summary;
2. four pillars, tappable for each metric, its value and its comfortable range;
3. content feedback;
4. three drills.

The deferral premise (that for anxious speakers on open tasks the load of mid-speech alerts outweighs immediate correction) is argued from theory (Sections II.A–B) and **untested**. A within-subject comparison is pre-registered (Section IV.C).

**Learner data handling.** Voice, face video, resumes and goals are personal data under Malaysia's PDPA 2010 [77]. The table maps its seven principles to the current controls (`docs/project/Security.md`).

| PDPA principle | Current control | Gap |
|---|---|---|
| General / purpose | data used only for the user's own feedback | — |
| Notice and choice | **consent screen** before any cloud processing (what goes to Groq, what to Gemini, what stays on the server); consent time stored per user; withdrawable in Settings. The server refuses live sessions, analyses, interview plans, deck uploads, live-turn transcription and the AI partner without it (403 `cloud_consent_required`); none of them can be called without an account | consent covers both providers together |
| Disclosure | **current deployment sends audio (Groq) and transcripts, resume and deck text (Gemini) to cloud APIs**; the local configuration sends nothing | must be disclosed in-app and in the paper |
| Security | bcrypt; rotating httpOnly refresh token; owner checks on every session, result, deck and slide image (slides are fetched with the token, not public URLs; tested); history lists return summaries without transcripts or resume text; rate limits; upload caps; JSON-validated LLM output | access token in localStorage; in-memory rate limits |
| Retention | **raw recordings deleted as soon as their analysis succeeds** (files removed only after results are committed), unless the user opts to keep them; resume text kept only inside its session; deleting a session removes everything; the old upload-a-rehearsal feature and its tables were removed (migration 0008) | — |
| Data integrity | measured values only; "unavailable" when not measured | — |
| Access and erasure | users see all their sessions and results; **download all their data** as one JSON file; **delete the account** (password re-entered), which removes every row and file | — |

Implemented 2026-10-16 (`routers/auth.py`, `components/layout/ConsentGate.tsx`, Settings → Privacy & your data); tested in `backend/tests/test_privacy.py`. V1's "short, configurable review window" can now be stated as: *recordings are deleted as soon as their analysis completes, unless the user chooses to keep them.*

### I. Graceful Degradation and Measurement Honesty

**Rule.** No number is shown that was not measured. Each stage has a defined fallback, and every fallback is recorded in the session's notes.

| Stage | Without its model or key | Shown to user |
|---|---|---|
| ASR | no transcript; pauses and blocks still measured from audio (ffmpeg); typed input during sessions | "not measured" for word metrics |
| Pronunciation, expression, eye contact, posture, prosody | skipped | "not measured" with the reason |
| Confidence | needs at least 30% of cue weight | no score below that |
| Overall / pillars | renormalised over measured parts; a pillar with no metrics shows "—" | the components listed |
| LLM plans | question bank; deck likely questions and key points | labelled "standard question bank" |
| Interviewer turns | plan still enforced, fixed reactions | — |
| Answer feedback | rule-based (STAR cue words, numbers, length, overlap with the question) | labelled rule-based |
| Partner voice | backend TTS, then the browser voice | — |

**LLM grounding (G5).**
1. **Plans.** JSON is validated against a schema and re-prompted once. Category labels and placeholders are stripped. Question 1 is spoken verbatim after the greeting.
2. **Turn control.** The server, not the model, chooses the next question. The model writes only a one-sentence reaction, so a 3B model cannot skip or invent questions. An answer under 25 words gets exactly one follow-up.
3. **Recommendations.** Candidates are built from measured issues (with evidence, drill and a target relative to the user's value). The LLM may only select and phrase them; it cannot add an issue.
4. **Fact check.** In a stronger answer, any capitalised name or any number not found in that answer, its question, or the user's resume or background triggers a re-prompt naming the invented terms. If it persists, the rewrite is replaced by a structure hint. Observed fabrications that the check caught: "Tableau", "Maybank" (the target company, not the speaker's employer).
5. **Explainability.** Every score's method, range and a worked example are on the in-app reference page. The confidence result lists its cues, weakest first.

### J. Computational Cost and Implementation Status

**Reference machine:** CPU-only, WSL 2 with 7.6 GB RAM. Training used an RTX 4060 Laptop GPU (8 GB).

| Item | Cost | Source |
|---|---|---|
| Local ASR (Mesolitica turbo, int8, 8 threads) | 2.27 s per 5 s turn (RTF ≈ 0.45); +653 MB RAM | benchmark 2026-09-30 |
| ASR threads | 4 → 8 threads: 21% faster, identical WER; above 12 threads it gets slower | same |
| Beam 5 vs 1 | WER 7.9% vs 8.3%; little speed difference (4-layer decoder; the encoder dominates) | same |
| Shared verbatim prompt | +0.19 s per turn; WER 6.1% → 6.5% on a filler-free set | benchmark 2026-10-02 |
| Local LLM (qwen2.5:3b, CPU) | interview plan 30–60 s; deck insights about 35 s; Q&A plan about 25 s; reply 2–15 s | measured during development |
| Session analysis | about 80–115 s for a 23 s test recording; about 1–2 min for a few minutes of talk | end-to-end runs, Architecture.md |
| Memory | speech and vision models run one after the other (in parallel they exceeded 7.6 GB) | Architecture.md |
| Docker image with local ML | about 4.7 GB | deploy notes |
| LoRA fine-tune | 82 min, 2.20 GiB peak VRAM, 648 steps, 10.3 h audio | fine-tune/docs/RESULTS.md |
| Cloud ASR (Groq whisper-large-v3) | median 0.56 s per turn (p90 1.30 s, p95 6.66 s, n = 500); 3.2 s for a 189 s recording; about $0.014 per 5-min conversation, $0.030 per 10-min interview | benchmark 2026-10-15 |
| Cloud LLM (Gemini 3.5 Flash-Lite) | every session now logs its calls and tokens, priced at the paid-tier list rate (US$0.30 / 2.50 per million input / output tokens [81]); first logged session (96 s Q&A): 1 call, 956 + 477 tokens, **US$0.0015**; US$0 on the free tier; latency not yet measured | `details.usage.llm` |

**Implementation status**

| Component | Status |
|---|---|
| Three practice functions, live sessions, deferred results, progress | [I] |
| ASR model selection, language token, prompt | [E] |
| Dual-engine routing | [E][R] removed 2026-10-14 |
| Cloud ASR (Groq Whisper large-v3) | [E] 2026-10-15; silence guard and FLAC upload added (S11, S12 fixed) |
| Local ASR stack | [R] 2026-10-14 (restorable) |
| LoRA fine-tune | [E] on synthetic and near-domain data; not deployed |
| Pronunciation: phone-level GOP with regional/intelligibility split | [I] 2026-10-16 (word-level CTC fallback); human validation pending |
| Privacy: consent gate, retention, export, erasure | [I] 2026-10-16; sign-in + consent on every cloud endpoint, private slide images [I] 2026-10-16 |
| Unused features' data (narration columns, upload coach, duplicated progress rows, reports) | [R] 2026-10-20 (migration 0008, reversible) |
| Real-speaker evaluation tooling (`run_app_on_clips.py`, `study_stats.py`) | [I], self-tested; awaiting data |
| Disfluency (rule-based heuristic) | [I]; CNN-BiLSTM classifier [D] |
| Eye contact, posture, gestures, expression | [I] |
| 11-cue confidence, pillars, overall score | [I] |
| Gaze Tunneling | [I] server-side with permutation test (S9 fixed); not yet run on real face recordings |
| Grounded feedback guards | [I]; unit-tested |
| Ideal Presentation Agent (narrated example) | [R] 2026-10-07 |
| Deck Agent and talk Coach Agent | [I] |
| Automated tests | 63 backend tests (`backend/tests/`, tests of removed code removed with it); frontend type-check and lint; voice-turn self-test |

---

## IV. Evaluation

### A. Datasets and What They Can Support

| Dataset | Size | Real or synthetic | Licence | Used for |
|---|---|---|---|---|
| FLEURS `ms_my` test [58] | 25 utterances | real speakers, read Malay | CC BY 4.0 | ASR model selection, language token |
| Malaysian-TTS clips | 4 Malaysian English + 4 Manglish | synthetic (3 voices) | own generation | same (indicative only) |
| Kokoro clips | 6 US/UK English | synthetic | own generation | translation-failure check |
| eval/paper: FLEURS `en_us` test | 200 | real speakers, read US English | CC BY 4.0 | routing; fine-tune |
| eval/paper: FLEURS `ms_my` test | 100 | real speakers, read Malay | CC BY 4.0 | cloud ASR (Experiment 8) |
| eval/paper: Synth-Manglish held-out [59] | 200 | synthetic, 3 voices never trained on | CC BY 4.0 | routing; fine-tune |
| Fine-tune training set | 3,451 clips, 10.3 h | Synth-Manglish 2,118 + FLEURS ms/en 900 + 301 noisy copies + 132 silent | CC BY 4.0 | training only |
| Silence and noise | 10 clips | generated | — | hallucination safety |

**What these data can and cannot support**

| Claim | Supported? | Why |
|---|---|---|
| Model A transcribes read Malay better than model B | **Yes**, for read speech | real speakers, human transcripts |
| A model keeps English as English (no translation) | **Yes, as a failure check** | a single counter-example is decisive |
| Routing hurts mixed-speech WER | **Yes, for synthetic Manglish**; direction very unlikely to reverse (p ≈ 2×10⁻⁵⁷, 196 of 200 clips worse) | engine-level error, not voice-specific |
| The fine-tune is better on real Malaysian Manglish | **No** | mixed test voices come from the same TTS system and style as training (in-domain) |
| The fine-tune is better on English | **Weakly**, near-domain | FLEURS en_us *train* was in the training mix; sign test p = 0.056 |
| WER on spontaneous, noisy, real Malaysian conversation | **No** | no such data yet |
| Filler retention / filler F1 | **No** | test sets contain no fillers |
| Pronunciation, gaze, posture, expression, confidence validity | **No** | no human ratings yet |
| The deployed cloud ASR's accuracy | **Yes, for read English, read Malay and synthetic Manglish** | measured directly on the same held-out clips (Experiment 8); still no real conversational Manglish |

### B. How Accurate Must the Router Be?

Let speech groups $g \in \{E, M\}$ (English-only, mixed) occur with proportions $\pi_g$. Engines $A$ (general) and $B$ (specialised) have WERs $W_{A,g}$ and $W_{B,g}$, with $\Delta_g = W_{B,g} - W_{A,g}$. The router sends group $g$ to $B$ with probability $q_g$, so $q_M$ is the true-positive rate and $q_E$ the false-positive rate. Then

$$ \mathbb{E}[\text{WER}_{\text{routed}}] - \mathbb{E}[\text{WER}_A] = \pi_M\, q_M\, \Delta_M + \pi_E\, q_E\, \Delta_E . $$

Routing helps only if this is negative. Two consequences follow.

1. **If $\Delta_M \ge 0$, no router helps.** With the specialised engine no better on its own target, any routing adds error. Measured $\Delta_M = +21.3$ points [95% CI +19.9, +22.7] (Table IV-3). The router's detection was perfect on this set ($q_M = 200/200$, $q_E = 0/200$; mean language confidence 0.99 on English and 0.96 on mixed). **The binding constraint was the engine, not the router.**
2. **For a future engine with $\Delta_M = -d_M < 0$ and $\Delta_E = +d_E > 0$**, routing helps iff

   $$ q_E < q_M \cdot \frac{\pi_M\, d_M}{\pi_E\, d_E} . $$

   *Example:* if a new engine were 5 points better on mixed speech and 20 points worse on English, with half the sessions mixed, the router's false-positive rate must stay below one quarter of its true-positive rate.

   Note that per-recording routing applies one engine to a whole session that may switch at only a few words. A segment-level router would change $\pi$ and the $\Delta$s.

**Acceptance rule (pre-registered for any future router):** report $\Delta_M$ and $\Delta_E$ with confidence intervals on held-out data first. Deploy only if the inequality holds at the upper confidence bound.

### C. Baselines and Metrics

| Component | Baseline | Metric | Pre-registered acceptance | Sample-size reasoning |
|---|---|---|---|---|
| ASR | Whisper medium (previous setting); then the shipped model | WER by group; translation incidents; silent-clip output | measurable WER reduction vs baseline; zero translation; zero text on silence | per-clip bootstrap CIs and a paired sign test [60], [61] |
| Fine-tune go/no-go | shipped Mesolitica turbo | as above + latency + per-speaker gains | better by a pre-set margin; no regression in silence, noise, English or language preservation; gains across speakers | needs real speakers (30–50 clips) |
| Pronunciation | — | Pearson / Spearman r with 2–3 human raters; inter-rater ICC [62] | r ≥ 0.7 | with n = 30 and r = 0.7, the 95% CI is about [0.45, 0.85]; plan n ≥ 30 |
| Disfluency / fillers | — | precision, recall, F1; false-positive rate on natural pauses | F1 ≥ 0.75 | annotate ≥ 300 events; Cohen's κ between annotators [79] |
| Eye contact | — | accuracy vs frame-level manual coding | ≥ 0.80 | ≥ 1,000 coded frames from ≥ 15 speakers |
| Perceived confidence | — | Spearman ρ vs mean of blind 1–7 ratings | ρ ≥ 0.5 | ρ = 0.5 at α = .05 with power .8 needs n ≈ 29 |
| Overall score | — | correlation with a supervisor rating | r ≥ 0.6 | n ≥ 30 |
| Feedback quality | generic LLM advice (no grounding) | Likert: specific, actionable, accurate | mean ≥ 4/5 and better than baseline | within-subject; d = 0.5 needs n ≈ 34 |
| Deferral premise | real-time alerts (same app, alerts on) | performance + self-reported anxiety (e.g. FLCAS items [30]) | lower anxiety, performance not worse | within-subject, counterbalanced, n ≈ 34 |

### D. Procedure and Results

All ASR runs use the app's own decoding settings: VAD filter, `condition_on_previous_text=False`, beam 5. WER is computed after lower-casing and stripping punctuation (`[a-z0-9']+` tokens).

**Experiment 1: model selection** (33 utterances; `docs/benchmarks/stt-benchmark-2026-09-30.md`)

| Model | Language token | Malay (real) | MY English | Manglish | All | s per 5 s turn |
|---|---|---|---|---|---|---|
| Whisper medium (previous) | en | 59.5% | 6.0% | 17.0% | 51.3% | 2.20 |
| Whisper medium | ms | 12.1% | 50.0% | 14.9% | 15.6% | 2.41 |
| Mesolitica small-v3 | ms | 9.5% | 90.0% | 34.0% | 18.6% | 0.90 |
| **Mesolitica large-v3-turbo-v3** | ms | **7.4%** | **4.0%** | 17.0% | **7.9%** | 2.77 |

Standard Whisper cannot serve both languages with one language token: it *translates* Malay into English under `en` and English into Malay under `ms`. The headline gap (51.3% → 7.9%) is dominated by translation failures on the 25 real Malay utterances. It is large enough that its direction is not in doubt, but the English and Manglish columns (4 clips each) are indicative only.

**Experiment 2: language token** (39 utterances; `docs/benchmarks/stt-benchmark-2026-10-01.md`). Forcing `ms` with no English prompt made the Malaysian model translate a US-English answer into Malay. Auto-detection fixed this and improved accuracy:

| Setting | Malay | MY English | Manglish | US/UK English | All |
|---|---|---|---|---|---|
| forced `ms` | 7.4% | 4.0% | 17.0% | 0.0% | 6.8% |
| auto-detect | 6.4% | 4.0% | 17.0% | 0.0% | 6.1% |

**Experiment 3: verbatim prompt** (`docs/benchmarks/stt-benchmark-2026-10-02.md`). The shared filler-bearing prompt moved overall WER from 6.1% to 6.5%, about one word across 4 synthetic Manglish clips, mostly spelling ("okay" → "okey", "kenyang lah" → "kenyanglah"). It was chosen for filler retention, which this test set cannot measure.

**Experiment 4: routing** (400 held-out clips; `fine-tune/eval/paper/results.csv`; statistics from `fine-tune/scripts/paper_stats.py`; 5,000 bootstrap draws)

| Group | Routing off | Routing on | Difference [95% CI] | Clips better / worse / same | Sign test |
|---|---|---|---|---|---|
| English (200, real) | 5.3% [4.4, 6.2] | 5.3% | 0 (never triggered) | 0 / 0 / 200 | — |
| Mixed (200, synthetic) | 15.4% [14.0, 17.0] | 36.7% [34.8, 38.6] | **+21.3 pts [+19.9, +22.7]** | 1 / 196 / 3 | p ≈ 2×10⁻⁵⁷ |

Typical error from the code-switch model: "…challenge arwah Sudirman kot, energi dia…" became "…challen arwasudirman kod energy dia…". CTC without a strong language model fragments and merges words.

**Experiment 5: LoRA fine-tune** (same 400 clips; `finetune_results.csv`)

- Base: Mesolitica turbo-v3 [65], adapted with LoRA [70].
- Settings: LoRA r = 32, lr = 1e-4, bf16, effective batch 16, 3 epochs, timestamp mode, best epoch kept.
- Data: 10.3 h public.

| Group | Shipped | Fine-tune | Difference [95% CI] | Clips better / worse / same | Sign test |
|---|---|---|---|---|---|
| English (real, near-domain) | 9.4% [7.2, 12.0] | 6.7% [5.7, 7.8] | −2.8 pts [−5.2, −0.8] | 39 / 23 / 138 | p = 0.056 |
| Mixed (synthetic, in-domain) | 14.5% [13.1, 16.0] | 6.7% [5.8, 7.7] | −7.8 pts [−8.9, −6.8] | 154 / 9 / 37 | p ≈ 3×10⁻³⁵ |

- The prompt changes the fine-tune's WER by only +0.1 to +0.3 points.
- Plain Whisper large-v3 (5.3% English, 15.4% mixed) beats both Malaysian models on US English but is worse than both on mixed speech. This is consistent with Malaysian adaptation trading some native-English accuracy for Manglish coverage.

The fine-tune is **not deployed**. The go/no-go criteria (`fine-tune/docs/manglish-finetune-plan.md` §11) require real Malaysian speakers.

**Experiment 6: silence safety.** 10 silent or noise-only clips (8 s of silence, 8 s of white noise, and dev silent clips).
- **Local models** (app settings with VAD): 0 of 10 produced any text, for both the shipped model and the fine-tune.
- **Deployed cloud service** (no VAD in front): **8 of 10 produced text**, for example "Subtitles by the Amara.org community" (4 clips), "Okay." (2), "you", and a 9-word sentence on white noise. This is a known Whisper failure mode [42]. The local VAD had been masking it.

**Experiment 7: end-to-end function.**
- **Procedure:** synthetic spoken interview answers (Kokoro) were uploaded as a session and analysed by the full pipeline with real models.
- **Result:** analysis completed in 82–114 s. All four pillars were populated where signals existed (Body language was correctly "not measured" for audio-only input). Per-answer LLM feedback was produced, and the fact check replaced an invented stronger answer.
- **Automated tests:** 65 backend test functions cover every metric with worked numbers, the plan-following partner, the fact check, ownership (another user's id returns 404), silence and the analysis API end to end.
- **What this supports:** functional correctness only. It is not evidence of validity.

**Experiment 8: deployed cloud ASR** (`docs/benchmarks/stt-groq-cloud-2026-10-15.md`; `fine-tune/eval/paper/groq_results.csv`).

- **Setup:** Groq `whisper-large-v3` with the app's exact request (verbose JSON, word timestamps, verbatim prompt, automatic language) on the same 400 held-out clips, plus 100 real Malay clips (FLEURS ms_my test).
- **Free tier:** the whole run used Groq's free tier (511 requests, 94 billed minutes; at list price it would cost US$0.17).

| Group | Groq (deployed) | Same weights, local | Shipped Malaysian model | Groq − local [95% CI] | Groq − shipped [95% CI] |
|---|---|---|---|---|---|
| English (200, real) | **4.9%** [4.1, 5.8] | 5.3% | 9.4% | −0.4 [−1.1, +0.2], p = 0.75 | **−4.6 [−7.2, −2.4], p = 8×10⁻⁹** |
| Mixed (200, synthetic) | **16.5%** [14.7, 18.4] | 15.4% | 14.5% | +1.0 [−0.1, +2.5], p = 0.72 | **+2.0 [+0.7, +3.5], p = 0.003** |
| Malay (100, real) | **7.3%** | — | — | — | — |

- **Cloud vs local:** the cloud service is statistically indistinguishable from the same weights run locally, so the local design study transfers to the deployed system.
- **Trade-off made by moving to cloud:**
  - **better on English** than the previously shipped Malaysian model (−4.6 points);
  - **slightly worse on Manglish** (+2.0 points; 86 clips worse, 50 better);
  - no clip was translated;
  - detected language: English 200/200; mixed: Malay 194, English 6; Malay: Malay 92, Indonesian 8.
- **Word timestamps:** returned for every clip with text.
- **Latency:** median **0.56 s** per request (p90 1.30 s, p95 6.66 s, max 8.51 s), against 2.3–2.7 s for the local model on CPU. A 189 s recording, the size of a typical analysis upload, took 3.2 s.

**Cost per session.** The service bills US$0.111 per audio hour with a 10 s minimum per request. A session sends every spoken phrase as a live turn, plus the user's own speech once for analysis:

$$ 	ext{cost} = rac{\$0.111}{3600}\Big(\sum_{	ext{phrases}} \max(10\,	ext{s}, d_i) + T_{	ext{user}}\Big) $$

Assuming phrases of about 5 s:
- a 5-minute conversation (2.5 min of user speech, 31 requests) bills 450 s, **about US$0.014**;
- a 10-minute mock interview bills 960 s, **about US$0.030**.

The free tier (2,000 requests and 28,800 audio-seconds per day) therefore covers about 64 conversations or 30 interviews per day.

Because short phrases are billed as 10 s, live turns cost more than the analysis. Sending whole turns would roughly halve the cost.

**Not yet run:** every human-rated study in Table IV-C, and Gemini latency. Gemini cost is now logged per session (Section III.J) but rests on one session so far.

### E. Defects Found in Early Training (and During Evaluation)

These are reported because each would otherwise have produced a wrong conclusion that looked plausible.

**Fine-tuning** (`fine-tune/docs/RESULTS.md`)

| # | Symptom | Cause | Fix / lesson |
|---|---|---|---|
| T1 | Mesolitica base scored 52.7% before training; output looped ("5.5.5…") although the words were right | evaluated in no-timestamp mode; this model never emits end-of-text without timestamp tokens | train and evaluate in timestamp mode (matches how faster-whisper decodes). Afterwards: 12.6% → 11.2% |
| T2 | Smoke runs (204 clips) peaked at step 100 and got worse by step 200 | overfitting about 15 epochs on 204 clips | full run on 10.3 h, best epoch kept (epoch 2 of 3) |
| T3 | Vanilla turbo got *worse* with LoRA (13.0% → 14.3%) while Mesolitica improved (12.6% → 11.2%) | strong base, little data | fine-tune the Malaysian base; the difference is 1–3 words on 42 clips, a hint, not proof |
| T4 | 4 near-silent clips did not stop silence hallucination | too few negatives | 132 silent + 301 noisy clips; VAD kept on; 0/10 silent outputs after |
| T5 | Dev WER 19.5% → 4.1%, much better than held-out (14.5% → 6.7%) | dev voices share the TTS system, sentence style and particle spellings with training | report only held-out voices; treat even those as in-domain |
| T6 | Correct transcriptions counted as errors ("lah" vs "la", "weh" vs "wei"; "3" vs "tiga") | style-guide spelling normalisation in training labels vs raw corpus references | orthography-aware scoring (map variants) for Manglish; report both raw and normalised WER |
| T7 | No Mesolitica dataset could be used | licences not stated; one CC BY source's download link was dead | licence register before training; only CC BY data used |

**System, found during evaluation**

| # | Symptom | Cause | Fix |
|---|---|---|---|
| S1 | Routing "worked" but never changed a transcript | torch 2.4.1 cannot load the code-switch `.bin` checkpoint under transformers 4.53 (CVE-2025-32434 guard); the exception was caught and Whisper's text returned | torch 2.6. **Lesson:** log and assert the engine actually used; the per-clip `engine_used` column exposed it |
| S2 | US-English answer transcribed in Malay | forced `ms` token | auto language detection (Experiment 2) |
| S3 | Crash on a fully silent clip | faster-whisper 1.0.3 language detection on empty audio (`max()` of an empty list) | empty transcript for silent audio |
| S4 | Filler rate 7.8/min on fluent speech | lexicon counted "I *like* data", *tapi* (= "but"), *lah* | context rules (Section III.F); particles never fillers |
| S5 | Stronger answer added "Tableau", "interned at Maybank" | LLM fabrication | fact check (Section III.I) |
| S6 | Interview intro read "Hi [Candidate]", skipped planned Q1, questions ended "(Mixed)" | 3B model drift | intro composed in code; labels stripped; server-chosen questions |
| S7 | 171 wpm scored "Strong" although outside 120–160 | pace slope too shallow (−1.5 per wpm) | −2.5 per wpm |
| S8 | Longer sessions looked less confident | counts instead of per-minute rates; AI turns counted as pauses | per-minute rates; gaps ≥ 3 s excluded |
| S9 | Gaze Tunneling events misaligned by seconds; "links" reported at chance level | events stamped on transcript arrival in the browser; no significance test (Section III.G) | computed on the server from word timestamps and a 2 fps iris-gaze stream, with a circular-shift permutation test; needs ≥ 100 s of speech (2026-10-15) |
| S10 | Deck endpoints reachable by another user | missing owner check | owner check + test (2026-10-07) |
| S11 | Cloud ASR returned "Subtitles by the Amara.org community", "Okay." or "you" for silent or noise-only audio (8/10 clips) | the local VAD and hallucination filter were removed with the local stack; Whisper hallucinates on non-speech [36], [42]; only an energy gate (≥ 0.35 s above the noise floor) remains in front of live turns fixed (2026-10-15): segments dropped when Whisper's no-speech probability is ≥ 0.4, or ≥ 0.2 and the text is a stock phrase or ≤ 2 words; subtitle credits always dropped. Calibrated on Groq's scores (silence 0.24–0.72, speech 0.001–0.097): removes 10/10 silent outputs, keeps 10/10 speech clips including a genuine "Okay."; applied to live turns, analysis and rehearsals; the analysis also drops the dropped segments' word timings |
| S12 | Recordings with more than about 13 min of user speech would get no transcript | the analysis uploads 16 kHz 16-bit WAV (32 kB/s); Groq's direct-upload limit is 25 MB | fixed (2026-10-15): uploads are lossless FLAC, measured at 35% of the WAV size (2.1 vs 6.0 MB for 3 min), raising the limit to about 37 min of speech; applied to the analysis and to rehearsals |
| S13 | A clear 5.8 s English clip rejected as "No speech was detected" | the silence threshold was absolute (−35 dBFS); this recording peaks at −44 dB, as a quiet or distant microphone can | fixed (2026-10-16): threshold relative to the recording's own peak (−35 dB for a normal −3 dB peak, lowered by the same amount for quieter ones, floored at −80 dB, not applied below a −60 dB peak); regression test |
| S14 | The deployed ASR returned a Malay *translation* of Malaysian-accented English ("My final year project helps…" → "Projek tahun akhir saya membantu…", 100% WER) in 1 of 4 Malaysian-voice clips, and "I" → "saya" in a mixed clip | auto language detection labels Malaysian-accented English as Malay; the local Malaysian model had 4.0% WER on the same clips | mitigated (2026-10-16): the phone-level scorer detects that the transcript's sounds don't match the audio (score < 40 over ≥ 5 words); the recording is then re-transcribed once with English forced, and the transcript that fits the audio better is kept (recovered "My final year project helped students practice public speaking…"). Remaining risk: partial translations of single words are not caught |

---

## V. Discussion and Limitations

### A. Cost and Accessibility

| | Local configuration | Cloud configuration (current deployment) |
|---|---|---|
| Hardware | a laptop with about 8 GB RAM (16 GB recommended for a 7B LLM); no GPU required | any device with a browser |
| Per-use cost | none after setup | ASR about US$0.014 per 5-min conversation and US$0.030 per 10-min interview (free tier: about 64 conversations a day); LLM about US$0.0015 per session at list price on the one logged session, US$0 on the free tier [81] |
| Privacy | nothing leaves the machine | audio and text sent to third parties |
| Latency | 2–3 s per turn for ASR; LLM 2–15 s on CPU | ASR median 0.56 s per turn (p95 6.7 s); LLM not yet measured |
| Model drift | pinned weights | provider may change model versions |

**The evaluated system is the cloud configuration.** It lowers the barrier to access the most: a student needs only a browser and a webcam, which matters for the target population, who often practise on modest laptops. The trade-offs that must be stated in the paper:
- **Cost:** per-use API charges replace the hardware requirement. Transcription costs about US$0.014 per 5-minute session and is covered by the provider's free tier at student scale (Experiment 8). Gemini token cost per session still needs measuring from the provider dashboard.
- **Privacy:** audio and text leave the user's machine, so cloud processing needs an explicit consent notice (Section III.H).
- **Dependency:** the service depends on network access and on providers that may change models without notice. Log the model id and date of every evaluation run.
- **Accuracy evidence:** the ASR design study was run locally on fixed weights. The deployed engine was then measured on the same clips and matched the same weights run locally (Experiment 8). Moving to cloud gained English accuracy and lost about 2 points on Manglish compared with the previously shipped Malaysian model.

Commercial coaches are also subscription-priced and cloud-only. SpeechMate keeps a local configuration as an option for privacy-sensitive users or institutions, at the price of a one-time multi-gigabyte download and slower responses. The fine-tune was trained on a consumer laptop GPU in 82 minutes, so local adaptation is within reach of a student project.

### B. Limitations

1. **No real Malaysian conversational speech in any evaluation.** All Manglish results are synthetic; Malay results are read speech.
2. **The silence guard is calibrated on 20 clips** (10 silent, 10 speech). Quiet or distant real speech may score higher no-speech probabilities than the clean speech tested, so its false-drop rate on real users is unknown. Uploads are capped at about 37 minutes of speech.
3. **Pronunciation** is phone-level GOP with an explicit accent-fairness rule, but its thresholds are uncalibrated, the phoneme recogniser is not trained on Malaysian speech, and its agreement with human raters is untested. The deployed speech recognition sometimes translates Malaysian-accented English into Malay (S14); whole-clip translations are caught and corrected, single-word ones are not.
4. **Disfluency** detection is rule-based on transcript and energy. The FluentNet-style classifier is not trained.
5. **Gaze.** A webcam recovers head and eye orientation, not point of regard. Tri-zone gaze is not implemented. Gaze Tunneling needs at least 100 s of speech to be decidable and has not been run on recordings of real faces (Section III.G).
6. **Confidence** weights are reasoned, not fitted. Expression models are trained mostly on posed, non-Malaysian faces.
7. **Code-switch characterisation** is a 193-word lexicon at whole-transcript level.
8. **LLM content feedback** is non-deterministic and model-dependent. The evaluated configuration uses Gemini; the guards were developed on a 3B local model. The fact check catches invented names and numbers, not invented claims expressed in common words.
9. **Deferral** is argued, not tested, and it forgoes immediate correction.
10. **Retention.** Recordings are retained until deleted; the ephemeral design in V1 is not implemented.
11. **Worked example.** The narrated example presentation was withdrawn, so the PresentCoach comparison is only partial.

### C. Generalisation and Threats to Validity

- **Internal validity.**
  - Synthetic test voices come from the same TTS family as the training data (in-domain).
  - FLEURS en_us train overlaps the English test domain.
  - Several design decisions and all functional checks were made by the developer.
  - Mitigations: held-out voices, a locked test split, per-clip outputs published, and statistics recomputed by script.
- **Construct validity.**
  - WER penalises orthographic variants of Manglish (T6).
  - "Pronunciation" is acoustic-model certainty.
  - "Confidence" is *perceived* confidence.
  - "Eye contact" is looking at the lens, not at an audience.
  - LLM-generated ratings (answer feedback, slide alignment) can carry the biases known for LLM judges, such as favouring longer or more fluent answers [78]; they must be validated against human ratings, not taken as ground truth.
  - Gaze aversion can be adaptive [35], [38].
- **External validity.**
  - Read FLEURS speech and TTS do not represent spontaneous, emotional and noisy practice speech.
  - Malay-, Chinese- and Indian-influenced Malaysian English differ [48].
  - Lighting, camera and microphone vary across users.
  - The accent-fairness set is specific to Malaysian English and must be re-derived for other varieties.
- **Conclusion validity.**
  - Small categories (4-clip columns).
  - Multiple comparisons across experiments.
  - The English fine-tune gain is borderline (p = 0.056); report CIs, not only point WERs.
- **Reproducibility.**
  - Cloud models can change without notice. Log the provider, model id and date for every run.
  - Local results are reproducible from the repository (commit `6f89bed` for the local ASR path). `fine-tune/scripts/paper_stats.py` recomputes Section IV.D's statistics from saved outputs.
- **Ethics.** Recording real users requires informed consent, approval from the institution's ethics committee, and opt-in data use (`fine-tune/docs/OWN_DATA_GUIDE.md`).

---

## VI. Conclusion and Future Work

SpeechMate shows that an accent-aware, deferred, multimodal speaking coach for Malaysian learners can run end to end on commodity hardware. It covers three practice functions on one analysis pipeline, and its feedback is tied to what was measured. The design decisions trace to identified gaps:
- fair treatment of Malaysian English (G1);
- deferral for cognitive load (G2);
- gaze–disfluency fusion (G3);
- measured code-switched ASR (G4);
- grounded LLM feedback (G5).

The most transferable findings are empirical and partly negative:
- Model choice dominated ASR accuracy (51.3% → 6.1%).
- A language-token setting silently turned transcription into translation.
- A router with perfect detection still doubled error because its target engine was weaker; we give the condition any future router must satisfy.
- Fine-tuning helps on in-domain data, and every gain must be read against the domain of its test set.

What is *not* established is that any of this helps a speaker improve. That is the remaining substantive work, and the thresholds are fixed in advance (Section IV.C) so the answer cannot be fitted to the system afterwards.

**Future work, in priority order**

1. **Collect per-session usage from real sessions** (now logged with every analysis: speech-to-text requests and billed seconds, Gemini calls and tokens) to replace the 5-second-phrase assumption in the cost model and decide whether to send whole turns instead of phrases.
2. **Real-speaker evaluation set.** 30–50 consenting Malaysian speakers, spontaneous and noisy speech, human-verified transcripts, filler and disfluency annotation (`fine-tune/docs/RECORDING_PROMPTS.md`, `SPEAKER_SCRIPT.md`). Then:
   - ASR WER by group, with raw and orthography-normalised scores;
   - the fine-tune go/no-go decision;
   - a bake-off including Qwen3-ASR [69].
3. **Human-rated validity studies:** pronunciation (r ≥ 0.7), disfluency (F1 ≥ 0.75), eye contact (≥ 0.80), confidence (ρ ≥ 0.5), and refitting the confidence weights with cross-validation.
4. **Validate Gaze Tunneling on real recordings**: gaze accuracy against manually coded frames, and the rate of significant links across sessions.
5. **Calibrate the pronunciation scorer** on rated real-speaker clips: GOP thresholds, regional credit, and per-category agreement with raters.
6. **Controlled deferral study:** deferred vs real-time alerts, within-subject, measuring performance and anxiety.
7. **Data protection:** separate consent per provider.
8. **Replayable evidence:** link every flagged moment to a clip of the recording, and adapt difficulty to a rolling baseline of the learner's own sessions.
9. **Token-level language ID**, replacing the lexicon.

---

## Appendix A. Corrections to Paper V1

| V1 statement | Current fact | Action |
|---|---|---|
| Backend on Python 3.13 with SQLite; websocket routes | Python 3.12, PostgreSQL; REST + polling, no websockets | update §II.B |
| Router: faster-whisper *small* → wav2vec2-mixed; "the mechanism behind the code-switching support" | evaluated: doubles WER on mixed speech; removed. ASR now Malaysian Whisper (local) or Whisper large-v3 (cloud) with auto language | rewrite as an evaluated design (§III.C, §IV.B) |
| Pronunciation scored by GOP forced alignment with regional/intelligibility split | implemented 2026-10-16: phone-level GOP on a CTC forced alignment with the regional/intelligibility split (§III.E); thresholds uncalibrated | describe as implemented, validation pending |
| "No model fine-tuning or training was performed" | LoRA fine-tune trained and evaluated; not deployed | update status and limitations |
| Ephemeral retention with a configurable review window | implemented 2026-10-16: recordings deleted when their analysis completes unless the user keeps them; consent, export and erasure added | state the implemented rule (§III.H) |
| "Locally deployable"; coaching calls an external LLM | evaluated and deployed in the cloud (Groq ASR, Gemini LLM); local configuration optional | reframe gap (iv) as "optional local deployment", not a headline contribution |
| Tri-zone gaze re-implementation | camera/left/right/down iris classes; browser head-pose heuristic | rephrase as "inspired by" |
| Disfluency stamped onto the transcript timeline | was stamped on transcript arrival in the browser (S9); now computed on the server from word timestamps with a significance test | describe the server-side method and the revision |
| Pre-presentation scripting assistant (O1) | deck comprehension (insights, key point per slide) for checking alignment between the deck and the talk; narrated example withdrawn (Section III.B) | rename O1's mechanism |
| Feedback "being rebuilt around a fixed schema" | implemented: measured candidates, plan enforcement, fact check | move to §III.I |
| Six products compared | eight columns including Speeko | keep, and re-verify claims at submission |

## Appendix B. Objective → Mechanism → Evaluation Traceability

| Objective | Mechanism | Validating metric | Status |
|---|---|---|---|
| O1 lower upfront load | deck insights (key point per slide), interview question preview | Likert: preparedness, perceived load | [I] |
| O2 segmental + suprasegmental, accent-aware | CTC pronunciation + allowance; fluency, pace, pitch, loudness, pauses | r with raters ≥ 0.7; WPM and pause accuracy | [I]; GOP split [D] |
| O3 fuse gaze with disfluency | Gaze Tunneling on a shared timeline (server-side, permutation-tested) | accuracy vs coded video; permutation significance | [I]; real-face validation pending |
| O4 withhold in-session feedback | results page only; no live scores | anxiety + performance, within-subject | [I]; premise untested |
| O5 traceable AI feedback | measured candidates, plan enforcement, fact check, worked numbers on the reference page | Likert specificity/accuracy; fact-check flag rate | [I] |
| Cross-cutting: code-switched input | model selection + auto language + verbatim prompt; routing rejected | WER by group with CIs; translation incidents | [E] synthetic/read; real speakers pending |

## Appendix C. Reproducibility

| Result | File |
|---|---|
| Model selection, threads, beam | `docs/benchmarks/stt-benchmark-2026-09-30.md` (+ `.json`) |
| Language token | `docs/benchmarks/stt-benchmark-2026-10-01.md` |
| Prompt | `docs/benchmarks/stt-benchmark-2026-10-02.md` |
| Routing and fine-tune | `docs/benchmarks/stt-routing-and-finetune-2026-10-06.md`, `fine-tune/eval/paper/*.csv` |
| Real-speaker studies (when data exists) | `fine-tune/scripts/run_app_on_clips.py` → `fine-tune/scripts/study_stats.py` (WER raw/normalised, event F1, ICC and validity, Likert/Wilcoxon), guide in `fine-tune/docs/EVALUATION.md`; `study_stats.py selftest` |
| Figures | `python fine-tune/scripts/paper_figures.py` → `docs/figures/fig_asr_systems`, `fig_routing_paired` (PNG + PDF); `docs/figures/fig_results_page.png` (screenshot) |
| Deployed cloud ASR (Experiment 8) | `fine-tune/.venv-app/bin/python fine-tune/scripts/eval_groq.py` (free-tier caps built in), `docs/benchmarks/stt-groq-cloud-2026-10-15.md` |
| CIs and sign tests (Section IV.D) | `python3 fine-tune/scripts/paper_stats.py` (stdlib only, under 1 s; asserts it reproduces the reported WERs) |
| Fine-tune runs, including failures | `fine-tune/docs/RESULTS.md` |
| Removed local ASR | `docs/project/local-stt-removal.md` (commit `6f89bed`) |
| Confidence model | `backend/docs/confidence-model.md`, `backend/app/services/live/scoring.py` |
| Metric formulas and worked examples | `frontend/app/(app)/methodology/page.tsx`, `backend/app/services/live/` |
| Security controls | `docs/project/Security.md` |

## Appendix D. Suggested Figures

1. Architecture: three tiers, both model configurations.
2. Session timeline: word timings, 2 fps gaze samples and disfluency events in 5 s windows, before (transcript-arrival stamps) and after (word timestamps) the S9 fix.
3. Routing result: paired per-clip WER scatter, routing off vs on (196 of 200 above the diagonal).
4. Fine-tune result: per-group bar chart with 95% CIs, labelled in-domain and near-domain.
5. Results page: four pillars + per-answer feedback (screenshot).
6. Accent-fairness set: F1–F7 with intelligibility risk (from Section II.D).

## References

[1]–[23] as in V1. [24]–[81] were added for this revision. Authors and titles of the arXiv entries were checked against their arXiv pages on 2026-10-20. Re-check vendor pages [7]–[12], [66], [67], [81] at submission, since product capabilities change.

[1] JobStreet.com Malaysia, "Graduate Employability Survey and Job Outlook Report 2025," 2025.
[2] JobStreet Malaysia and Malaysian Employers Federation, "Graduate Skills Assessment 2025," 2025.
[3] M. G. W. Kho and S. H. Ting, "English proficiency, public speaking experience, and communication apprehension in oral presentation of polytechnic students," 2023.
[4] S. Loewen, D. R. Isbell, and Z. Sporn, "The efficacy of app-based language learning for developing spoken proficiency," 2020.
[5] H. Kang, R. Yang, R. Song, C. Yang, and W. Wang, "An approach of query audience's attention in virtual speech," *Sensors*, vol. 24, no. 16, art. 5363, 2024.
[6] D. Carless, "Differing perceptions in the feedback process," *Stud. High. Educ.*, vol. 31, no. 2, pp. 219–233, 2006.
[7] Orai, "6 Best AI Speech Coach Apps in 2026," Orai Blog, 2026.
[8] Wellspoken, "Best App for Public Speaking in 2026," Wellspoken Blog, 2026.
[9] Yoodli, product documentation, 2026.
[10] Elqo, "Elqo vs Yoodli vs Orai," Elqo Blog, 2026.
[11] ELSA Speak, product documentation, 2026.
[12] BoldVoice, App Store listing, 2026.
[13] V. C. Mathad et al., "The impact of forced-alignment errors on automatic pronunciation evaluation," in *Proc. Interspeech*, 2021, pp. 1922–1926.
[14] J. Sweller, "Cognitive load during problem solving: Effects on learning," *Cogn. Sci.*, vol. 12, no. 2, pp. 257–285, 1988.
[15] D. L. Butler and P. H. Winne, "Feedback and self-regulated learning: A theoretical synthesis," *Rev. Educ. Res.*, vol. 65, no. 3, pp. 245–281, 1995.
[16] N. K. Dennis, "Automatic speech recognition: Foundations and applications," 2024.
[17] T. Kourkounakis, A. Hajavi, and A. Etemad, "FluentNet: End-to-end detection of stuttered speech disfluencies with deep learning," *IEEE/ACM Trans. Audio Speech Lang. Process.*, vol. 29, pp. 2986–2999, 2021.
[18] L. Du, X. Zhang, and G. Lan, "Talk to me, not the slides," arXiv:2602.01201, 2026.
[19] S. Latif, F. XianWen, and L. L. Wang, "Intelligent decision support system approach for predicting the performance of students," *J. Intell. Syst.*, vol. 30, no. 1, pp. 739–749, 2021.
[20] F. Saleem, Z. Ullah, B. Fakieh, and F. Kateb, "Intelligent decision support system for predicting student's E-learning performance," *Mathematics*, vol. 9, no. 17, p. 2078, 2021.
[21] P. Qin et al., "AI-based speaking assistant: Supporting non-native speakers' speaking in real-time multilingual communication," *Proc. ACM Hum.-Comput. Interact.*, vol. 9, no. 7, pp. 1–28, 2025.
[22] A. Koenecke et al., "Racial disparities in automated speech recognition," *Proc. Natl. Acad. Sci.*, vol. 117, no. 14, pp. 7684–7689, 2020.
[23] Mesolitica, "wav2vec2-xls-r-300m-mixed," model card, Hugging Face, 2023.
[24] P. D. MacIntyre and R. C. Gardner, "The subtle effects of language anxiety on cognitive processing in the second language," *Lang. Learn.*, vol. 44, no. 2, pp. 283–305, 1994.
[25] J. Hattie and H. Timperley, "The power of feedback," *Rev. Educ. Res.*, vol. 77, no. 1, pp. 81–112, 2007.
[26] V. J. Shute, "Focus on formative feedback," *Rev. Educ. Res.*, vol. 78, no. 1, pp. 153–189, 2008.
[27] A. N. Kluger and A. DeNisi, "The effects of feedback interventions on performance," *Psychol. Bull.*, vol. 119, no. 2, pp. 254–284, 1996.
[28] D. J. Nicol and D. Macfarlane-Dick, "Formative assessment and self-regulated learning: A model and seven principles of good feedback practice," *Stud. High. Educ.*, vol. 31, no. 2, pp. 199–218, 2006.
[29] J. A. Kulik and C.-L. C. Kulik, "Timing of feedback and verbal learning," *Rev. Educ. Res.*, vol. 58, no. 1, pp. 79–97, 1988.
[30] E. K. Horwitz, M. B. Horwitz, and J. Cope, "Foreign language classroom anxiety," *Mod. Lang. J.*, vol. 70, no. 2, pp. 125–132, 1986.
[31] J. Sweller, J. J. G. van Merriënboer, and F. G. W. C. Paas, "Cognitive architecture and instructional design," *Educ. Psychol. Rev.*, vol. 10, no. 3, pp. 251–296, 1998.
[32] J. Sweller and G. A. Cooper, "The use of worked examples as a substitute for problem solving in learning algebra," *Cogn. Instr.*, vol. 2, no. 1, pp. 59–89, 1985.
[33] S. Kalyuga, P. Ayres, P. Chandler, and J. Sweller, "The expertise reversal effect," *Educ. Psychol.*, vol. 38, no. 1, pp. 23–31, 2003.
[34] R. E. Mayer, *Multimedia Learning*, 2nd ed. Cambridge Univ. Press, 2009.
[35] A. M. Glenberg, J. L. Schroeder, and D. A. Robertson, "Averting the gaze disengages the environment and facilitates remembering," *Mem. Cogn.*, vol. 26, no. 4, pp. 651–658, 1998.
[36] G. Aparin, V. Popov, T. Sadekova and A. Yermekova, "Whisper hallucination detection and mitigation via hidden representation steering and sparse autoencoders," arXiv:2606.07473, 2026.
[37] Z. Ji et al., "Survey of hallucination in natural language generation," *ACM Comput. Surv.*, vol. 55, no. 12, 2023.
[38] G. Doherty-Sneddon and F. G. Phelps, "Gaze aversion: A response to cognitive or social difficulty?" *Mem. Cogn.*, vol. 33, no. 4, pp. 727–733, 2005.
[39] A. Radford et al., "Robust speech recognition via large-scale weak supervision," in *Proc. ICML*, 2023.
[40] A. Baevski, H. Zhou, A. Mohamed, and M. Auli, "wav2vec 2.0: A framework for self-supervised learning of speech representations," in *Proc. NeurIPS*, 2020.
[41] A. Babu et al., "XLS-R: Self-supervised cross-lingual speech representation learning at scale," in *Proc. Interspeech*, 2022.
[42] A. Koenecke et al., "Careless Whisper: Speech-to-text hallucination harms," in *Proc. ACM FAccT*, 2024.
[43] S. M. Witt and S. J. Young, "Phone-level pronunciation scoring and assessment for interactive language learning," *Speech Commun.*, vol. 30, no. 2–3, pp. 95–108, 2000.
[44] J. M. Levis, "Changing contexts and shifting paradigms in pronunciation teaching," *TESOL Q.*, vol. 39, no. 3, pp. 369–377, 2005.
[45] M. J. Munro and T. M. Derwing, "Foreign accent, comprehensibility, and intelligibility in the speech of second language learners," *Lang. Learn.*, vol. 45, no. 1, pp. 73–97, 1995.
[46] J. Jenkins, *The Phonology of English as an International Language*. Oxford Univ. Press, 2000.
[47] L. Baskaran, "Malaysian English: Phonology," in *Varieties of English 4: Africa, South and Southeast Asia*, R. Mesthrie, Ed. Mouton de Gruyter, 2008.
[48] H. S. Phoon, A. C. Abdullah, and M. Maclagan, "The consonant realizations of Malay-, Chinese- and Indian-influenced Malaysian English," *Aust. J. Linguist.*, vol. 33, no. 1, pp. 3–30, 2013.
[49] S. Pillai, Z. Mohd. Don, G. Knowles, and J. Tang, "Malaysian English: An instrumental analysis of vowel contrasts," *World Englishes*, vol. 29, no. 2, pp. 159–172, 2010.
[50] J. Schneider, D. Börner, P. van Rosmalen, and M. Specht, "Presentation Trainer, your public speaking multimodal coach," in *Proc. ACM ICMI*, 2015.
[51] M. I. Tanveer, E. Lin, and M. E. Hoque, "Rhema: A real-time in-situ intelligent interface to help people with public speaking," in *Proc. ACM IUI*, 2015.
[52] M. Fung et al., "ROC Speak: Semi-automated personalized feedback on nonverbal behavior from recorded videos," in *Proc. ACM UbiComp*, 2015.
[53] L. Batrinca, G. Stratou, A. Shapiro, L.-P. Morency, and S. Scherer, "Cicero: Towards a multimodal virtual audience platform for public speaking training," in *Proc. IVA*, 2013.
[54] M. E. Hoque, M. Courgeon, J.-C. Martin, B. Mutlu, and R. W. Picard, "MACH: My automated conversation coach," in *Proc. ACM UbiComp*, 2013.
[55] Chen et al., "PresentCoach," arXiv:2511.15253, 2025 (copy in `backend/docs/`).
[56] M. A. Covington and J. D. McFall, "Cutting the Gordian knot: The moving-average type–token ratio (MATTR)," *J. Quant. Linguist.*, vol. 17, no. 2, pp. 94–100, 2010.
[57] A. de Cheveigné and H. Kawahara, "YIN, a fundamental frequency estimator for speech and music," *J. Acoust. Soc. Am.*, vol. 111, no. 4, pp. 1917–1930, 2002.
[58] A. Conneau et al., "FLEURS: Few-shot learning evaluation of universal representations of speech," in *Proc. IEEE SLT*, 2022.
[59] emhaihsan, "Synth-Manglish," dataset, Hugging Face (CC BY 4.0).
[60] M. Bisani and H. Ney, "Bootstrap estimates for confidence intervals in ASR performance evaluation," in *Proc. IEEE ICASSP*, 2004.
[61] B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. Chapman & Hall, 1993.
[62] T. K. Koo and M. Y. Li, "A guideline of selecting and reporting intraclass correlation coefficients for reliability research," *J. Chiropr. Med.*, vol. 15, no. 2, pp. 155–163, 2016.

[63] T. Nguyen and H.-D. Tran, "Can we train ASR systems on code-switch without real code-switch data? Case study for Singapore's languages," in *Proc. Interspeech*, 2025, arXiv:2506.14177.
[64] Y. Yang, Y. Peng, X. Zhong, H. Huang and E. S. Chng, "Adapting OpenAI's Whisper for speech recognition on code-switch Mandarin-English SEAME and ASRU2019 datasets," arXiv:2311.17382, 2023.
[65] Mesolitica, "Malaysian-whisper-large-v3-turbo-v3," model card, Hugging Face, 2025. [Online]. Available: https://huggingface.co/mesolitica/Malaysian-whisper-large-v3-turbo-v3
[66] Groq, "Speech to text (whisper-large-v3)," API documentation, 2026. [Online]. Available: https://console.groq.com/docs/speech-to-text
[67] Google, "Gemini API: OpenAI compatibility," documentation, 2026. [Online]. Available: https://ai.google.dev/gemini-api/docs/openai
[68] Qwen Team, "Qwen2.5 technical report," arXiv:2412.15115, 2024.
[69] Qwen Team, "Qwen3-ASR technical report," arXiv:2601.21337, 2026.
[70] E. J. Hu et al., "LoRA: Low-rank adaptation of large language models," in *Proc. ICLR*, 2022.
[71] C. Lugaresi et al., "MediaPipe: A framework for building perception pipelines," arXiv:1906.08172, 2019.
[72] Y. Kartynnik, A. Ablavatski, I. Grishchenko, and M. Grundmann, "Real-time facial surface geometry from monocular video on mobile GPUs," arXiv:1907.06724, 2019.
[73] V. Bazarevsky et al., "BlazePose: On-device real-time body pose tracking," arXiv:2006.10204, 2020.
[74] hexgrad, "Kokoro-82M," model card, Hugging Face, 2025. [Online]. Available: https://huggingface.co/hexgrad/Kokoro-82M
[75] A. Dosovitskiy et al., "An image is worth 16x16 words: Transformers for image recognition at scale," in *Proc. ICLR*, 2021.
[76] I. J. Goodfellow et al., "Challenges in representation learning: A report on three machine learning contests," in *Proc. ICONIP*, 2013 (FER2013).
[77] Laws of Malaysia, *Personal Data Protection Act 2010* (Act 709).
[78] L. Zheng et al., "Judging LLM-as-a-judge with MT-Bench and Chatbot Arena," in *Proc. NeurIPS Datasets and Benchmarks*, 2023.
[79] J. Cohen, "A coefficient of agreement for nominal scales," *Educ. Psychol. Meas.*, vol. 20, no. 1, pp. 37–46, 1960.
[80] Q. Xu, A. Baevski, and M. Auli, "Simple and effective zero-shot cross-lingual phoneme recognition," in *Proc. Interspeech*, 2022.
[81] Google, "Gemini Developer API pricing," documentation, accessed 2026-10-20. [Online]. Available: https://ai.google.dev/gemini-api/docs/pricing
