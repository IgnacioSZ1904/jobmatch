"""Perfil del candidato, validado con pydantic."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field, field_validator

from jobmatch.models import Modality, Seniority

ROLES = ["backend", "frontend", "fullstack", "data", "devops", "mobile", "qa", "ml"]
CONTRACTS = ["indefinido", "freelance", "temporal"]
LANGUAGE_LEVELS = ["A2", "B1", "B2", "C1", "C2", "nativo"]

# Escala de dominio de una tecnología: (nombre corto, qué implica)
SKILL_LEVELS: dict[int, tuple[str, str]] = {
    1: ("Básico", "Conozco los conceptos o he seguido tutoriales; necesito ayuda constante."),
    2: ("Principiante", "La he usado en clase, prácticas o proyectos pequeños (p. ej. el TFG)."),
    3: ("Autónomo", "La uso en proyectos reales sin ayuda y resuelvo los problemas habituales."),
    4: ("Avanzado", "Aplico buenas prácticas, testing y rendimiento; reviso código de otros."),
    5: ("Experto", "Diseño soluciones complejas, conozco sus internos y enseño a otros."),
}
MUST_HAVE_HELP = "Tecnología central para ti: en las ofertas que la piden cuenta el doble."


def skill_level_label(level: int) -> str:
    return f"{level} · {SKILL_LEVELS[level][0]}"


def parse_skill_level_label(label: str | int) -> int:
    return int(str(label).split("·")[0].strip())


class SkillLevel(BaseModel):
    name: str
    level: int = Field(3, ge=1, le=5)
    must_have: bool = False

    @field_validator("name")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()


class LanguageSkill(BaseModel):
    code: str  # "es", "en", ...
    level: str = "B2"

    @field_validator("code")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.strip().lower()


class Profile(BaseModel):
    roles: list[str] = Field(default_factory=list)
    desired_title: str = ""
    years_experience: float = Field(0, ge=0, le=50)
    seniority: Seniority = Seniority.JUNIOR
    skills: list[SkillLevel] = Field(default_factory=list)
    learning: list[str] = Field(default_factory=list)
    city: str = ""
    country: str = "España"
    modalities: list[Modality] = Field(default_factory=lambda: [Modality.REMOTE])
    accepts_foreign_remote: bool = True
    timezones: list[str] = Field(default_factory=lambda: ["europe"])
    min_salary: float | None = None
    contracts: list[str] = Field(default_factory=lambda: ["indefinido"])
    languages: list[LanguageSkill] = Field(
        default_factory=lambda: [LanguageSkill(code="es", level="nativo")]
    )
    excluded_words: list[str] = Field(default_factory=list)
    excluded_companies: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator("learning", "excluded_words", "excluded_companies", "roles")
    @classmethod
    def _clean_list(cls, v: list[str]) -> list[str]:
        return [x.strip().lower() for x in v if x and x.strip()]

    @property
    def skill_map(self) -> dict[str, SkillLevel]:
        return {s.name: s for s in self.skills}

    def semantic_text(self) -> str:
        """Texto que representa al perfil para los embeddings."""
        parts = [self.summary, self.desired_title, " ".join(self.roles)]
        parts.append(" ".join(s.name for s in self.skills))
        return ". ".join(p for p in parts if p)

    def fingerprint(self) -> str:
        """Hash estable: si cambia, hay que recalcular las puntuaciones."""
        raw = json.dumps(self.model_dump(mode="json"), sort_keys=True)
        return hashlib.sha1(raw.encode()).hexdigest()[:12]
