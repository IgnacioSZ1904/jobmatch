from jobmatch.connectors.arbeitnow import ArbeitnowConnector
from jobmatch.connectors.remotive import RemotiveConnector
from jobmatch.dedup import find_duplicate, normalize_company
from tests.conftest import load_fixture


def test_normalize_company():
    assert normalize_company("Acme Labs GmbH") == "acme labs"
    assert normalize_company("Cárnica S.L.") == "carnica"


def test_cross_source_duplicate():
    original = RemotiveConnector().to_offer(load_fixture("remotive.json")["jobs"][0])
    other = ArbeitnowConnector().to_offer(load_fixture("arbeitnow.json")["data"][0])
    unrelated = ArbeitnowConnector().to_offer(load_fixture("arbeitnow.json")["data"][1])
    assert find_duplicate(other, [original, unrelated]) is original
    assert find_duplicate(unrelated, [original]) is None
    # misma fuente: no es duplicado entre fuentes
    assert find_duplicate(original, [original]) is None
