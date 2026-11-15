"""Combina filtros, reglas y similitud semántica en una puntuación 0–100."""

from __future__ import annotations

from dataclasses import dataclass, field

from jobmatch.config import EXCLUDED_WORD_PENALTY, ScoreWeights, settings
from jobmatch.models import JobOffer
from jobmatch.profile.model import Profile
from jobmatch.scoring import rules

LABELS = {
    "skills": "Skills",
    "semantic": "Semántico",
    "seniority": "Seniority",
    "location": "Modalidad",
    "salary": "Salario",
    "language": "Idioma",
}


@dataclass
class ScoreResult:
    total: float
    filtered_reason: str | None = None
    components: dict[str, dict] = field(default_factory=dict)
    penalties: list[str] = field(default_factory=list)

    @property
    def filtered(self) -> bool:
        return self.filtered_reason is not None

    def to_dict(self) -> dict:
        return {
            "components": self.components,
            "penalties": self.penalties,
            "filtered_reason": self.filtered_reason,
        }

    def summary(self) -> str:
        parts = [
            f"{LABELS[k]} {c['points']:.0f}/{c['max']:.0f}" for k, c in self.components.items()
        ]
        return " · ".join(parts)


def score_offer(
    profile: Profile,
    offer: JobOffer,
    semantic: float | None = None,
    weights: ScoreWeights | None = None,
) -> ScoreResult:
    """`semantic` es la similitud ya reescalada a 0–1 (None → neutro)."""
    weights = weights or settings.weights
    values = {
        "skills": rules.skills_component(profile, offer),
        "semantic": (rules.NEUTRAL, "Sin embeddings")
        if semantic is None
        else (semantic, f"Similitud {semantic:.0%}"),
        "seniority": rules.seniority_component(profile, offer),
        "location": rules.location_component(profile, offer),
        "salary": rules.salary_component(profile, offer),
        "language": rules.language_component(profile, offer),
    }
    w = weights.as_dict()
    components = {
        name: {"points": round(value * w[name], 1), "max": w[name], "detail": detail}
        for name, (value, detail) in values.items()
    }
    total = sum(c["points"] for c in components.values())
    found = rules.excluded_words_found(profile, offer)
    penalties = [f"Contiene '{word}' (−{EXCLUDED_WORD_PENALTY})" for word in found]
    total = max(0.0, total - EXCLUDED_WORD_PENALTY * len(found))
    return ScoreResult(
        total=round(min(100.0, total), 1),
        filtered_reason=rules.hard_filter(profile, offer),
        components=components,
        penalties=penalties,
    )
