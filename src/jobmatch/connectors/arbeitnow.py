"""Arbeitnow: ofertas en Europa (muchas remotas). https://www.arbeitnow.com/api/job-board-api"""

from __future__ import annotations

from jobmatch.connectors.base import RawOffer, SearchQuery, get_json, parse_datetime
from jobmatch.models import JobOffer, offer_id
from jobmatch.normalize.offer import enrich
from jobmatch.normalize.text import html_to_text

URL = "https://www.arbeitnow.com/api/job-board-api"
PAGES = 3


class ArbeitnowConnector:
    name = "arbeitnow"
    requires_credentials = False

    def is_configured(self) -> bool:
        return True

    def fetch(self, query: SearchQuery) -> list[RawOffer]:
        jobs: list[RawOffer] = []
        for page in range(1, PAGES + 1):
            payload = get_json(URL, {"page": page})
            jobs.extend(payload.get("data", []))
            if not payload.get("links", {}).get("next"):
                break
        return jobs

    def to_offer(self, raw: RawOffer) -> JobOffer:
        job_types = [t.lower() for t in raw.get("job_types") or []]
        contract = "temporal" if any("intern" in t or "part" in t for t in job_types) else None
        offer = JobOffer(
            id=offer_id(self.name, raw["slug"]),
            source=self.name,
            source_id=raw["slug"],
            url=raw["url"],
            title=raw["title"].strip(),
            company=(raw.get("company_name") or "").strip(),
            description=html_to_text(raw.get("description")),
            location_text=raw.get("location") or "",
            contract_type=contract,
            published_at=parse_datetime(raw.get("created_at")),
        )
        return enrich(offer, tags=raw.get("tags"), remote_flag=bool(raw.get("remote")))
