"""
Word-level English/Malay ratio estimation.

This is a lexicon lookup, not a trained language-ID model — every word in a
transcript is checked against a list of common Bahasa Malaysia / colloquial
Manglish tokens; anything not on the list defaults to English. That's a real
limitation (proper nouns, rare Malay words, and code-switched compounds like
"makan-makan session" will misclassify), documented here rather than implied
away. It's good enough to drive the two ratio bars already on the Assessment
page's Language & Accent Detection card, and to flag likely code-switching —
it is NOT a substitute for the audio-based classifier
(malaya_speech.language_detection) if per-segment accuracy ever matters more
than a whole-transcript estimate.
"""

import re

# Common Bahasa Malaysia function words, pronouns, particles, and everyday
# vocabulary, plus the colloquial Manglish discourse particles that show up
# constantly in transcribed Malaysian speech ("lah", "lor", "kan"...). Kept
# lowercase; matching is done on lowercased, punctuation-stripped tokens.
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
    "sahaja", "saja", "lah", "lor", "kan", "eh", "wah", "aiyo", "aiya", "kan",
    # everyday nouns
    "orang", "hari", "masa", "waktu", "sekarang", "nanti", "esok", "semalam",
    "tadi", "rumah", "sekolah", "keluarga", "kawan", "kerja", "duit", "wang",
    "makanan", "air",
    # adjectives / adverbs
    "betul", "salah", "baik", "bagus", "cantik", "hebat", "teruk", "susah",
    "senang", "mudah", "cepat", "lambat", "besar", "kecil", "banyak", "byk",
    "sikit", "sangat", "memang", "pasti", "mesti", "sepatutnya", "patut",
    "sebenarnya", "sebenar", "sekali", "agak", "hampir", "hanya", "cuma",
    "semua", "setiap", "masing", "sendiri", "bersama",
    # more everyday verbs/nouns that came up as gaps in testing
    "rasa", "dulu", "fikiran", "pendapat", "pandangan", "cara", "jalan",
    "tempat", "benda", "perkara", "hal", "isu", "masalah", "keputusan",
    "jawapan", "soalan", "cadangan", "ialah", "adalah", "merupakan",
    "menjadi", "akan", "telah", "sedang", "pernah", "kerap", "selalu",
    "biasa", "jarang", "kadang", "kadangkala", "antara", "tentang",
    "mengenai", "terhadap", "oleh", "seperti",
}

_TOKEN_RE = re.compile(r"[a-zA-Z']+")


def estimate_language_ratio(text: str) -> tuple[float, float]:
    """Rough (english_ratio, malay_ratio) for a transcript, word-count based.

    Returns (1.0, 0.0) for empty/no-alphabetic-token input rather than
    dividing by zero.
    """
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    if not tokens:
        return 1.0, 0.0
    malay = sum(1 for t in tokens if t in MALAY_WORDS)
    english = len(tokens) - malay
    total = len(tokens)
    return round(english / total, 4), round(malay / total, 4)


def is_code_switching(english_ratio: float, malay_ratio: float, threshold: float = 0.15) -> bool:
    """Both languages present in meaningful proportion, not just a stray borrowed word."""
    return english_ratio >= threshold and malay_ratio >= threshold
