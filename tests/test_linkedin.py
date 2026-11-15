from datetime import date
from pathlib import Path

from jobmatch.profile.linkedin import (
    experience_years,
    parse_linkedin_pdf,
    parse_linkedin_text,
)
from jobmatch.profile.model import Profile

FIXTURE = Path(__file__).parent / "fixtures" / "linkedin_es.txt"
TODAY = date(2026, 11, 15)


def test_parse_spanish_profile():
    result = parse_linkedin_text(FIXTURE.read_text(encoding="utf-8"), TODAY)
    f = result.fields
    assert result.warnings == []
    assert f["desired_title"] == "Backend Developer | Python · FastAPI · LLMs"
    assert f["city"] == "Málaga" and f["country"] == "España"
    skills = {s["name"]: s["level"] for s in f["skills"]}
    assert skills["python"] == 4 and skills["fastapi"] == 4 and skills["react"] == 4
    assert skills["postgresql"] == 3 and skills["docker"] == 3 and skills["django"] == 3
    assert skills["aws"] == 2  # solo aparece en certificaciones
    # marzo 2025 – noviembre 2026 sin contar el solape
    assert f["years_experience"] == 1.8
    assert f["seniority"] == "junior"
    assert f["languages"] == [{"code": "es", "level": "nativo"}, {"code": "en", "level": "B2"}]
    assert f["summary"].startswith("Ingeniero de software")
    assert {"backend", "ml"} <= set(f["roles"])
    # Lo importado es un perfil válido al combinarlo con los valores por defecto
    Profile.model_validate({**Profile().model_dump(mode="json"), **f})


def test_experience_years_english_and_overlaps():
    lines = ["January 2020 - December 2021 (2 years)", "June 2021 - Present", "2015 - 2016"]
    assert experience_years(lines, TODAY) == 8.9  # 2015–2016 + ene 2020 – nov 2026


def test_not_a_linkedin_pdf():
    result = parse_linkedin_text("Factura nº 123\nTotal: 40 €")
    assert result.warnings
    assert "skills" not in result.fields


def test_pdf_roundtrip(tmp_path):
    from reportlab.pdfgen import canvas

    path = tmp_path / "Profile.pdf"
    pdf = canvas.Canvas(str(path))
    y = 800
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        pdf.drawString(40, y, line)
        y -= 14
    pdf.save()
    result = parse_linkedin_pdf(path.read_bytes(), TODAY)
    assert result.fields["city"] == "Málaga"
    assert result.fields["years_experience"] == 1.8


def test_broken_pdf():
    assert parse_linkedin_pdf(b"not a pdf").warnings
