"""Phone-level, accent-fair pronunciation scoring (GOP over a CTC forced alignment).

1. Words → phonemes with espeak-ng, a phrase at a time so function words take their natural
   weak forms ("a" → /ɐ/), with the British English voice: Malaysian English, like British
   English, doesn't pronounce the r in "car" or "clear" (non-rhotic), so a US norm would
   penalise it.
2. Audio → phoneme posteriors with facebook/wav2vec2-xlsr-53-espeak-cv-ft (Xu et al. 2021, a
   multilingual phoneme recogniser with the same espeak phoneme set), in chunks of consecutive
   words (speech-recognition word timings) so memory stays bounded.
3. torchaudio's CTC forced alignment places each expected phoneme in the audio.
4. Goodness of Pronunciation per phoneme = mean over its frames of P(expected) / P(best phoneme)
   (Witt & Young 2000, in its CTC form), where "expected" includes equivalent realisations
   (a reduced vowel for another reduced vowel, r-coloured vs plain schwa).
5. Malay words aren't scored: each word is also aligned against its Malay pronunciation
   (espeak's Malay voice), and a word that fits Malay better is left out. Code-switching isn't
   an error, and this scores English pronunciation.
6. A phoneme under DEVIATION is a deviation. An unstressed vowel reduced to a schwa-like vowel
   is normal fluent speech (ok). A deviation matching a documented feature of Malaysian English
   (TECHNICAL.md §II.D: th-stopping, final cluster reduction, vowel length, final stops,
   monophthongs, non-rhotic r) is *regional variation*: reported, scored as acceptable. Any
   other deviation is *intelligibility-affecting*: it lowers the score and is named.

Thresholds are a reasoned start, not yet calibrated against human ratings (TECHNICAL.md §IV.C).
"""

import logging
import re
import subprocess
from dataclasses import dataclass

from app.services.live._ml import load_once

logger = logging.getLogger(__name__)

MODEL_NAME = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
DEVIATION = 0.5          # P(expected)/P(best) below this marks a deviation
WORD_OK = 60             # a word scoring below this is listed as unclear
REGIONAL_CREDIT = 85     # what a regional-variation phoneme scores (accepted, not perfect-native)
MALAY_MARGIN = 0.05      # a word is Malay if its Malay pronunciation fits this much better
CHUNK_SEC, GAP_SEC, PAD_SEC = 12.0, 0.8, 0.1

# (expected, heard) → Malaysian English feature (Baskaran 2008; Phoon et al. 2013; Pillai et al. 2010)
REGIONAL = {
    ("θ", "t"): "F1", ("θ", "f"): "F1", ("ð", "d"): "F1",
    ("iː", "ɪ"): "F3", ("iː", "i"): "F3", ("ɪ", "iː"): "F3", ("ɪ", "i"): "F3",
    ("uː", "ʊ"): "F3", ("uː", "u"): "F3", ("ʊ", "uː"): "F3", ("ʊ", "u"): "F3",
    ("æ", "ɛ"): "F3", ("ɛ", "æ"): "F3", ("ɑː", "a"): "F3", ("ɔː", "ɔ"): "F3", ("ɜː", "ə"): "F3",
    ("t", "ʔ"): "F4", ("k", "ʔ"): "F4", ("p", "ʔ"): "F4", ("d", "t"): "F4",
    ("eɪ", "e"): "F6", ("əʊ", "o"): "F6", ("oʊ", "o"): "F6", ("eə", "ɛ"): "F6", ("iə", "ɪ"): "F6", ("ʊə", "ʊ"): "F6",
}
FEATURE_NAMES = {
    "F1": "th said as t/d", "F2": "final consonant dropped", "F3": "vowel length or quality",
    "F4": "final stop softened", "F6": "single vowel for a diphthong",
}
# Realisations counted as the expected sound itself (not deviations): reduced vowels, weak/strong
# forms of function words, and the US/UK variants of the same vowel. No variety of English is the
# reference, so a speaker with a US accent isn't marked down against the British phonemes either.
EQUIVALENT = {
    "ə": {"ɐ", "ɚ", "ᵻ", "ɪ", "ʌ"}, "ɐ": {"ə", "ʌ", "eɪ", "a"}, "ᵻ": {"ɪ", "ə"}, "ɚ": {"ə"}, "ɜː": {"ɚ", "ɝ", "ɜ"},
    "ɪ": {"ᵻ"}, "ɾ": {"t", "d"}, "t": {"ɾ"}, "d": {"ɾ"}, "ɡ": {"g"}, "əl": {"l", "ə"},
    "ɒ": {"ɑː", "ɑ", "ʌ", "ɔ"}, "a": {"æ", "ɑː"}, "ɑː": {"æ", "a", "ɑ"}, "əʊ": {"oʊ", "oː", "o"},
    "iə": {"iː", "ɪɹ", "ɪ"}, "eə": {"ɛɹ", "ɛː"}, "ʊə": {"uː", "ʊɹ", "ɔː"}, "aɪə": {"aɪ", "aɪɚ"}, "aʊə": {"aʊ"},
}
REDUCED = {"ə", "ɐ", "ɪ", "ᵻ", "ʊ", "ɚ"}
CONSONANTS = set("pbtdkɡfvθðszʃʒhmnŋlɹrjwʔ") | {"tʃ", "dʒ"}


@dataclass
class Phone:
    word_index: int
    expected: str
    stressed: bool
    ratio: float          # P(expected)/P(best), 0-1
    heard: str | None     # best competing phoneme when deviating (None = dropped)
    category: str = "ok"  # ok | regional | intelligibility
    feature: str | None = None

    @property
    def score(self) -> float:
        return round(100 * self.ratio, 1)


# ── Words → phonemes ────────────────────────────────────────────────────────

def tokenize_ipa(ipa: str, vocab: dict[str, int]) -> list[tuple[str, bool]] | None:
    """espeak phonemes ("θ_ˈɪ_ŋ_k") → [(model token, stressed)]; None if a phoneme has no token."""
    out = []
    for ph in ipa.split("_"):
        stressed = "ˈ" in ph or "ˌ" in ph
        ph = re.sub(r"\([a-z-]+\)|[ˈˌ\s]", "", ph)          # stress marks, "(en)" language tags
        if not ph:
            continue
        i = 0
        while i < len(ph):                                  # longest match ("ɑːɹ" may be one token or two)
            for j in range(len(ph), i, -1):
                if ph[i:j] in vocab:
                    out.append((ph[i:j], stressed))
                    i = j
                    break
            else:
                return None
    return out


def _espeak(lines: list[str], voice: str) -> list[str] | None:
    try:
        res = subprocess.run(["espeak-ng", "-q", "--ipa", "--sep=_", "-v", voice], input="\n".join(lines),
                             capture_output=True, text=True, timeout=60, check=True)
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("espeak-ng failed: %s", e)
        return None
    out = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
    return out if len(out) == len(lines) else None


def g2p_phrase(words: list[str], voice: str) -> list[str | None]:
    """Phonemes of each word, phonemised as one phrase (natural weak forms); words whose phrase
    output doesn't split back into one item per word are phonemised on their own."""
    phrase = _espeak([" ".join(words)], voice)
    if phrase:
        parts = [p for p in re.sub(r"\([a-z-]+\)", "", phrase[0]).split() if p.strip("_")]
        if len(parts) == len(words):
            return parts
    return _espeak(words, voice) or [None] * len(words)


def scoreable(word: str) -> bool:
    from app.services.live.language import MALAY_WORDS, MANGLISH_PARTICLES

    w = word.lower()
    return bool(re.fullmatch(r"[a-z']+", w)) and w not in MALAY_WORDS and w not in MANGLISH_PARTICLES


def chunks(words: list[dict]) -> list[list[int]]:
    """Indices of consecutive words grouped into ≤ CHUNK_SEC stretches, split at long gaps."""
    groups, cur = [], []
    for i, w in enumerate(words):
        if cur and (w["start"] - words[cur[-1]]["end"] > GAP_SEC or w["end"] - words[cur[0]]["start"] > CHUNK_SEC):
            groups.append(cur)
            cur = []
        cur.append(i)
    return groups + ([cur] if cur else [])


# ── Alignment and GOP ───────────────────────────────────────────────────────

def classify(p: Phone, word_final: bool, after_consonant: bool, previous: str | None = None) -> tuple[str, str | None]:
    if p.ratio >= DEVIATION:
        return "ok", None
    if not p.stressed and p.expected not in CONSONANTS and p.heard in REDUCED:
        return "ok", None                                   # unstressed vowel reduced: fluent speech
    if p.heard and (p.expected, p.heard) in REGIONAL:
        feature = REGIONAL[(p.expected, p.heard)]
        if feature != "F4" or word_final:                   # final-stop softening only at a word's end
            return "regional", feature
    if word_final and after_consonant and p.expected in CONSONANTS and (p.heard is None or p.heard == previous):
        return "regional", "F2"                             # final cluster simplified: "las'", "an'" for "and"
    return "intelligibility", None


def align_chunk(log_probs, tokens: list[list[tuple[str, bool]]], vocab: dict[str, int], blank: int) -> list[Phone] | None:
    """Posterior ratio for every expected phoneme in one chunk. log_probs: [frames, vocab] (torch);
    tokens: the (phoneme, stressed) list of each word in the chunk, in order."""
    import torch
    from torchaudio.functional import forced_align, merge_tokens

    flat = [(wi, ph, st) for wi, phs in enumerate(tokens) for ph, st in phs]
    if not flat or log_probs.shape[0] < len(flat):
        return None
    targets = torch.tensor([[vocab[ph] for _, ph, _ in flat]], dtype=torch.int32)
    try:
        aligned, frame_scores = forced_align(log_probs[None].float(), targets, blank=blank)
    except Exception as e:  # noqa: BLE001 — too few frames for the phonemes, etc.
        logger.info("Forced alignment failed for a chunk: %s", e)
        return None
    spans = merge_tokens(aligned[0], frame_scores[0].exp())
    if len(spans) != len(flat):
        return None
    non_blank = log_probs.clone()
    non_blank[:, blank] = float("-inf")
    best = non_blank.max(dim=1).values
    inv = {i: t for t, i in vocab.items()}
    out = []
    for (wi, ph, st), span in zip(flat, spans):
        frames = slice(span.start, span.end)
        ok_ids = [vocab[ph]] + [vocab[e] for e in EQUIVALENT.get(ph, ()) if e in vocab]
        ratio = float((log_probs[frames][:, ok_ids].max(dim=1).values - best[frames]).exp().mean())
        heard = None
        if ratio < DEVIATION:
            mean_lp = non_blank[frames].mean(dim=0)
            mean_lp[ok_ids] = float("-inf")
            blank_share = float((log_probs[frames].argmax(dim=1) == blank).float().mean())
            heard = None if blank_share > 0.5 else inv.get(int(mean_lp.argmax()))   # blank wins: dropped
        out.append(Phone(wi, ph, st, ratio, heard))
    return out


def label(phones: list[Phone]) -> list[Phone]:
    """Fill in category/feature, using each phoneme's position in its word."""
    by_word: dict[int, list[Phone]] = {}
    for p in phones:
        by_word.setdefault(p.word_index, []).append(p)
    for ws in by_word.values():
        for k, p in enumerate(ws):
            prev = ws[k - 1].expected if k > 0 else None
            p.category, p.feature = classify(p, k == len(ws) - 1, prev in CONSONANTS, prev)
    return phones


def word_fit(phones: list[Phone]) -> dict[int, float]:
    fit: dict[int, list[float]] = {}
    for p in phones:
        fit.setdefault(p.word_index, []).append(p.ratio)
    return {w: sum(v) / len(v) for w, v in fit.items()}


def summarise(words: list[str], phones_by_word: dict[int, list[Phone]]) -> dict:
    """Word and session scores with regional variation accepted, plus the deviations found."""
    word_scores, deviations = [], []
    for wi, phones in sorted(phones_by_word.items()):
        credited = [max(p.score, REGIONAL_CREDIT) if p.category == "regional" else p.score for p in phones]
        s = round(sum(credited) / len(credited), 1)
        word_scores.append({"word": words[wi], "score": s, "is_correct": s >= WORD_OK})
        deviations += [{"word": words[wi], "expected": p.expected, "heard": p.heard or "(dropped)", "category": p.category,
                        "feature": p.feature, "feature_name": FEATURE_NAMES.get(p.feature or ""), "score": p.score}
                       for p in phones if p.category != "ok"]
    return {
        "score": round(sum(w["score"] for w in word_scores) / len(word_scores), 1) if word_scores else None,
        "word_scores": word_scores,
        "incorrect_words": [w["word"] for w in word_scores if not w["is_correct"]],
        "regional": [d for d in deviations if d["category"] == "regional"],
        "intelligibility": [d for d in deviations if d["category"] == "intelligibility"],
    }


# ── Model and entry point ───────────────────────────────────────────────────

@load_once
def _model():
    """(feature extractor, model, vocab). The checkpoint's own tokenizer needs the `phonemizer`
    package only to phonemize text, which espeak-ng does here, so its vocab.json is read directly."""
    import json

    from huggingface_hub import hf_hub_download
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

    logger.info("Loading phoneme model '%s' (CPU)…", MODEL_NAME)
    extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_NAME)
    model = Wav2Vec2ForCTC.from_pretrained(MODEL_NAME)
    model.eval()
    with open(hf_hub_download(MODEL_NAME, "vocab.json"), encoding="utf-8") as f:
        vocab = json.load(f)
    return extractor, model, vocab


def assess(wav_16k, word_timestamps: list[dict]) -> dict | None:
    """Blocking (call via asyncio.to_thread). None when nothing is scoreable or the model fails,
    so the caller can fall back to the word-level scorer."""
    import torch

    from app.services.live.audio import MODEL_SAMPLE_RATE, load_wav_float

    words = [w for w in word_timestamps or [] if w.get("start") is not None and w.get("end") is not None]
    clean = [re.sub(r"[^\w']", "", w["word"]).lower() for w in words]
    keep = [i for i, c in enumerate(clean) if scoreable(c)]
    if not keep:
        return None
    extractor, model, vocab = _model()
    blank = vocab["<pad>"]
    audio = load_wav_float(wav_16k)
    phones_by_word: dict[int, list[Phone]] = {}
    malay = 0
    for group in chunks([words[i] for i in keep]):
        idx = [keep[g] for g in group]
        en = [tokenize_ipa(x, vocab) if x else None for x in g2p_phrase([clean[i] for i in idx], "en-gb")]
        ms = [tokenize_ipa(x, vocab) if x else None for x in g2p_phrase([clean[i] for i in idx], "ms")]
        ok = [k for k in range(len(idx)) if en[k]]
        if not ok:
            continue
        a = max(0, int((words[idx[ok[0]]]["start"] - PAD_SEC) * MODEL_SAMPLE_RATE))
        b = min(len(audio), int((words[idx[ok[-1]]]["end"] + PAD_SEC) * MODEL_SAMPLE_RATE))
        if b - a < MODEL_SAMPLE_RATE // 10:
            continue
        inputs = extractor(audio[a:b], sampling_rate=MODEL_SAMPLE_RATE, return_tensors="pt")
        with torch.no_grad():
            log_probs = torch.log_softmax(model(inputs.input_values).logits[0], dim=-1)
        phones = align_chunk(log_probs, [en[k] for k in ok], vocab, blank)
        if not phones:
            continue
        # Which words are really Malay: their Malay pronunciation fits the audio better. A word with no
        # Malay phonemisation keeps its English one in this second alignment, so it can't "win" as Malay.
        ms_phones = align_chunk(log_probs, [ms[k] or en[k] for k in ok], vocab, blank)
        fit_en, fit_ms = word_fit(phones), word_fit(ms_phones or [])
        for p in label(phones):
            if fit_ms.get(p.word_index, 0) > fit_en[p.word_index] + MALAY_MARGIN:
                continue
            phones_by_word.setdefault(idx[ok[p.word_index]], []).append(p)
        malay += sum(1 for w in fit_en if fit_ms.get(w, 0) > fit_en[w] + MALAY_MARGIN)
    if not phones_by_word:
        return None
    return summarise(clean, phones_by_word) | {"method": "phone-gop", "words_scored": len(phones_by_word),
                                                "words_malay": malay, "words_skipped": len(words) - len(phones_by_word)}
