"""Rutas, pesos del scoring y ajustes generales."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    path = Path(os.getenv("JOBMATCH_DATA_DIR") or ROOT_DIR / "data")
    path.mkdir(parents=True, exist_ok=True)
    return path


USER_AGENT = "jobmatch/0.1 (+https://github.com/IgnacioSZ1904/jobmatch)"
HTTP_TIMEOUT = 20.0
HTTP_RETRIES = 2

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# Tipos de cambio fijos a EUR (suficiente para comparar salarios)
FX_TO_EUR = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "CHF": 1.05}

DEDUP_FUZZY_THRESHOLD = 90
DEDUP_WINDOW_DAYS = 30
EXCLUDED_WORD_PENALTY = 15


@dataclass(frozen=True)
class ScoreWeights:
    skills: float = 35
    semantic: float = 25
    seniority: float = 15
    location: float = 10
    salary: float = 10
    language: float = 5

    def as_dict(self) -> dict[str, float]:
        return dict(self.__dict__)


@dataclass
class Settings:
    weights: ScoreWeights = field(default_factory=ScoreWeights)

    @property
    def db_path(self) -> Path:
        return data_dir() / "jobmatch.db"

    @property
    def profile_path(self) -> Path:
        return data_dir() / "profile.yaml"

    @property
    def raw_dir(self) -> Path:
        return data_dir() / "raw"


settings = Settings()
