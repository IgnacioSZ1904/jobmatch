"""Nivel y años de experiencia pedidos en la oferta."""

from __future__ import annotations

import re

from jobmatch.models import Seniority
from jobmatch.normalize.text import fold

_LEVELS: list[tuple[Seniority, re.Pattern[str]]] = [
    (Seniority.LEAD, re.compile(r"\b(lead|principal|staff|head of|tech lead|lider)\b")),
    (Seniority.SENIOR, re.compile(r"\b(senior|sr\.?|snr)\b")),
    (Seniority.JUNIOR, re.compile(r"\b(junior|jr\.?|entry[- ]level|graduate|trainee|intern)\b")),
    (Seniority.MID, re.compile(r"\b(mid|middle|intermediate|semi[- ]?senior|ssr)\b")),
]
_YEARS = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years?|yrs?|anos?)"
    r"(?:\s+(?:of\s+)?(?:\w+\s+){0,2}(?:experience|experiencia))?"
)


def years_required(text: str) -> int | None:
    values = [int(m.group(1)) for m in _YEARS.finditer(fold(text))]
    values = [v for v in values if 0 < v <= 20]
    return min(values) if values else None


def level_from_years(years: float) -> Seniority:
    if years < 2:
        return Seniority.JUNIOR
    if years < 5:
        return Seniority.MID
    if years < 9:
        return Seniority.SENIOR
    return Seniority.LEAD


def detect_seniority(title: str, description: str = "") -> tuple[Seniority, int | None]:
    years = years_required(description) or years_required(title)
    folded_title = fold(title)
    for level, pattern in _LEVELS:
        if pattern.search(folded_title):
            return level, years
    if years is not None:
        return level_from_years(years), years
    folded_desc = fold(description[:600])
    for level, pattern in _LEVELS:
        if pattern.search(folded_desc):
            return level, years
    return Seniority.UNKNOWN, years
