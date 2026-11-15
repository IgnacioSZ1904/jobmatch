"""Modelos de datos persistidos en SQLite (SQLModel)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, Column, LargeBinary
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class Modality(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"
    UNKNOWN = "unknown"


class RemoteScope(StrEnum):
    WORLDWIDE = "worldwide"
    EUROPE = "europe"
    SPAIN = "spain"
    OTHER = "other"
    UNKNOWN = "unknown"


class Seniority(StrEnum):
    INTERN = "intern"  # prácticas / beca
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    UNKNOWN = "unknown"


SENIORITY_LABELS = {
    "intern": "Prácticas",
    "junior": "Junior",
    "mid": "Mid",
    "senior": "Senior",
    "lead": "Lead",
    "unknown": "Sin indicar",
}


class OfferStatus(StrEnum):
    NEW = "new"
    SEEN = "seen"
    INTERESTING = "interesting"
    DISCARDED = "discarded"
    APPLIED = "applied"


def offer_id(source: str, source_id: str) -> str:
    return hashlib.sha1(f"{source}:{source_id}".encode()).hexdigest()[:16]


class JobOffer(SQLModel, table=True):
    id: str = Field(primary_key=True)
    source: str = Field(index=True)
    source_id: str
    url: str
    title: str
    company: str = ""
    description: str = ""
    location_text: str = ""
    country: str | None = None
    modality: Modality = Modality.UNKNOWN
    remote_scope: RemoteScope = RemoteScope.UNKNOWN
    seniority: Seniority = Seniority.UNKNOWN
    years_required: int | None = None
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    salary_min: float | None = None
    salary_max: float | None = None
    contract_type: str | None = None
    languages: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=utcnow)
    first_seen_at: datetime = Field(default_factory=utcnow)
    duplicate_of: str | None = Field(default=None, index=True)
    embedding: bytes | None = Field(default=None, sa_column=Column(LargeBinary))


class OfferState(SQLModel, table=True):
    offer_id: str = Field(primary_key=True, foreign_key="joboffer.id")
    status: OfferStatus = OfferStatus.NEW
    notes: str = ""
    updated_at: datetime = Field(default_factory=utcnow)


class OfferScore(SQLModel, table=True):
    offer_id: str = Field(primary_key=True, foreign_key="joboffer.id")
    profile_hash: str = Field(index=True)
    total: float
    filtered: bool = False
    breakdown: dict = Field(default_factory=dict, sa_column=Column(JSON))
