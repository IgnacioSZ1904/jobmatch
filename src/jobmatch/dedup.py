"""Deduplicación entre fuentes por empresa + título con similitud difusa."""

from __future__ import annotations

import re
from collections.abc import Iterable

from rapidfuzz import fuzz

from jobmatch.config import DEDUP_FUZZY_THRESHOLD
from jobmatch.models import JobOffer
from jobmatch.normalize.text import fold

_COMPANY_SUFFIX = re.compile(
    r"\b(s\.?l\.?u?|s\.?a\.?|gmbh|ltd|limited|inc|llc|corp|corporation|co|bv|ag)\b\.?"
)
_PUNCT = re.compile(r"[^\w\s]")
_SPACES = re.compile(r"\s+")


def normalize_company(name: str) -> str:
    text = _COMPANY_SUFFIX.sub(" ", fold(name))
    return _SPACES.sub(" ", _PUNCT.sub(" ", text)).strip()


def normalize_title(title: str) -> str:
    text = re.sub(r"\(.*?\)|\[.*?\]", " ", fold(title))
    return _SPACES.sub(" ", _PUNCT.sub(" ", text)).strip()


def dedup_key(offer: JobOffer) -> str:
    return f"{normalize_company(offer.company)} | {normalize_title(offer.title)}"


def find_duplicate(
    offer: JobOffer, candidates: Iterable[JobOffer], threshold: int = DEDUP_FUZZY_THRESHOLD
) -> JobOffer | None:
    """Devuelve la oferta original de otra fuente de la que `offer` es duplicada."""
    company = normalize_company(offer.company)
    title = normalize_title(offer.title)
    if not company or not title:
        return None
    best: tuple[float, JobOffer] | None = None
    for other in candidates:
        if other.id == offer.id or other.source == offer.source or other.duplicate_of:
            continue
        if fuzz.ratio(company, normalize_company(other.company)) < threshold:
            continue
        score = fuzz.token_sort_ratio(title, normalize_title(other.title))
        if score >= threshold and (best is None or score > best[0]):
            best = (score, other)
    return best[1] if best else None
