"""Extracción de tecnologías con una taxonomía de nombres canónicos y alias."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

TAXONOMY_PATH = Path(__file__).with_name("skills_taxonomy.yaml")


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    aliases: tuple[str, ...]


def _pattern(term: str) -> re.Pattern[str]:
    # Límites "de palabra" que funcionan con términos como c++, .net o node.js
    return re.compile(rf"(?<![\w.+#]){re.escape(term)}(?![\w+#]|\.\w)", re.IGNORECASE)


@lru_cache
def load_taxonomy(path: Path = TAXONOMY_PATH) -> tuple[Skill, ...]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return tuple(
        Skill(str(name).lower(), v.get("category", "other"), tuple(v.get("aliases", [])))
        for name, v in data.items()
    )


@lru_cache
def _compiled() -> tuple[tuple[str, tuple[re.Pattern[str], ...]], ...]:
    return tuple(
        (s.name, tuple(_pattern(t) for t in (s.name, *s.aliases))) for s in load_taxonomy()
    )


def skill_names() -> list[str]:
    return sorted(s.name for s in load_taxonomy())


def canonical(name: str) -> str:
    """Nombre canónico de un skill o alias; si no se conoce, el propio nombre."""
    key = name.strip().lower()
    for s in load_taxonomy():
        if key == s.name or key in s.aliases:
            return s.name
    return key


def extract_skills(*texts: str) -> list[str]:
    text = "\n".join(t for t in texts if t)
    found = [name for name, patterns in _compiled() if any(p.search(text) for p in patterns)]
    # "go" es muy ambiguo en inglés: solo cuenta si aparece "golang" o "Go " en mayúscula
    if "go" in found and not re.search(r"\bgolang\b|\bGo\b", text):
        found.remove("go")
    return found
