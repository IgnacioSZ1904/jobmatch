import pytest

from jobmatch.connectors.arbeitnow import ArbeitnowConnector
from jobmatch.connectors.remoteok import RemoteOKConnector
from jobmatch.connectors.remotive import RemotiveConnector
from jobmatch.models import Modality, RemoteScope, Seniority
from tests.conftest import load_fixture


def test_remotive_to_offer():
    raw = load_fixture("remotive.json")["jobs"][0]
    offer = RemotiveConnector().to_offer(raw)
    assert offer.source == "remotive"
    assert offer.company == "Acme Labs"
    assert offer.modality == Modality.REMOTE
    assert offer.remote_scope == RemoteScope.EUROPE
    assert offer.seniority == Seniority.SENIOR
    assert offer.years_required == 5
    assert {"python", "django", "postgresql", "docker", "kubernetes", "aws"} <= set(offer.skills)
    assert offer.salary_min == 82800 and offer.salary_max == 110400
    assert offer.contract_type == "indefinido"
    assert "en" in offer.languages
    assert "<p>" not in offer.description


def test_arbeitnow_to_offer_and_broken_entry():
    raws = load_fixture("arbeitnow.json")["data"]
    conn = ArbeitnowConnector()
    remote = conn.to_offer(raws[0])
    onsite = conn.to_offer(raws[1])
    assert remote.modality == Modality.REMOTE
    assert onsite.modality == Modality.ONSITE
    assert onsite.country == "Alemania"
    assert {"vue", "node.js", "mongodb"} <= set(onsite.skills)
    with pytest.raises(KeyError):
        conn.to_offer(raws[2])


def test_remoteok_skips_legal_notice(monkeypatch):
    payload = load_fixture("remoteok.json")
    monkeypatch.setattr("jobmatch.connectors.remoteok.get_json", lambda *a, **k: payload)
    conn = RemoteOKConnector()
    raws = conn.fetch(None)
    assert len(raws) == 1
    offer = conn.to_offer(raws[0])
    assert offer.title == "Machine Learning Engineer (LLM)"
    assert offer.remote_scope == RemoteScope.WORLDWIDE
    assert offer.salary_max == 92000
    assert {"python", "pytorch", "llm", "fastapi", "langchain"} <= set(offer.skills)


def test_infojobs_to_offer():
    from jobmatch.connectors.infojobs import InfoJobsConnector

    raws = load_fixture("infojobs.json")["offers"]
    conn = InfoJobsConnector("id", "secret")
    junior, practicas, remoto = (conn.to_offer(r) for r in raws)
    assert junior.company == "Soluciones Andaluzas S.L."
    assert junior.modality == Modality.HYBRID and junior.seniority == Seniority.JUNIOR
    assert (junior.salary_min, junior.salary_max) == (24000, 30000)
    assert junior.years_required == 1 and junior.contract_type == "indefinido"
    assert {"python", "django", "postgresql"} <= set(junior.skills)
    assert practicas.seniority == Seniority.INTERN and practicas.contract_type == "prácticas"
    assert practicas.modality == Modality.ONSITE and practicas.salary_max == 9600
    assert remoto.modality == Modality.REMOTE and remoto.remote_scope == RemoteScope.SPAIN
    assert remoto.seniority == Seniority.MID and remoto.salary_max is None


def test_infojobs_disabled_without_credentials(monkeypatch):
    from jobmatch.connectors.infojobs import InfoJobsConnector

    monkeypatch.delenv("INFOJOBS_CLIENT_ID", raising=False)
    monkeypatch.delenv("INFOJOBS_CLIENT_SECRET", raising=False)
    assert not InfoJobsConnector().is_configured()


def test_infojobs_fetch_uses_basic_auth(monkeypatch):
    from jobmatch.connectors import infojobs
    from jobmatch.connectors.base import SearchQuery

    calls = []

    def fake_get_json(url, params, client):
        calls.append((params["q"], client.auth))
        return load_fixture("infojobs.json")

    monkeypatch.setattr(infojobs, "get_json", fake_get_json)
    raws = infojobs.InfoJobsConnector("id", "secret").fetch(
        SearchQuery(keywords=["python", "react"])
    )
    assert len(raws) == 3  # sin repetidos entre búsquedas
    assert [q for q, _ in calls] == ["python", "react"]
    assert calls[0][1] is not None
