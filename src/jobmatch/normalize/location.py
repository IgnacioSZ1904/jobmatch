"""Modalidad (remoto/híbrido/presencial), alcance del remoto y país."""

from __future__ import annotations

import re

from jobmatch.models import Modality, RemoteScope
from jobmatch.normalize.text import fold

_HYBRID = re.compile(r"\b(hybrid|hibrido|semi[- ]?presencial)\b")
_REMOTE = re.compile(r"\b(remote|remoto|teletrabajo|work from home|wfh|anywhere|100% remot)")
_ONSITE = re.compile(r"\b(on[- ]?site|presencial|in[- ]office)\b")

_SPAIN = re.compile(r"\b(spain|espana|madrid|barcelona|malaga|valencia|sevilla|bilbao)\b")
_EUROPE = re.compile(
    r"\b(europe|eu|emea|cet|european|germany|deutschland|berlin|france|portugal|"
    r"netherlands|uk|united kingdom|ireland|italy|poland)\b"
)
_WORLDWIDE = re.compile(r"\b(worldwide|anywhere|global|any location)\b")
_OTHER = re.compile(r"\b(usa|us only|united states|canada|latam|americas|india|apac|brazil)\b")

_COUNTRIES = {
    "spain": "España",
    "espana": "España",
    "madrid": "España",
    "barcelona": "España",
    "malaga": "España",
    "valencia": "España",
    "sevilla": "España",
    "bilbao": "España",
    "germany": "Alemania",
    "deutschland": "Alemania",
    "berlin": "Alemania",
    "munich": "Alemania",
    "hamburg": "Alemania",
    "france": "Francia",
    "portugal": "Portugal",
    "netherlands": "Países Bajos",
    "uk": "Reino Unido",
    "united kingdom": "Reino Unido",
    "ireland": "Irlanda",
    "usa": "EE. UU.",
    "united states": "EE. UU.",
}


def detect_modality(location: str, text: str = "", remote_flag: bool | None = None) -> Modality:
    loc, body = fold(location), fold(text[:1500])
    if _HYBRID.search(loc) or _HYBRID.search(body):
        return Modality.HYBRID
    if remote_flag or _REMOTE.search(loc):
        return Modality.REMOTE
    if _ONSITE.search(loc) or _ONSITE.search(body):
        return Modality.ONSITE
    if _REMOTE.search(body):
        return Modality.REMOTE
    return Modality.UNKNOWN if remote_flag is None else Modality.ONSITE


def detect_remote_scope(location: str) -> RemoteScope:
    loc = fold(location)
    if not loc.strip():
        return RemoteScope.UNKNOWN
    if _SPAIN.search(loc):
        return RemoteScope.SPAIN
    if _WORLDWIDE.search(loc):
        return RemoteScope.WORLDWIDE
    if _EUROPE.search(loc):
        return RemoteScope.EUROPE
    if _OTHER.search(loc):
        return RemoteScope.OTHER
    return RemoteScope.UNKNOWN


def detect_country(location: str) -> str | None:
    loc = fold(location)
    for key, country in _COUNTRIES.items():
        if re.search(rf"\b{re.escape(key)}\b", loc):
            return country
    return None
