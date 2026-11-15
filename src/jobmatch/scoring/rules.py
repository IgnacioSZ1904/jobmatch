"""Reglas del scoring. Cada componente devuelve (valor 0–1, explicación)."""

from __future__ import annotations

import re

from jobmatch.models import JobOffer, Modality, RemoteScope, Seniority
from jobmatch.normalize.text import fold
from jobmatch.profile.model import Profile

Component = tuple[float, str]
_LEVELS = [Seniority.JUNIOR, Seniority.MID, Seniority.SENIOR, Seniority.LEAD]
NEUTRAL = 0.5


# --- Filtros duros --------------------------------------------------------------


def hard_filter(profile: Profile, offer: JobOffer) -> str | None:
    """Motivo por el que la oferta queda fuera del ranking, o None."""
    if offer.modality != Modality.UNKNOWN and offer.modality not in profile.modalities:
        return f"Modalidad no aceptada ({offer.modality.value})"
    company = fold(offer.company)
    for excluded in profile.excluded_companies:
        if excluded and fold(excluded) in company:
            return f"Empresa excluida ({offer.company})"
    if offer.modality == Modality.REMOTE:
        reason = _remote_scope_filter(profile, offer.remote_scope)
        if reason:
            return reason
    return None


def _remote_scope_filter(profile: Profile, scope: RemoteScope) -> str | None:
    if scope in (RemoteScope.UNKNOWN, RemoteScope.SPAIN):
        return None
    if scope == RemoteScope.OTHER:
        return "Remoto restringido a otra zona"
    if not profile.accepts_foreign_remote:
        return "Remoto con empresa extranjera no aceptado"
    zones = set(profile.timezones)
    if scope == RemoteScope.EUROPE and not zones & {"europe", "worldwide"}:
        return "Remoto Europa no aceptado"
    if scope == RemoteScope.WORLDWIDE and "worldwide" not in zones and "europe" not in zones:
        return "Remoto mundial no aceptado"
    return None


# --- Penalizaciones -------------------------------------------------------------


def excluded_words_found(profile: Profile, offer: JobOffer) -> list[str]:
    text = fold(f"{offer.title}\n{offer.description}")
    return [
        w for w in profile.excluded_words if re.search(rf"(?<!\w){re.escape(fold(w))}(?!\w)", text)
    ]


# --- Componentes ponderados -----------------------------------------------------


def skills_component(profile: Profile, offer: JobOffer) -> Component:
    required = set(offer.skills)
    if not required:
        return NEUTRAL, "La oferta no menciona tecnologías reconocibles"
    user = profile.skill_map
    matched = sorted(required & user.keys())
    missing = sorted(required - user.keys())
    possible = gained = 0.0
    for name in required:
        skill = user.get(name)
        weight = 2.0 if skill and skill.must_have else 1.0
        possible += weight
        if skill:
            gained += weight * (0.5 + skill.level / 10)  # nivel 1 → 0.6, nivel 5 → 1.0
    learning = sorted(required & set(profile.learning) - set(matched))
    value = min(1.0, gained / possible + 0.05 * len(learning))
    parts = []
    if matched:
        parts.append("✔ " + ", ".join(matched))
    if missing:
        parts.append("✘ " + ", ".join(missing))
    if learning:
        parts.append("📚 " + ", ".join(learning))
    return value, " · ".join(parts)


def seniority_component(profile: Profile, offer: JobOffer) -> Component:
    if offer.seniority != Seniority.UNKNOWN:
        diff = abs(_LEVELS.index(offer.seniority) - _LEVELS.index(profile.seniority))
        value = {0: 1.0, 1: 0.5}.get(diff, 0.0)
        detail = f"Pide {offer.seniority.value}, tú {profile.seniority.value}"
        if offer.years_required:
            detail += f" ({offer.years_required}+ años)"
        return value, detail
    if offer.years_required:
        gap = offer.years_required - profile.years_experience
        value = 1.0 if gap <= 0 else 0.5 if gap <= 2 else 0.0
        return value, f"Pide {offer.years_required}+ años, tienes {profile.years_experience:g}"
    return NEUTRAL, "Nivel no indicado"


def location_component(profile: Profile, offer: JobOffer) -> Component:
    if offer.modality == Modality.UNKNOWN:
        return NEUTRAL, "Modalidad no indicada"
    if offer.modality not in profile.modalities:
        return 0.0, f"{offer.modality.value} no aceptada"
    preferred = profile.modalities[0]
    value = 1.0 if offer.modality == preferred else 0.8
    detail = offer.modality.value
    if offer.modality == Modality.REMOTE and offer.remote_scope != RemoteScope.UNKNOWN:
        detail += f" ({offer.remote_scope.value})"
    elif offer.location_text:
        detail += f" ({offer.location_text})"
    return value, detail


def salary_component(profile: Profile, offer: JobOffer) -> Component:
    top = offer.salary_max or offer.salary_min
    if top is None:
        return NEUTRAL, "Sin salario publicado"
    rng = f"{(offer.salary_min or top) / 1000:.0f}–{top / 1000:.0f}k €"
    if not profile.min_salary:
        return NEUTRAL, rng
    value = 1.0 if top >= profile.min_salary else top / profile.min_salary
    return value, f"{rng} (mínimo {profile.min_salary / 1000:.0f}k)"


def language_component(profile: Profile, offer: JobOffer) -> Component:
    required = set(offer.languages)
    if not required:
        return 1.0, "Sin requisitos de idioma"
    spoken = {lang.code for lang in profile.languages}
    met = required & spoken
    value = len(met) / len(required)
    missing = sorted(required - spoken)
    detail = "Pide " + ", ".join(sorted(required))
    if missing:
        detail += " (te falta " + ", ".join(missing) + ")"
    return value, detail
