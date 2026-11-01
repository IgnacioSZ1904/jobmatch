"""Repositorio sobre SQLite (SQLModel)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, col, create_engine, select

from jobmatch.config import DEDUP_WINDOW_DAYS
from jobmatch.models import JobOffer, OfferScore, OfferState, OfferStatus, utcnow

# Campos que se actualizan si la oferta ya existía
_UPDATABLE = (
    "url",
    "title",
    "company",
    "description",
    "location_text",
    "country",
    "modality",
    "remote_scope",
    "seniority",
    "years_required",
    "skills",
    "salary_min",
    "salary_max",
    "contract_type",
    "languages",
    "published_at",
    "fetched_at",
)


@dataclass
class OfferRow:
    offer: JobOffer
    status: OfferStatus
    notes: str
    score: OfferScore | None


def make_engine(db_path: Path | None = None) -> Engine:
    if db_path is None:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return engine


class Repository:
    def __init__(self, engine: Engine):
        self.engine = engine

    # --- Ofertas -----------------------------------------------------------
    def get(self, offer_id: str) -> JobOffer | None:
        with Session(self.engine) as s:
            return s.get(JobOffer, offer_id)

    def upsert(self, offer: JobOffer) -> bool:
        """Inserta o actualiza por (source, source_id). Devuelve True si es nueva."""
        with Session(self.engine, expire_on_commit=False) as s:
            existing = s.get(JobOffer, offer.id)
            if existing:
                for name in _UPDATABLE:
                    setattr(existing, name, getattr(offer, name))
                if existing.description != offer.description:
                    existing.embedding = None
                s.add(existing)
                s.commit()
                return False
            s.add(offer)
            s.add(OfferState(offer_id=offer.id))
            s.commit()
            return True

    def recent_originals(self, days: int = DEDUP_WINDOW_DAYS) -> list[JobOffer]:
        since = utcnow() - timedelta(days=days)
        with Session(self.engine) as s:
            stmt = select(JobOffer).where(
                col(JobOffer.duplicate_of).is_(None), JobOffer.first_seen_at >= since
            )
            return list(s.exec(stmt))

    def mark_duplicate(self, offer_id: str, original_id: str) -> None:
        with Session(self.engine) as s:
            offer = s.get(JobOffer, offer_id)
            if offer:
                offer.duplicate_of = original_id
                s.add(offer)
                s.commit()

    def duplicates_of(self, offer_id: str) -> list[JobOffer]:
        with Session(self.engine) as s:
            return list(s.exec(select(JobOffer).where(JobOffer.duplicate_of == offer_id)))

    def all_offers(self, include_duplicates: bool = False) -> list[JobOffer]:
        with Session(self.engine) as s:
            stmt = select(JobOffer)
            if not include_duplicates:
                stmt = stmt.where(col(JobOffer.duplicate_of).is_(None))
            return list(s.exec(stmt))

    def set_embedding(self, offer_id: str, vector: bytes) -> None:
        with Session(self.engine) as s:
            offer = s.get(JobOffer, offer_id)
            if offer:
                offer.embedding = vector
                s.add(offer)
                s.commit()

    # --- Estado del usuario --------------------------------------------------
    def set_status(self, offer_id: str, status: OfferStatus, notes: str | None = None) -> None:
        with Session(self.engine) as s:
            state = s.get(OfferState, offer_id) or OfferState(offer_id=offer_id)
            state.status = status
            if notes is not None:
                state.notes = notes
            state.updated_at = utcnow()
            s.add(state)
            s.commit()

    # --- Puntuaciones --------------------------------------------------------
    def save_score(self, score: OfferScore) -> None:
        with Session(self.engine) as s:
            s.merge(score)
            s.commit()

    def unscored_ids(self, profile_hash: str) -> set[str]:
        with Session(self.engine) as s:
            scored = set(
                s.exec(select(OfferScore.offer_id).where(OfferScore.profile_hash == profile_hash))
            )
            ids = set(s.exec(select(JobOffer.id).where(col(JobOffer.duplicate_of).is_(None))))
            return ids - scored

    # --- Consulta para la UI -------------------------------------------------
    def rows(self) -> list[OfferRow]:
        with Session(self.engine) as s:
            stmt = (
                select(JobOffer, OfferState, OfferScore)
                .join(OfferState, OfferState.offer_id == JobOffer.id, isouter=True)
                .join(OfferScore, OfferScore.offer_id == JobOffer.id, isouter=True)
                .where(col(JobOffer.duplicate_of).is_(None))
            )
            return [
                OfferRow(
                    offer,
                    state.status if state else OfferStatus.NEW,
                    state.notes if state else "",
                    score,
                )
                for offer, state, score in s.exec(stmt)
            ]
