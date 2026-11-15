"""Importación del perfil desde el PDF de LinkedIn ("Más → Guardar en PDF").

LinkedIn no ofrece una API pública de perfiles, pero el PDF que genera tiene
siempre las mismas secciones (en español o en inglés). Aquí se extrae lo que
sirve para prerrellenar el cuestionario; el usuario lo revisa después.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date
from typing import BinaryIO

from jobmatch.normalize.seniority import level_from_years
from jobmatch.normalize.skills import canonical, extract_skills, skill_names
from jobmatch.normalize.text import fold

SECTIONS = {
    "contact": ["contactar", "contact", "contacto"],
    "top_skills": ["aptitudes principales", "top skills"],
    "languages": ["languages", "idiomas"],
    "certifications": ["certifications", "certificaciones", "licencias y certificaciones"],
    "honors": ["honors-awards", "honors & awards", "reconocimientos y premios"],
    "publications": ["publications", "publicaciones"],
    "summary": ["extracto", "summary", "acerca de", "about"],
    "experience": ["experiencia", "experience"],
    "education": ["educacion", "education", "formacion"],
}
_HEADING = {alias: key for key, aliases in SECTIONS.items() for alias in aliases}

_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_PRESENT = r"(?:present|actualidad|presente|hoy)"
_MONTH_YEAR = r"(?:([a-z]+)\s+(?:de\s+)?)?(\d{4})"
_RANGE = re.compile(rf"{_MONTH_YEAR}\s*[-–]\s*(?:{_PRESENT}|{_MONTH_YEAR})")

_LANG_NAMES = {
    "espanol": "es",
    "castellano": "es",
    "spanish": "es",
    "ingles": "en",
    "english": "en",
    "frances": "fr",
    "french": "fr",
    "aleman": "de",
    "german": "de",
    "italiano": "it",
    "italian": "it",
    "portugues": "pt",
    "portuguese": "pt",
    "catalan": "ca",
}
_LANG_LEVELS = [
    ("native", "nativo"),
    ("nativ", "nativo"),
    ("bilingual", "nativo"),
    ("bilingue", "nativo"),
    ("full professional", "C1"),
    ("completa", "C1"),
    ("professional working", "B2"),
    ("profesional", "B2"),
    ("limited", "B1"),
    ("limitada", "B1"),
    ("elementary", "A2"),
    ("basica", "A2"),
    ("elemental", "A2"),
]
_ROLE_WORDS = {
    "fullstack": ["full stack", "full-stack", "fullstack"],
    "backend": ["backend", "back-end", "back end"],
    "frontend": ["frontend", "front-end", "front end"],
    "data": ["data engineer", "data scientist", "data analyst", "datos"],
    "devops": ["devops", "sre", "platform engineer", "cloud engineer"],
    "mobile": ["mobile", "android", "ios", "movil"],
    "qa": ["qa", "tester", "testing", "quality assurance"],
    "ml": ["machine learning", "ml engineer", "inteligencia artificial", "ia", "ai", "llm"],
}
_NOISE = re.compile(r"^page \d+ of \d+$|^pagina \d+ de \d+$")


@dataclass
class LinkedInImport:
    """Campos de `Profile` detectados y avisos para mostrar al usuario."""

    fields: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def pdf_to_text(data: bytes | BinaryIO) -> str:
    from pypdf import PdfReader

    stream = io.BytesIO(data) if isinstance(data, bytes) else data
    return "\n".join(page.extract_text() or "" for page in PdfReader(stream).pages)


def parse_linkedin_pdf(data: bytes | BinaryIO, today: date | None = None) -> LinkedInImport:
    try:
        text = pdf_to_text(data)
    except Exception as exc:  # PDF dañado o cifrado
        return LinkedInImport(warnings=[f"No se ha podido leer el PDF: {exc}"])
    return parse_linkedin_text(text, today)


def split_sections(text: str) -> tuple[list[str], dict[str, list[str]]]:
    """Devuelve las líneas sin sección (cabecera) y las líneas de cada sección."""
    header: list[str] = []
    sections: dict[str, list[str]] = {}
    current: list[str] = header
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _NOISE.match(fold(line)):
            continue
        key = _HEADING.get(fold(line))
        if key:
            current = sections.setdefault(key, [])
        else:
            current.append(line)
    return header, sections


def experience_years(lines: list[str], today: date | None = None) -> float:
    """Años de experiencia uniendo los intervalos de fechas (sin contar solapes)."""
    today = today or date.today()
    intervals = []
    for m in _RANGE.finditer(fold("\n".join(lines))):
        m1, y1, m2, y2 = m.groups()
        start = (int(y1), _MONTHS.get(m1 or "", 1))
        end = (int(y2), _MONTHS.get(m2 or "", 12)) if y2 else (today.year, today.month)
        a, b = start[0] * 12 + start[1] - 1, end[0] * 12 + end[1]
        if b > a:
            intervals.append((a, b))
    months, last_end = 0, -1
    for a, b in sorted(intervals):
        a = max(a, last_end)
        if b > a:
            months += b - a
            last_end = b
    return round(months / 12, 1)


def _languages(lines: list[str]) -> list[dict]:
    found: dict[str, str] = {}
    for line in lines:
        folded = fold(line)
        name = folded.split("(")[0].strip()
        code = _LANG_NAMES.get(name)
        if not code:
            continue
        level = next((lvl for key, lvl in _LANG_LEVELS if key in folded), "B2")
        found[code] = level
    return [{"code": c, "level": lvl} for c, lvl in found.items()]


def _roles(text: str) -> list[str]:
    folded = fold(text)
    roles = [
        role
        for role, words in _ROLE_WORDS.items()
        if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", folded) for w in words)
    ]
    if "fullstack" in roles:
        roles = [r for r in roles if r not in ("backend", "frontend")] + ["backend", "frontend"]
    return list(dict.fromkeys(roles))


def _identity(header: list[str]) -> tuple[str, str]:
    """(titular, ubicación) a partir de la cabecera: nombre, titular, ubicación."""
    lines = [
        line
        for line in header
        if "@" not in line
        and "linkedin.com" not in line
        and not re.search(r"\(linkedin\)|\(mobile\)|\(movil\)|\+?\d[\d ]{7,}", fold(line))
    ]
    if len(lines) >= 3:
        return lines[-2], lines[-1]
    if len(lines) == 2:
        return lines[-1], ""
    return "", ""


def parse_linkedin_text(text: str, today: date | None = None) -> LinkedInImport:
    header, sections = split_sections(text)
    result = LinkedInImport()
    fields = result.fields

    if "experience" not in sections:
        result.warnings.append(
            "No parece un PDF de perfil de LinkedIn: no se encuentra la sección Experiencia."
        )

    # El nombre, titular y ubicación van justo antes del extracto o la experiencia.
    # pypdf suele sacar la barra lateral (contacto, aptitudes…) primero, así que
    # la cabecera útil son las últimas líneas de la sección que precede.
    before_main = header
    for key in ("publications", "honors", "certifications", "languages", "top_skills", "contact"):
        if key in sections:
            before_main = sections[key]
            break
    headline, location = _identity(before_main)
    if headline:
        fields["desired_title"] = headline
    if location:
        fields["city"] = location.split(",")[0].strip()
        if "," in location:
            fields["country"] = location.split(",")[-1].strip()

    top = [canonical(s) for s in sections.get("top_skills", [])]
    known = set(skill_names())
    experience = sections.get("experience", [])
    used_at_work = set(extract_skills("\n".join(experience)))
    mentioned = extract_skills(text)
    skills = []
    for name in dict.fromkeys([t for t in top if t in known] + mentioned):
        level = 4 if name in top else 3 if name in used_at_work else 2
        skills.append({"name": name, "level": level, "must_have": False})
    if skills:
        fields["skills"] = skills

    years = experience_years(experience, today)
    if experience:
        fields["years_experience"] = years
        fields["seniority"] = level_from_years(years).value

    languages = _languages(sections.get("languages", []))
    if languages:
        fields["languages"] = languages

    summary = " ".join(sections.get("summary", []))
    if summary:
        fields["summary"] = summary[:800]

    roles = _roles(f"{headline}\n{summary}")
    if roles:
        fields["roles"] = roles
    return result
