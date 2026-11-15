"""Carga y guardado del perfil en YAML."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from jobmatch.config import settings
from jobmatch.profile.model import Profile

log = logging.getLogger(__name__)


def load_profile(path: Path | None = None) -> Profile | None:
    """Devuelve el perfil, o None si no existe o es inválido."""
    path = path or settings.profile_path
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return Profile.model_validate(data)
    except (yaml.YAMLError, ValidationError) as exc:
        log.warning("Perfil inválido en %s: %s", path, exc)
        return None


def load_raw_profile(path: Path | None = None) -> dict:
    """Datos crudos del YAML, para recuperar lo posible si el perfil es inválido."""
    path = path or settings.profile_path
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def save_profile(profile: Profile, path: Path | None = None) -> Path:
    path = path or settings.profile_path
    path.parent.mkdir(parents=True, exist_ok=True)
    data = profile.model_dump(mode="json")
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
