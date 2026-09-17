"""
Malaysian Language Support Layer
Handles: English, Bahasa Melayu, Code-switching (Manglish), Malaysian accents
This is a key FYP contribution — Malaysian-specific NLP processing.

Word-ratio detection is delegated to speech/lexicon.py's ~190-word list
(pronouns, verbs, connectives, everyday nouns/adjectives, tested against
pure-English/pure-Malay/mixed sample sentences) rather than duplicating a
separate, smaller keyword set here — one vetted list, reused everywhere the
app needs an English/Malay ratio.
"""
from dataclasses import dataclass

from app.ai.speech import lexicon

# Manglish discourse particles — checked separately from lexicon.py's word
# list because they signal *code-switching style*, not raw word count (a
# single "lah" flags Manglish even in an otherwise all-English sentence).
MANGLISH_PARTICLES = {
    "lah", "mah", "weh", "kan", "lor", "leh", "la", "wei",
    "one", "what", "also", "already", "got", "no need",
}

# Malaysian accent phoneme substitutions (for pronunciation scoring adjustment)
MY_ACCENT_SUBSTITUTIONS = {
    # Commonly reduced endings in Malaysian English
    "th → d/t": ["the", "this", "that", "there", "think", "three"],
    "final consonant reduction": ["and", "hand", "end", "find"],
    "vowel shifts": ["pen", "ten", "men"],
}


@dataclass
class LanguageDetectionResult:
    primary_language: str           # "en" | "ms" | "mixed"
    english_ratio: float            # 0–1
    malay_ratio: float              # 0–1
    is_code_switching: bool
    manglish_particles: list[str]
    detected_bm_words: list[str]
    accent_type: str                # "Malaysian English" | "Standard BM" | "Mixed"


def detect_language_and_accent(transcript: str) -> LanguageDetectionResult:
    """
    Detect language composition and code-switching in Malaysian speech.
    This drives adjusted pronunciation scoring (Malaysian accent allowances)
    and ASR model selection.
    """
    words = transcript.lower().split()

    bm_found = [w.strip(".,!?\"'") for w in words if w.strip(".,!?\"'") in lexicon.MALAY_WORDS]
    manglish_found = [w.strip(".,!?\"'") for w in words if w.strip(".,!?\"'") in MANGLISH_PARTICLES]

    en_ratio, bm_ratio = lexicon.estimate_language_ratio(transcript)
    is_code_switching = lexicon.is_code_switching(en_ratio, bm_ratio)
    is_manglish = len(manglish_found) > 0

    if bm_ratio > 0.7:
        primary = "ms"
        accent = "Standard BM"
    elif bm_ratio > 0.15 or is_manglish:
        primary = "mixed"
        accent = "Malaysian English"
    else:
        primary = "en"
        accent = "Malaysian English"

    return LanguageDetectionResult(
        primary_language=primary,
        english_ratio=round(en_ratio, 2),
        malay_ratio=round(bm_ratio, 2),
        is_code_switching=is_code_switching,
        manglish_particles=list(set(manglish_found)),
        detected_bm_words=list(set(bm_found)),
        accent_type=accent,
    )


def adjust_pronunciation_score_for_accent(
    base_score: float,
    language_result: LanguageDetectionResult,
) -> float:
    """
    Apply Malaysian accent allowance to pronunciation scores.
    Standard pronunciation models are trained on American/British English.
    Malaysian English has distinct phonological patterns that are NOT errors.
    """
    if language_result.accent_type == "Malaysian English":
        # Apply +5% tolerance for known Malaysian accent features
        adjusted = min(100, base_score * 1.05)
        return round(adjusted, 1)
    return base_score


def get_whisper_language_hint(detection: LanguageDetectionResult) -> str:
    """
    Return the language hint to pass to Whisper to improve ASR accuracy.
    Whisper supports 'ms' for Bahasa Melayu.
    """
    if detection.primary_language == "ms":
        return "ms"
    if detection.primary_language == "mixed":
        # Use English — Whisper handles code-switching better in English mode
        return "en"
    return "en"
