"""Plain-text rules shared by the analysis, the feedback and the deck tools."""

import re

_WORD = re.compile(r"\b[\w'’-]+\b")


def words(text: str) -> list[str]:
    """Words as a listener hears them: "don't" and "well-known" are one word each."""
    return _WORD.findall(text)


def count_words(text: str) -> int:
    return len(words(text))


def invented_terms(text: str, source: str) -> list[str]:
    """Names and numbers in `text` that never appear in `source`: capitalised words that
    don't start a sentence (tools, companies, places) and any figure."""
    known = {w.lower() for w in re.findall(r"[\w']+", source)}
    found = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        tokens = re.findall(r"[\w'%]+", sentence)
        for i, w in enumerate(tokens):
            name = i > 0 and w[:1].isupper() and len(w) > 2 and w != "I"
            if (name or any(ch.isdigit() for ch in w)) and w.lower().rstrip("%") not in known and w.lower() not in known:
                found.append(w)
    return list(dict.fromkeys(found))
