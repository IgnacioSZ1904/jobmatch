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
