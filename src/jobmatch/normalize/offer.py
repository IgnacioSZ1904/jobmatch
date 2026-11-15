"""Rellena los campos derivados de una oferta a partir de su texto."""

from __future__ import annotations

from jobmatch.models import JobOffer, Modality, RemoteScope, Seniority
from jobmatch.normalize.languages import detect_languages
from jobmatch.normalize.location import detect_country, detect_modality, detect_remote_scope
from jobmatch.normalize.salary import parse_salary
from jobmatch.normalize.seniority import detect_seniority, level_from_years
from jobmatch.normalize.skills import canonical, extract_skills


def enrich(
    offer: JobOffer,
    tags: list[str] | None = None,
    salary_text: str | None = None,
    remote_flag: bool | None = None,
) -> JobOffer:
    """Completa skills, seniority, salario, modalidad, país e idiomas si faltan."""
    found = extract_skills(offer.title, offer.description)
    tag_skills = [canonical(t) for t in tags or []]
    known = set(extract_skills(" ".join(tags or [])))
    offer.skills = sorted(set(found) | {t for t in tag_skills if t in known})

    if offer.seniority == Seniority.UNKNOWN:
        level, years = detect_seniority(offer.title, offer.description)
        offer.years_required = offer.years_required or years
        if level == Seniority.UNKNOWN and offer.years_required:
            level = level_from_years(offer.years_required)
        offer.seniority = level

    if offer.salary_min is None and offer.salary_max is None:
        offer.salary_min, offer.salary_max = parse_salary(salary_text)

    if offer.modality == Modality.UNKNOWN:
        offer.modality = detect_modality(offer.location_text, offer.description, remote_flag)
    if offer.remote_scope == RemoteScope.UNKNOWN and offer.modality == Modality.REMOTE:
        offer.remote_scope = detect_remote_scope(offer.location_text)
    offer.country = offer.country or detect_country(offer.location_text)
    offer.languages = offer.languages or detect_languages(offer.description)
    return offer
