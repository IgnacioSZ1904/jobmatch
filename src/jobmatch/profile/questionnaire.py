"""Definición declarativa del cuestionario de perfil.

La UI (Streamlit hoy, React mañana) recorre estos pasos y pinta cada pregunta
según su `kind`. Las claves `field` coinciden con los campos de `Profile`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from jobmatch.models import Modality, Seniority
from jobmatch.profile.model import CONTRACTS, LANGUAGE_LEVELS, ROLES

Kind = Literal[
    "multiselect", "select", "text", "textarea", "number", "bool", "tags", "skills", "languages"
]


@dataclass(frozen=True)
class Question:
    field: str
    label: str
    kind: Kind
    options: list[str] = field(default_factory=list)
    help: str = ""


@dataclass(frozen=True)
class Step:
    title: str
    questions: list[Question]


STEPS: list[Step] = [
    Step(
        "Rol",
        [
            Question("roles", "Roles objetivo", "multiselect", ROLES),
            Question(
                "desired_title",
                "Título del puesto deseado",
                "text",
                help="Ej.: Backend Developer Python",
            ),
        ],
    ),
    Step(
        "Experiencia",
        [
            Question("years_experience", "Años de experiencia total", "number"),
            Question(
                "seniority", "Nivel", "select", [s.value for s in Seniority if s != "unknown"]
            ),
        ],
    ),
    Step(
        "Habilidades",
        [
            Question("skills", "Tecnologías (nivel 1–5, marca las imprescindibles)", "skills"),
            Question("learning", "Tecnologías que quieres aprender", "tags"),
        ],
    ),
    Step(
        "Ubicación",
        [
            Question("city", "Ciudad de residencia", "text"),
            Question("country", "País", "text"),
            Question(
                "modalities",
                "Modalidades aceptadas",
                "multiselect",
                [m.value for m in Modality if m != "unknown"],
            ),
            Question(
                "accepts_foreign_remote", "¿Aceptas remoto con empresas de fuera de España?", "bool"
            ),
            Question(
                "timezones",
                "Zonas de remoto aceptadas",
                "multiselect",
                ["spain", "europe", "worldwide"],
            ),
        ],
    ),
    Step(
        "Condiciones",
        [
            Question("min_salary", "Salario mínimo bruto anual (EUR)", "number"),
            Question("contracts", "Tipo de contrato", "multiselect", CONTRACTS),
        ],
    ),
    Step(
        "Idiomas",
        [
            Question("languages", "Idiomas y nivel", "languages", LANGUAGE_LEVELS),
        ],
    ),
    Step(
        "Exclusiones",
        [
            Question(
                "excluded_words",
                "Palabras o tecnologías a evitar",
                "tags",
                help="Ej.: php, consultora, cárnica",
            ),
            Question("excluded_companies", "Empresas a excluir", "tags"),
        ],
    ),
    Step(
        "Resumen",
        [
            Question(
                "summary",
                "Describe en 2–3 frases lo que buscas",
                "textarea",
                help="Es el texto principal para la similitud semántica.",
            ),
        ],
    ),
]
