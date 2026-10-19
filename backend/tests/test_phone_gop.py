"""Phone-level accent-fair pronunciation (phone_gop.py), without loading the model:
synthetic posteriors stand in for the phoneme recogniser."""

import pytest

from app.services.live import phone_gop as pg
from app.services.live.phone_gop import Phone

torch = pytest.importorskip("torch")
pytest.importorskip("torchaudio")

VOCAB = {"<pad>": 0, "θ": 1, "ɪ": 2, "ŋ": 3, "k": 4, "t": 5, "l": 6, "æ": 7, "s": 8, "w": 9, "v": 10, "iː": 11,
         "ə": 12, "ɐ": 13}


def test_ipa_tokens_stress_and_skipped_words():
    assert pg.tokenize_ipa("θ_ˈɪ_ŋ_k", VOCAB) == [("θ", False), ("ɪ", True), ("ŋ", False), ("k", False)]
    assert [t for t, _ in pg.tokenize_ipa("θ_ˈɪŋ_k", VOCAB)] == ["θ", "ɪ", "ŋ", "k"]    # longest-match split
    assert [t for t, _ in pg.tokenize_ipa("(en)_θ_ɪ", VOCAB)] == ["θ", "ɪ"]             # espeak language tags dropped
    assert pg.tokenize_ipa("ʒ_ɪ", VOCAB) is None
    assert pg.scoreable("think") and not pg.scoreable("lah") and not pg.scoreable("saya") and not pg.scoreable("2025")


def _p(expected, heard, ratio=0.2, stressed=True):
    return Phone(0, expected, stressed, ratio, heard)


def test_regional_variation_accepted_reduction_ok_other_deviations_flagged():
    assert pg.classify(_p("θ", "t"), word_final=False, after_consonant=False) == ("regional", "F1")
    assert pg.classify(_p("t", None), word_final=True, after_consonant=True) == ("regional", "F2")       # "las'"
    assert pg.classify(_p("t", "ʔ"), word_final=True, after_consonant=False) == ("regional", "F4")
    assert pg.classify(_p("t", "ʔ"), word_final=False, after_consonant=False)[0] == "intelligibility"
    assert pg.classify(_p("eə", "ɛ"), word_final=True, after_consonant=False) == ("regional", "F6")       # non-rhotic "shared"
    assert pg.classify(_p("ʊ", "ɪ", stressed=False), word_final=False, after_consonant=True) == ("ok", None)  # "singular"
    assert pg.classify(_p("v", "w"), word_final=False, after_consonant=False) == ("intelligibility", None)
    assert pg.classify(_p("θ", "t", ratio=0.9), word_final=False, after_consonant=False) == ("ok", None)


def test_chunks_split_at_gaps_and_length():
    words = [{"start": s, "end": s + 0.4} for s in (0, 0.5, 1.0, 3.0, 3.5)] + [{"start": 4 + i, "end": 4.5 + i} for i in range(14)]
    groups = pg.chunks(words)
    assert groups[0] == [0, 1, 2] and all(words[g[-1]]["end"] - words[g[0]]["start"] <= pg.CHUNK_SEC for g in groups)


def _posteriors(frames):
    rows = []
    for tok, p in frames:
        row = torch.full((len(VOCAB),), (1 - p) / (len(VOCAB) - 1))
        row[VOCAB[tok]] = p
        rows.append(row)
    return torch.stack(rows).log()


def test_gop_on_synthetic_posteriors():
    # "think" said as "tink" (F1), "vest"-like v said as w, and a reduced vowel heard as ɐ for expected ə
    frames = ([("<pad>", .9)] + [("t", .9)] * 3 + [("ɪ", .9)] * 3 + [("ŋ", .9)] * 3 + [("k", .9)] * 3 + [("<pad>", .9)]
              + [("w", .9)] * 3 + [("ɪ", .9)] * 3 + [("s", .9)] * 3 + [("t", .9)] * 3 + [("<pad>", .9)] + [("ɐ", .9)] * 3)
    tokens = [[("θ", True), ("ɪ", True), ("ŋ", False), ("k", False)],
              [("v", True), ("ɪ", True), ("s", False), ("t", False)], [("ə", False)]]
    phones = pg.label(pg.align_chunk(_posteriors(frames), tokens, VOCAB, blank=0))
    th, v, schwa = phones[0], phones[4], phones[8]
    assert (th.category, th.heard, th.feature) == ("regional", "t", "F1")
    assert (v.category, v.heard) == ("intelligibility", "w")
    assert schwa.category == "ok" and schwa.ratio > 0.9                  # ɐ counts as the expected ə
    assert all(p.category == "ok" for p in phones if p not in (th, v))

    s = pg.summarise(["think", "vest", "a"], {0: phones[:4], 1: phones[4:8], 2: phones[8:]})
    think, vest, _ = s["word_scores"]
    assert think["score"] > vest["score"] and think["is_correct"]          # regional credit keeps "think" fine
    assert [d["word"] for d in s["regional"]] == ["think"] and [d["word"] for d in s["intelligibility"]] == ["vest"]


def test_us_uk_variants_are_not_errors_and_simplified_clusters_are_regional():
    assert "ʌ" in pg.EQUIVALENT["ɒ"] and "iː" in pg.EQUIVALENT["iə"]          # "was", "clear" with a US accent
    assert pg.classify(_p("d", "n"), word_final=True, after_consonant=True, previous="n") == ("regional", "F2")  # "an'"
