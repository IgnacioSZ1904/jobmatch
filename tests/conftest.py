import json
from pathlib import Path

import pytest

from jobmatch.models import Modality, Seniority
from jobmatch.profile.model import LanguageSkill, Profile, SkillLevel
from jobmatch.storage import Repository, make_engine

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def repo() -> Repository:
    return Repository(make_engine(None))


def make_profile() -> Profile:
    return Profile(
        roles=["backend"],
        desired_title="Backend Developer Python",
        years_experience=1,
        seniority=Seniority.JUNIOR,
        skills=[
            SkillLevel(name="python", level=4, must_have=True),
            SkillLevel(name="fastapi", level=3),
            SkillLevel(name="postgresql", level=3),
            SkillLevel(name="docker", level=2),
            SkillLevel(name="react", level=2),
        ],
        learning=["kubernetes"],
        modalities=[Modality.REMOTE, Modality.HYBRID],
        timezones=["europe", "worldwide"],
        min_salary=28000,
        languages=[LanguageSkill(code="es", level="nativo"), LanguageSkill(code="en", level="B2")],
        excluded_words=["php"],
        excluded_companies=["cárnica sa"],
        summary="Busco un puesto junior de backend con Python, APIs y sistemas con LLM.",
    )


@pytest.fixture
def profile() -> Profile:
    return make_profile()
