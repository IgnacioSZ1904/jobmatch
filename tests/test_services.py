import httpx

from jobmatch.connectors.arbeitnow import ArbeitnowConnector
from jobmatch.connectors.remoteok import RemoteOKConnector
from jobmatch.connectors.remotive import RemotiveConnector
from jobmatch.models import OfferStatus
from jobmatch.scoring.semantic import HashingEmbedder
from jobmatch.services import list_offers, refresh_offers, score_pending, set_status
from tests.conftest import load_fixture


class Fake:
    """Envuelve un conector real devolviendo una fixture en lugar de llamar a la red."""

    def __init__(self, inner, payload):
        self.inner, self.payload = inner, payload
        self.name, self.requires_credentials = inner.name, False

    def is_configured(self):
        return True

    def fetch(self, query):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    def to_offer(self, raw):
        return self.inner.to_offer(raw)


def connectors(fail_remoteok=False):
    remoteok = [x for x in load_fixture("remoteok.json") if "id" in x]
    return [
        Fake(RemotiveConnector(), load_fixture("remotive.json")["jobs"]),
        Fake(ArbeitnowConnector(), load_fixture("arbeitnow.json")["data"]),
        Fake(RemoteOKConnector(), httpx.ConnectError("down") if fail_remoteok else remoteok),
    ]


def test_refresh_end_to_end(repo, profile, tmp_path):
    report = refresh_offers(repo, profile, connectors(), HashingEmbedder(), raw_dir=tmp_path)
    assert report.new == 6
    assert report.duplicates == 1
    assert report.sources["arbeitnow"].skipped == 1
    assert report.scored == 5
    assert (tmp_path / "remotive").exists()

    ranked = list_offers(repo, profile)
    filtered = list_offers(repo, profile, filtered=True)
    assert len(ranked) + len(filtered) == 5
    totals = [r.score.total for r in ranked]
    assert totals == sorted(totals, reverse=True)
    assert ranked[0].offer.title == "Senior Python Backend Engineer"
    assert all(r.score.breakdown["components"] for r in ranked)
    # PHP en USA queda filtrada; la de Hamburgo presencial también
    assert {r.offer.company for r in filtered} == {"Old Web Inc", "Nordwerk GmbH"}

    # segunda ejecución: nada nuevo, solo actualizaciones
    again = refresh_offers(repo, profile, connectors(), HashingEmbedder())
    assert again.new == 0 and again.scored == 0
    assert again.sources["remotive"].updated == 3


def test_source_failure_does_not_stop_others(repo, profile):
    report = refresh_offers(repo, profile, connectors(fail_remoteok=True))
    assert "ConnectError" in report.sources["remoteok"].error
    assert report.sources["remotive"].new == 3


def test_status_and_rescore_on_profile_change(repo, profile):
    refresh_offers(repo, profile, connectors())
    top = list_offers(repo, profile)[0]
    set_status(repo, top.offer.id, OfferStatus.INTERESTING, "Escribir al CTO")
    row = next(r for r in list_offers(repo, profile) if r.offer.id == top.offer.id)
    assert row.status == OfferStatus.INTERESTING and row.notes == "Escribir al CTO"
    assert len(list_offers(repo, profile, only_new=True)) == len(list_offers(repo, profile)) - 1

    profile.min_salary = 200000
    assert list_offers(repo, profile) == []  # puntuaciones del perfil anterior no valen
    assert score_pending(repo, profile) == 5
    assert list_offers(repo, profile)


def test_import_manual_offer(repo, profile):
    from jobmatch.services import import_manual_offer

    offer, is_new = import_manual_offer(
        repo,
        profile,
        url="https://www.linkedin.com/jobs/view/123",
        title="Junior Python Developer",
        company="Startup Málaga",
        location="Málaga (híbrido)",
        description="Buscamos perfil junior con Python, FastAPI y PostgreSQL.",
    )
    assert is_new and offer.source == "manual"
    assert offer.modality == "hybrid" and offer.seniority == "junior"
    row = list_offers(repo, profile)[0]
    assert row.offer.id == offer.id and row.score.total > 60

    # Pegarla otra vez actualiza en vez de duplicar
    _, again = import_manual_offer(
        repo,
        profile,
        url="https://www.linkedin.com/jobs/view/123",
        title="Junior Python Developer",
        description="Texto actualizado con Python",
    )
    assert not again and len(list_offers(repo, profile)) == 1


def test_import_manual_requires_text(repo, profile):
    import pytest

    from jobmatch.services import import_manual_offer

    with pytest.raises(ValueError):
        import_manual_offer(repo, profile, url="", title="", description="")
