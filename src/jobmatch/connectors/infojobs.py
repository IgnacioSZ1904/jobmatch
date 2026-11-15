"""InfoJobs: ofertas en España mediante su API oficial.

Requiere registrar una aplicación gratuita en https://developer.infojobs.net y
poner INFOJOBS_CLIENT_ID e INFOJOBS_CLIENT_SECRET en `.env`. Sin ellas la fuente
aparece como desactivada.
"""

from __future__ import annotations

import os
import re

import httpx

from jobmatch.config import HTTP_TIMEOUT, USER_AGENT
from jobmatch.connectors.base import RawOffer, SearchQuery, get_json, parse_datetime
from jobmatch.models import JobOffer, Modality, RemoteScope, offer_id
from jobmatch.normalize.offer import enrich
from jobmatch.normalize.text import fold, html_to_text

URL = "https://api.infojobs.net/api/9/offer"
CATEGORY = "informatica-telecomunicaciones"
MAX_RESULTS = 50
MAX_QUERIES = 3

_CONTRACTS = {
    "indefinido": "indefinido",
    "de duracion determinada": "temporal",
    "temporal": "temporal",
    "formativo": "prácticas",
    "practicas": "prácticas",
    "autonomo": "freelance",
    "freelance": "freelance",
}


def _value(raw: RawOffer, key: str) -> str:
    """InfoJobs devuelve muchos campos como {"id": ..., "value": ...}."""
    item = raw.get(key)
    if isinstance(item, dict):
        return str(item.get("value") or "")
    return str(item or "")


def _modality(teleworking: str) -> Modality:
    text = fold(teleworking)
    if "solo teletrabajo" in text or "remoto" in text:
        return Modality.REMOTE
    if "parcial" in text or "hibrido" in text:
        return Modality.HYBRID
    if "presencial" in text or "sin teletrabajo" in text:
        return Modality.ONSITE
    return Modality.UNKNOWN


def _years(experience: str) -> int | None:
    match = re.search(r"(\d+)", experience)
    return int(match.group(1)) if match else None


class InfoJobsConnector:
    name = "infojobs"
    requires_credentials = True

    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self.client_id = client_id or os.getenv("INFOJOBS_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("INFOJOBS_CLIENT_SECRET", "")

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def fetch(self, query: SearchQuery) -> list[RawOffer]:
        terms = query.keywords[:MAX_QUERIES] or query.roles[:1] or ["desarrollador"]
        offers: dict[str, RawOffer] = {}
        with httpx.Client(
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            auth=(self.client_id, self.client_secret),
        ) as client:
            for term in terms:
                params = {"q": term, "category": CATEGORY, "maxResults": MAX_RESULTS}
                payload = get_json(URL, params, client=client)
                for item in payload.get("offers", []):
                    offers[str(item["id"])] = item
        return list(offers.values())

    def to_offer(self, raw: RawOffer) -> JobOffer:
        modality = _modality(_value(raw, "teleworking"))
        salary_min, salary_max = _value(raw, "salaryMin"), _value(raw, "salaryMax")
        salary_text = ""
        if salary_min or salary_max:
            salary_text = f"{salary_min} - {salary_max} € {_value(raw, 'salaryPeriod')}"
        location = ", ".join(p for p in (raw.get("city"), _value(raw, "province")) if p)
        description = html_to_text(raw.get("requirementMin") or raw.get("description") or "")
        offer = JobOffer(
            id=offer_id(self.name, str(raw["id"])),
            source=self.name,
            source_id=str(raw["id"]),
            url=raw["link"],
            title=raw["title"].strip(),
            company=_value(raw, "author")
            if not isinstance(raw.get("author"), dict)
            else str(raw["author"].get("name") or ""),
            description=description,
            location_text=location,
            country="España",
            modality=modality,
            remote_scope=RemoteScope.SPAIN if modality == Modality.REMOTE else RemoteScope.UNKNOWN,
            years_required=_years(_value(raw, "experienceMin")),
            contract_type=_CONTRACTS.get(fold(_value(raw, "contractType"))),
            published_at=parse_datetime(raw.get("published")),
        )
        offer = enrich(offer, salary_text=salary_text)
        if not offer.languages:
            offer.languages = ["es"]
        return offer
