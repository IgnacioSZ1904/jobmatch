import pytest

from jobmatch.models import Modality, RemoteScope, Seniority
from jobmatch.normalize.languages import detect_languages
from jobmatch.normalize.location import detect_country, detect_modality, detect_remote_scope
from jobmatch.normalize.salary import parse_salary
from jobmatch.normalize.seniority import detect_seniority
from jobmatch.normalize.skills import canonical, extract_skills
from jobmatch.normalize.text import html_to_text


def test_extract_skills_with_aliases_and_symbols():
    text = "Buscamos dev con Postgres, JS, Node.js, C++ y .NET. Valorable k8s."
    skills = extract_skills(text)
    for s in ["postgresql", "javascript", "node.js", "c++", ".net", "kubernetes"]:
        assert s in skills
    assert "java" not in skills


def test_extract_skills_ignores_ambiguous_go():
    assert "go" not in extract_skills("You will go above and beyond")
    assert "go" in extract_skills("Backend in Go and gRPC")


def test_canonical():
    assert canonical("Postgres") == "postgresql"
    assert canonical("unknown-tech") == "unknown-tech"


@pytest.mark.parametrize(
    ("title", "desc", "level", "years"),
    [
        ("Senior Python Engineer", "", Seniority.SENIOR, None),
        ("Desarrollador Junior", "", Seniority.JUNIOR, None),
        ("Tech Lead", "", Seniority.LEAD, None),
        ("Backend Developer", "Mínimo 3 años de experiencia", Seniority.MID, 3),
        ("Backend Developer", "5+ years of experience with Java", Seniority.SENIOR, 5),
        ("Backend Developer", "Great team", Seniority.UNKNOWN, None),
    ],
)
def test_detect_seniority(title, desc, level, years):
    assert detect_seniority(title, desc) == (level, years)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("40k-50k €", (40000, 50000)),
        ("35.000 € brutos/año", (35000, 35000)),
        ("$120k", (110400, 110400)),
        ("3.000 € al mes", (36000, 36000)),
        ("", (None, None)),
        ("Competitive", (None, None)),
    ],
)
def test_parse_salary(text, expected):
    assert parse_salary(text) == expected


def test_modality_and_scope():
    assert detect_modality("Madrid (híbrido)") == Modality.HYBRID
    assert detect_modality("Remote - Europe") == Modality.REMOTE
    assert detect_modality("Málaga", "Trabajo presencial en oficina") == Modality.ONSITE
    assert detect_modality("Berlin", remote_flag=False) == Modality.ONSITE
    assert detect_remote_scope("Worldwide") == RemoteScope.WORLDWIDE
    assert detect_remote_scope("EU timezones") == RemoteScope.EUROPE
    assert detect_remote_scope("USA Only") == RemoteScope.OTHER
    assert detect_remote_scope("Spain") == RemoteScope.SPAIN
    assert detect_country("Málaga, Andalucía") == "España"


def test_languages_and_html():
    assert detect_languages("Fluent English required. German is a plus") == ["en", "de"]
    assert html_to_text("<p>Hola &amp; adiós</p><ul><li>uno</li></ul>") == "Hola & adiós\n\nuno"


@pytest.mark.parametrize(
    ("title", "desc", "level"),
    [
        ("Prácticas Desarrollo Web", "", Seniority.INTERN),
        ("Becario/a de desarrollo", "", Seniority.INTERN),
        ("Software Engineering Internship", "", Seniority.INTERN),
        ("Backend Developer", "Aplicamos buenas prácticas de código limpio", Seniority.UNKNOWN),
    ],
)
def test_detect_internship(title, desc, level):
    assert detect_seniority(title, desc)[0] == level


def test_monthly_salary_infojobs_style():
    assert parse_salary("800 € - 800 € Bruto/mes") == (9600, 9600)
