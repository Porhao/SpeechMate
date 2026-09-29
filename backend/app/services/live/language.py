"""Malaysian language support: English / Bahasa Melayu ratio, code-switching
(Manglish) detection, and the accent allowance applied to pronunciation.

The ratio is a lexicon lookup, not a trained language-ID model: every word is
checked against a list of common Bahasa Malaysia / colloquial Manglish tokens
and anything else counts as English. Proper nouns, rare Malay words and
code-switched compounds ("makan-makan session") can misclassify — it's a
whole-transcript estimate, not a per-segment classifier.
"""

import re
from dataclasses import asdict, dataclass

# Common BM function words, pronouns, particles and everyday vocabulary, plus
# the colloquial Manglish discourse particles ("lah", "lor", "kan"...).
MALAY_WORDS: set[str] = {
    # pronouns
    "saya", "aku", "awak", "kau", "korang", "dia", "ia", "kami", "kita", "mereka",
    "kamu", "beliau",
    # demonstratives / question words
    "ini", "itu", "sini", "situ", "sana", "mana", "apa", "siapa", "bila", "kenapa",
    "macam", "camna", "berapa", "yang", "yg",
    # common verbs
    "ada", "tak", "tiada", "tidak", "bukan", "boleh", "nak", "mahu", "suka", "buat",
    "pergi", "datang", "balik", "makan", "minum", "tidur", "kerja", "cakap", "kata",
    "tengok", "dengar", "faham", "tahu", "ingat", "rasa", "fikir", "cuba", "jadi",
    "bagi", "bawa", "ambil", "bagitau", "tanya", "jawab",
    # connectives / particles
    "dan", "atau", "tapi", "tetapi", "dengan", "dgn", "untuk", "utk", "dari", "dr",
    "kepada", "pada", "kalau", "jika", "sebab", "kerana", "supaya", "walaupun",
    "meskipun", "sambil", "selepas", "sebelum", "semasa", "sehingga", "hingga",
    "juga", "pun", "pon", "lagi", "dah", "sudah", "belum", "masih", "je", "jer",
    "sahaja", "saja", "lah", "lor", "kan", "eh", "wah", "aiyo", "aiya",
    # everyday nouns
    "orang", "hari", "masa", "waktu", "sekarang", "nanti", "esok", "semalam",
    "tadi", "rumah", "sekolah", "keluarga", "kawan", "duit", "wang",
    "makanan", "air",
    # adjectives / adverbs
    "betul", "salah", "baik", "bagus", "cantik", "hebat", "teruk", "susah",
    "senang", "mudah", "cepat", "lambat", "besar", "kecil", "banyak", "byk",
    "sikit", "sangat", "memang", "pasti", "mesti", "sepatutnya", "patut",
    "sebenarnya", "sebenar", "sekali", "agak", "hampir", "hanya", "cuma",
    "semua", "setiap", "masing", "sendiri", "bersama",
    # more everyday verbs/nouns
    "dulu", "fikiran", "pendapat", "pandangan", "cara", "jalan",
    "tempat", "benda", "perkara", "hal", "isu", "masalah", "keputusan",
    "jawapan", "soalan", "cadangan", "ialah", "adalah", "merupakan",
    "menjadi", "akan", "telah", "sedang", "pernah", "kerap", "selalu",
    "biasa", "jarang", "kadang", "kadangkala", "antara", "tentang",
    "mengenai", "terhadap", "oleh", "seperti",
}

# Discourse particles that signal Manglish *style*: a single "lah" flags it
# even in an otherwise all-English sentence.
MANGLISH_PARTICLES = {
    "lah", "mah", "weh", "kan", "lor", "leh", "la", "wei",
    "one", "what", "also", "already", "got", "no need",
}

_TOKEN_RE = re.compile(r"[a-zA-Z']+")


def estimate_language_ratio(text: str) -> tuple[float, float]:
    """(english_ratio, malay_ratio) by word count; (1.0, 0.0) for empty input."""
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    if not tokens:
        return 1.0, 0.0
    malay = sum(1 for t in tokens if t in MALAY_WORDS)
    return round((len(tokens) - malay) / len(tokens), 4), round(malay / len(tokens), 4)


def is_code_switching(english_ratio: float, malay_ratio: float, threshold: float = 0.15) -> bool:
    """Both languages present in meaningful proportion, not just a stray borrowed word."""
    return english_ratio >= threshold and malay_ratio >= threshold


@dataclass
class LanguageDetection:
    primary_language: str           # "en" | "ms" | "mixed"
    english_ratio: float            # 0–1
    malay_ratio: float              # 0–1
    is_code_switching: bool
    manglish_particles: list[str]
    detected_bm_words: list[str]
    accent_type: str                # "Malaysian English" | "Standard BM"

    def to_dict(self) -> dict:
        return asdict(self)


def detect_language_and_accent(transcript: str) -> LanguageDetection:
    words = [w.strip(".,!?\"'") for w in transcript.lower().split()]
    bm_found = sorted({w for w in words if w in MALAY_WORDS})
    manglish_found = sorted({w for w in words if w in MANGLISH_PARTICLES})

    en_ratio, bm_ratio = estimate_language_ratio(transcript)
    if bm_ratio > 0.7:
        primary, accent = "ms", "Standard BM"
    elif bm_ratio > 0.15 or manglish_found:
        primary, accent = "mixed", "Malaysian English"
    else:
        primary, accent = "en", "Malaysian English"

    return LanguageDetection(
        primary_language=primary,
        english_ratio=round(en_ratio, 2),
        malay_ratio=round(bm_ratio, 2),
        is_code_switching=is_code_switching(en_ratio, bm_ratio),
        manglish_particles=manglish_found,
        detected_bm_words=bm_found,
        accent_type=accent,
    )


def adjust_pronunciation_for_accent(score: float, detection: LanguageDetection) -> float:
    """Malaysian-English phonology (th → d/t, final-consonant reduction, vowel
    shifts) is regional variation, not error: pronunciation models trained on
    US/UK English under-score it, so apply a +5% allowance."""
    if detection.accent_type == "Malaysian English":
        return round(min(100.0, score * 1.05), 1)
    return score
