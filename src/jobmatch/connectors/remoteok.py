"""RemoteOK: ofertas remotas, API JSON pública. https://remoteok.com/api

Sus condiciones exigen atribución: la UI enlaza a la oferta original en RemoteOK.
"""

from __future__ import annotations

from jobmatch.connectors.base import RawOffer, SearchQuery, get_json, parse_datetime
from jobmatch.models import JobOffer, Modality, offer_id
from jobmatch.normalize.location import detect_remote_scope
from jobmatch.normalize.offer import enrich
from jobmatch.normalize.salary import to_eur
from jobmatch.normalize.text import html_to_text

URL = "https://remoteok.com/api"
ATTRIBUTION = "Ofertas de Remote OK (remoteok.com)"


class RemoteOKConnector:
    name = "remoteok"
    requires_credentials = False

    def is_configured(self) -> bool:
        return True

    def fetch(self, query: SearchQuery) -> list[RawOffer]:
        payload = get_json(URL)
        # El primer elemento es el aviso legal, no una oferta
        return [item for item in payload if isinstance(item, dict) and "id" in item]

    def to_offer(self, raw: RawOffer) -> JobOffer:
        location = raw.get("location") or ""
        offer = JobOffer(
            id=offer_id(self.name, str(raw["id"])),
            source=self.name,
            source_id=str(raw["id"]),
            url=raw.get("url") or raw.get("apply_url") or "",
            title=(raw.get("position") or "").strip(),
            company=(raw.get("company") or "").strip(),
            description=html_to_text(raw.get("description")),
            location_text=location,
            modality=Modality.REMOTE,
            remote_scope=detect_remote_scope(location),
            salary_min=to_eur(raw.get("salary_min") or None, "USD"),
            salary_max=to_eur(raw.get("salary_max") or None, "USD"),
            published_at=parse_datetime(raw.get("epoch") or raw.get("date")),
        )
        return enrich(offer, tags=raw.get("tags"))
