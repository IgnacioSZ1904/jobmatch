"""Conectores de fuentes de ofertas."""

from jobmatch.connectors.arbeitnow import ArbeitnowConnector
from jobmatch.connectors.base import Connector, RawOffer, SearchQuery
from jobmatch.connectors.infojobs import InfoJobsConnector
from jobmatch.connectors.remoteok import RemoteOKConnector
from jobmatch.connectors.remotive import RemotiveConnector


def all_connectors() -> list[Connector]:
    return [RemotiveConnector(), ArbeitnowConnector(), RemoteOKConnector(), InfoJobsConnector()]


__all__ = ["Connector", "RawOffer", "SearchQuery", "all_connectors"]
