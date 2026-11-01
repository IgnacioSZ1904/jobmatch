"""Remotive: ofertas remotas, API JSON pública. https://remotive.com/api/remote-jobs"""

from __future__ import annotations

from jobmatch.connectors.base import RawOffer, SearchQuery, get_json, parse_datetime
from jobmatch.models import JobOffer, Modality, offer_id
from jobmatch.normalize.location import detect_remote_scope
from jobmatch.normalize.offer import enrich
from jobmatch.normalize.text import html_to_text

URL = "https://remotive.com/api/remote-jobs"
_CONTRACTS = {
    "full_time": "indefinido",
    "contract": "freelance",
    "freelance": "freelance",
    "part_time": "temporal",
    "internship": "temporal",
}


class RemotiveConnector:
    name = "remotive"
    requires_credentials = False

    def is_configured(self) -> bool:
        return True

    def fetch(self, query: SearchQuery) -> list[RawOffer]:
        params = {"category": "software-dev", "limit": 200}
        return get_json(URL, params).get("jobs", [])

    def to_offer(self, raw: RawOffer) -> JobOffer:
        location = raw.get("candidate_required_location") or ""
        offer = JobOffer(
            id=offer_id(self.name, str(raw["id"])),
            source=self.name,
            source_id=str(raw["id"]),
            url=raw["url"],
            title=raw["title"].strip(),
            company=(raw.get("company_name") or "").strip(),
            description=html_to_text(raw.get("description")),
            location_text=location,
            modality=Modality.REMOTE,
            remote_scope=detect_remote_scope(location),
            contract_type=_CONTRACTS.get(raw.get("job_type") or ""),
            published_at=parse_datetime(raw.get("publication_date")),
        )
        return enrich(offer, tags=raw.get("tags"), salary_text=raw.get("salary"))
