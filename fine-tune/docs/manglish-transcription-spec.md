# Manglish Speech Transcription: Free, Local Spec for SpeechMate

Status: draft v1, researched 2 Oct 2026
Goal: turn the user's spoken Manglish (Malay + English mixed, often inside one sentence) into accurate text, using only free software that runs on a local machine.

---

## 1. TL;DR

1. **No public benchmark exists for Malay-English code-switching**, so nobody can honestly tell you "model X is the most accurate for Manglish". Any ranking, including this one, is provisional until you test on your own audio.
2. **Run a 3-way bake-off** on 30-50 clips of real target users:
   - A. `large-v3-turbo` (vanilla Whisper) via faster-whisper
   - B. `mesolitica/Malaysian-whisper-large-v3-turbo-v3` (Malaysian fine-tune)
   - C. `Qwen3-ASR-1.7B` (Apache-2.0, lists Malay and English)
3. **Provisional default until the bake-off says otherwise: A (vanilla large-v3-turbo)** with VAD, a Manglish `initial_prompt`, and a fixed language. Reasons: clear licensing, easy to run, and in the only side-by-side example I found it kept English words as English (see 3.2).
4. **Do not auto-translate or auto-"correct" the transcript.** SpeechMate is a coaching tool. Keep a raw transcript and a cleaned one (section 6).
5. **Do not use the browser Web Speech API.** It sends audio to a cloud service and works in one locale at a time.

---

## 2. What the evidence says (and how much to trust it)

| Claim | Source type | Trust |
|---|---|---|
| Off-the-shelf Whisper is roughly 21% WER on code-switched Malay/English and roughly 30% on monolingual Malay; best published adaptation is roughly 17% with no released checkpoint. | Project spike on GitHub (issue #9), numbers quoted without a named paper | Low-medium. Useful ballpark, not verified. |
| ASR error rates rise by 30-50% (relative) on code-switched speech versus monolingual. | Data paper for a Hinglish corpus (not Malay) | Low for Manglish. Direction is plausible, figure is from another language pair. |
| Whisper models are unevenly accurate across languages and weaker on low-resource languages and accents. | Whisper model card | High (the authors say so). |
| Fine-tuning Whisper on code-switched data reduces error (Mandarin-English, Singapore languages including Malay-English). | Several arXiv papers | Medium. Shows the technique works; those models are mostly not released. |

**Gap:** nothing above measures your users' Manglish on the models you can download today.

---

## 3. Candidates

### 3.1 Summary

| | A. Vanilla `large-v3-turbo` | B. Mesolitica Malaysian-Whisper turbo-v3 | C. Qwen3-ASR (1.7B / 0.6B) |
|---|---|---|---|
| Runs locally and free | Yes | Yes | Yes |
| Licence | Whisper is MIT (verify on the repo you download from) | **No licence visible on the model card I fetched; the GitHub spike calls it undeclared.** Treat as unknown. | Apache-2.0 (stated on the repo and model card) |
| Malay support | Yes (weaker, low-resource) | Trained on Malaysian data incl. Manglish | `ms` is on the supported list |
| English | Strong | Unclear after fine-tune (see 3.2) | Strong |
| Manglish-specific evidence | None found | Model card claims Manglish handling, shows one example clip; no published number I could verify | None found |
| Streaming | No (chunk it) | No (chunk it) | Offline and streaming modes advertised |
| Ease of local use | Easiest (faster-whisper, whisper.cpp) | Transformers; faster-whisper needs a CTranslate2 conversion and has a custom task token (untested here) | `qwen-asr` package, vLLM, MLX port |
| Provisional rank | 1 (default) | 2 (promising, needs checking) | 2 (dark horse, untested for Manglish) |

### 3.2 Things I found that should change your plan

- **The Mesolitica fine-tune may "translate" English into Malay.** On its own model card, in the conversational sample with mixed speech, the vanilla turbo output kept English phrases such as "work life balance" and "take flight", while the fine-tune's output rendered them in Malay. Caveats: it is one clip, and the fine-tune sample used its special `transcribeprecise` task while the vanilla sample used plain `transcribe`, so it is not a clean comparison. But for a coaching tool that must preserve exactly what the user said, this is the first thing to test.
- **A separate hallucination paper (arXiv 2609.32560) reports the Malaysian fine-tunes doing worse on noisy and "wild" audio** than base Whisper (for example, 60.7% vs 31.8% WER on its "genuine" set for the turbo-v3 fine-tune vs base turbo). That paper measures hallucination and noise robustness across many languages, not Manglish accuracy, so do not read it as "the fine-tune is worse at Manglish". It is a flag to include noisy and silent clips in your test set.
- **Licensing:** if this ever ships to other people, an undeclared licence on the weights is a blocker. For a personal local project it is a lower risk, but check the model page again before you rely on it.
- **Name trap:** a Hugging Face model called `whisper-small-manglish` is for **Malayalam**-English, not Malay-English. Ignore it.
- **Whisper large-v3 hallucination reports exist** (mostly on silence and real-world audio). The source I found is a competitor's blog, so treat the magnitude with scepticism, but it supports using VAD to avoid feeding silence to the model.

---

## 4. Recommended approach

### Phase 0: Decide what "accurate" means (30 minutes)

For SpeechMate, five things matter, not just overall WER:

1. Overall WER on mixed sentences.
2. **English-word accuracy** and **Malay-word accuracy**, scored separately.
3. **Language preservation:** Malay stays Malay, English stays English (no translating).
4. **Filler retention** ("um", "uh", "like", "lah"). Coaching needs these.
5. **Silence safety:** no invented text when the user is quiet.

### Phase 1: Build the bake-off (1-2 days)

Collect 30-50 clips, 5-20 seconds each, recorded the way real users will record (laptop mic, room noise like your screenshot's background). Include:

- Mostly English with Malay particles and words ("lah", "kan", "macam", "boleh")
- Real intra-sentence switching (English frame, Malay noun or verb, and the reverse)
- Mostly Malay
- A few silent or near-silent clips
- A few noisy clips

Hand-transcribe each one **exactly as spoken**. Run all three candidates on the same clips. Score with the script in section 8.

### Phase 2: Pick and tune (1 day)

Take the winner and tune: language setting, `initial_prompt`, VAD thresholds, chunk length. Re-run the same clips after each change so you can see what helped.

### Phase 3: Build into SpeechMate (see sections 5 and 6)

---

## 5. Architecture (all local)

```
Browser (mic) --16 kHz mono PCM chunks--> WebSocket --> Local server (Python/FastAPI)
                                                          |
                                                    Silero VAD (utterance boundaries)
                                                          |
                                           +--------------+--------------+
                                           | partial pass (small/fast)   | final pass (best model)
                                           v                             v
                                    live "Transcript" box          raw transcript -> cleaned transcript
                                                                          |
                                                                  AI partner + scoring
```

Key points:

- **Capture:** `getUserMedia` with echo cancellation on, so the AI partner's voice does not leak back into the mic. Resample to 16 kHz mono.
- **VAD:** use Silero VAD (free) to decide when the user has started and finished speaking. This also stops the model hearing silence, which is where hallucinations tend to appear.
- **Two-pass:** a fast pass (small model, or re-transcribe the growing buffer every 1-2 s) for live text; a final pass with the best model once VAD says the utterance ended. Only the final text goes to the AI partner.
- **Provider interface:** put the engine behind one function, `transcribe(audio, hints) -> {text, words, language_spans}`. Then swapping A, B or C is a config change.
- **Local LLM cleanup (optional):** a small model via Ollama can add punctuation and casing. Tell it explicitly: do not translate, do not fix grammar, do not remove fillers.

### Hardware tiers (starting points, not measured)

| Machine | Try first |
|---|---|
| No GPU, ordinary laptop | `small` or Qwen3-ASR-0.6B; expect slower and less accurate, mainly on Malay |
| NVIDIA GPU with 6 GB+ VRAM | `large-v3-turbo` in faster-whisper with float16 |
| Apple Silicon | whisper.cpp, MLX Whisper, or `mlx-qwen3-asr` |

---

## 6. Raw vs cleaned transcript (product decision)

Keep two versions of every utterance:

| Version | Contents | Used for |
|---|---|---|
| **Raw** | As close as possible to what was said: fillers, repetitions, grammar slips, code-switches untouched | Coaching metrics, filler counts, grammar feedback |
| **Cleaned** | Punctuation and casing restored; same words | Display, AI partner's conversation |

If cleanup "fixes" a sentence like the learner's own mistake, the coaching tool erases the thing it is supposed to catch. Also note that Whisper-family models often drop fillers by default, so test filler retention explicitly (a prompt that itself contains fillers can encourage Whisper to keep them; verify on your clips).

Add a tap-to-correct on the live transcript. It is cheap and fixes the worst misheard words before they reach the AI partner (as in "wouldn't be dear" in the screenshot).

---

## 7. Tuning knobs to try (Whisper-family)

1. **Fix the language** to the dominant one (`en` for mostly-English Manglish, `ms` for mostly-Malay) rather than auto-detect, which tends to flip on short clips. A community pipeline using the Malaysian fine-tune reported English being mis-routed and added a bias threshold for the language token; the same idea applies to you.
2. **`initial_prompt`:** a short example sentence in the style you expect, plus the current conversation topic. Example: "Okay lah, so macam this week saya busy sikit, um, but boleh la."
3. **`condition_on_previous_text=False`** to reduce runaway repetition across chunks.
4. **VAD filter on**, with a minimum silence of roughly 300-500 ms (tune on your clips).
5. **Word timestamps on**, so you can measure pauses and speaking pace later.

Faster-whisper sketch (not run here; check parameter names against the version you install):

```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3-turbo", device="auto", compute_type="auto")

PROMPT = "Okay lah, so macam this week saya busy sikit, um, but boleh la."

segments, info = model.transcribe(
    "clip.wav",
    language="en",                      # or "ms"; compare both in the bake-off
    initial_prompt=PROMPT,
    vad_filter=True,
    condition_on_previous_text=False,
    word_timestamps=True,
)
text = " ".join(s.text.strip() for s in segments)
print(text)
```

---

## 8. Scoring script (bake-off)

Layout:

```
bench/
  clips/            # 001.wav, 002.wav, ...
  refs.json         # {"001": "reference text as spoken", ...}
  hyps/
    A_whisper/      # 001.txt, ...
    B_mesolitica/
    C_qwen3/
  score.py
```

`score.py` (sketch, not run here):

```python
import json, re, sys
from pathlib import Path
import jiwer  # pip install jiwer

def norm(t: str) -> str:
    t = t.lower()
    t = re.sub(r"[^\w\s']", " ", t)   # drop punctuation, keep apostrophes
    return re.sub(r"\s+", " ", t).strip()

refs = json.loads(Path("refs.json").read_text(encoding="utf-8"))

for system_dir in sorted(Path("hyps").iterdir()):
    ref_list, hyp_list = [], []
    for clip_id, ref in refs.items():
        f = system_dir / f"{clip_id}.txt"
        if not f.exists():
            continue
        ref_list.append(norm(ref))
        hyp_list.append(norm(f.read_text(encoding="utf-8")))
    wer = jiwer.wer(ref_list, hyp_list)
    print(f"{system_dir.name}: WER {wer:.1%} over {len(ref_list)} clips")
```

Extra metrics to add by hand or with small scripts:

- English-word and Malay-word accuracy (tag words in the reference as `en` or `ms`; score each group separately)
- Fraction of reference fillers present in the hypothesis
- Output length on silent clips (anything above zero words is a hallucination)
- Real-time factor: processing time divided by audio length, on your machine

Use the **same normalisation for every system**, otherwise the comparison is meaningless.

---

## 9. Go / no-go criteria

Suggested starting thresholds (adjust to what your users will tolerate):

- Overall WER at or below about 20% on mixed clips (the published ballpark for off-the-shelf Whisper is around 21%; see section 2, low-medium trust)
- No translation of English into Malay or the reverse in more than a couple of clips
- Zero invented text on silent clips after VAD
- Final-pass latency under about 3 seconds after the user stops speaking on your target machine
- A clear licence on the chosen weights if you plan to distribute

If nothing meets these, fall back to: show the live transcript with tap-to-correct, and make the AI partner tolerant of transcript errors ("did you mean...?") rather than trusting the text blindly.

---

## 10. Milestones

| # | Milestone | Done when |
|---|---|---|
| M1 | Record and hand-transcribe 30-50 clips | `refs.json` exists |
| M2 | Run candidates A, B, C on all clips | Hypothesis files exist for each |
| M3 | Score and decide | Written result using section 9 criteria |
| M4 | Local server with VAD plus chosen model behind `transcribe()` | Speak into the browser, get final text |
| M5 | Live partial text and two-pass flow | Transcript box updates while speaking |
| M6 | Raw/cleaned split wired into coaching metrics | Filler count and pace come from raw text |
| M7 | Tap-to-correct and error logging | Corrections saved for future evaluation |

---

## 11. Open questions for the product owner

1. Which machine will this run on (CPU only, or which GPU)? This decides the model size.
2. Do you need live partial text, or is a short wait after the user stops speaking acceptable? Live text roughly doubles the complexity.
3. How mixed is the real speech: mostly English with Malay particles, or genuine switching inside sentences?
4. Will this ever be distributed to other people? If yes, weight licences matter.
5. Web only, or mobile too?

---

## 12. How to use this file

- Save it in your repo, for example `docs/manglish-transcription-spec.md`.
- Give it to your coding assistant (Claude Code, Cursor, etc.) with an instruction like: "Read docs/manglish-transcription-spec.md and implement Milestone M4 using the provider interface in section 5."
- Work one milestone at a time, and commit after each so you can roll back.
- Update section 3 with your own bake-off numbers once you have them. Those numbers will be worth more than anything in section 2.

---

## 13. Sources

- Spike on Malay/English code-switching accuracy (source of the 21% / 30% / 17% ballpark): https://github.com/SoongGuanLeong/footprint/issues/9
- Mesolitica Malaysian-whisper-large-v3-turbo-v3 model card: https://huggingface.co/mesolitica/Malaysian-whisper-large-v3-turbo-v3
- Mesolitica Malaysian-STT-Whisper dataset: https://huggingface.co/datasets/mesolitica/Malaysian-STT-Whisper
- Community pipeline using the Malaysian fine-tune (language-routing bias, VAD, per-chunk language detection): https://github.com/chibahari/whisper-transcribe
- "How to Reduce Whisper Hallucination" (benchmarks including Malaysian fine-tunes): https://arxiv.org/html/2609.32560
- Qwen3-ASR repo (Apache-2.0, 52 languages and dialects): https://github.com/QwenLM/Qwen3-ASR
- Qwen3-ASR model card with language list including Malay: https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf
- Qwen3-ASR technical report: https://arxiv.org/html/2601.21337v1
- Whisper large-v3 model card (uneven performance across languages): https://huggingface.co/reach-vb/whisper-large-v3
- Whisper-v3 hallucination write-up (competitor blog, treat with caution): https://deepgram.com/learn/whisper-v3-results
- Code-switching ASR with Singapore languages, including Malay-English: https://arxiv.org/html/2506.14177
- Hinglish code-switched corpus paper (source of the 30-50% relative increase figure): https://www.sciencedirect.com/science/article/pii/S2352340925006109
- Mandarin-English code-switching adaptation of Whisper (technique evidence): https://arxiv.org/pdf/2311.17382
- Name trap, Malayalam (not Malay) model: https://huggingface.co/neuroheart/whisper-small-manglish
