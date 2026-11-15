"""Idiomas requeridos por la oferta."""

from __future__ import annotations

import re

from jobmatch.normalize.text import fold

_PATTERNS = {
    "en": re.compile(
        r"\b(fluent|proficient|good|advanced|native)\s+english\b|\bingles\b"
        r"|\benglish\s+(c1|b2|level|required|speaker)"
    ),
    "de": re.compile(r"\b(german|deutsch|aleman)\b"),
    "fr": re.compile(r"\b(french|frances)\b"),
    "es": re.compile(r"\b(spanish|castellano|espanol)\b"),
}


def detect_languages(text: str) -> list[str]:
    body = fold(text)
    return [code for code, pattern in _PATTERNS.items() if pattern.search(body)]
