"""Casos de uso de la aplicación. La UI solo habla con este módulo."""

from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from jobmatch.config import settings
from jobmatch.connectors import Connector, SearchQuery, all_connectors
from jobmatch.connectors.base import save_raw
from jobmatch.dedup import find_duplicate
from jobmatch.models import JobOffer, OfferScore, OfferStatus, offer_id
from jobmatch.normalize.offer import enrich
from jobmatch.profile.model import Profile
from jobmatch.scoring import semantic
from jobmatch.scoring.scorer import score_offer
from jobmatch.storage import OfferRow, Repository

log = logging.getLogger(__name__)
SOURCE_TIMEOUT = 90


@dataclass
class SourceReport:
    fetched: int = 0
    new: int = 0
    updated: int = 0
    duplicates: int = 0
    skipped: int = 0
    error: str | None = None


@dataclass
class RefreshReport:
    sources: dict[str, SourceReport] = field(default_factory=dict)
    scored: int = 0

    @property
    def new(self) -> int:
        return sum(s.new for s in self.sources.values())

    @property
    def duplicates(self) -> int:
        return sum(s.duplicates for s in self.sources.values())


def build_query(profile: Profile) -> SearchQuery:
    top = sorted(profile.skills, key=lambda s: (not s.must_have, -s.level))[:5]
    return SearchQuery(keywords=[s.name for s in top], roles=profile.roles, country="es")


def _fetch(connector: Connector, query: SearchQuery, raw_dir: Path | None) -> list:
    raws = connector.fetch(query)
    if raw_dir is not None:
        save_raw(raw_dir, connector.name, raws)
    return raws


def refresh_offers(
    repo: Repository,
    profile: Profile,
    connectors: list[Connector] | None = None,
    embedder: semantic.Embedder | None = None,
    raw_dir: Path | None = None,
    on_progress=None,
) -> RefreshReport:
    """Descarga, normaliza, deduplica, guarda y puntúa las ofertas."""
    connectors = [c for c in (connectors or all_connectors()) if c.is_configured()]
    query = build_query(profile)
    report = RefreshReport()

    with ThreadPoolExecutor(max_workers=max(1, len(connectors))) as pool:
        futures = {pool.submit(_fetch, c, query, raw_dir): c for c in connectors}
        for future in as_completed(futures, timeout=SOURCE_TIMEOUT):
            connector = futures[future]
            src = report.sources.setdefault(connector.name, SourceReport())
            try:
                raws = future.result()
            except Exception as exc:  # una fuente caída no detiene las demás
                log.exception("Fallo en %s", connector.name)
                src.error = f"{type(exc).__name__}: {exc}"
                continue
            src.fetched = len(raws)
            _store(repo, connector, raws, src)
            if on_progress:
                on_progress(connector.name, src)

    report.scored = score_pending(repo, profile, embedder)
    return report


def _store(repo: Repository, connector: Connector, raws: list, src: SourceReport) -> None:
    candidates = repo.recent_originals()
    for raw in raws:
        try:
            offer = connector.to_offer(raw)
        except Exception:  # oferta mal formada: se salta
            log.warning("Oferta mal formada en %s", connector.name, exc_info=True)
            src.skipped += 1
            continue
        is_new = repo.upsert(offer)
        if not is_new:
            src.updated += 1
            continue
        src.new += 1
        original = find_duplicate(offer, candidates)
        if original:
            repo.mark_duplicate(offer.id, original.id)
            src.duplicates += 1
        else:
            candidates.append(offer)


def score_pending(
    repo: Repository,
    profile: Profile,
    embedder: semantic.Embedder | None = None,
    force: bool = False,
) -> int:
    """Puntúa las ofertas sin puntuación para el perfil actual (o todas si `force`)."""
    profile_hash = profile.fingerprint()
    pending = repo.unscored_ids(profile_hash)
    offers = [o for o in repo.all_offers() if force or o.id in pending]
    if not offers:
        return 0
    similarities = _similarities(repo, profile, offers, embedder) if embedder else {}
    for offer in offers:
        result = score_offer(profile, offer, similarities.get(offer.id))
        repo.save_score(
            OfferScore(
                offer_id=offer.id,
                profile_hash=profile_hash,
                total=result.total,
                filtered=result.filtered,
                breakdown=result.to_dict(),
            )
        )
    return len(offers)


def _similarities(
    repo: Repository, profile: Profile, offers: list[JobOffer], embedder: semantic.Embedder
) -> dict[str, float]:
    missing = [o for o in offers if o.embedding is None]
    if missing:
        vectors = embedder.embed([semantic.offer_text(o) for o in missing])
        for offer, vec in zip(missing, vectors, strict=True):
            offer.embedding = semantic.pack(vec)
            repo.set_embedding(offer.id, offer.embedding)
    [profile_vec] = embedder.embed([profile.semantic_text() or " "])
    return {
        o.id: semantic.rescale(semantic.cosine(profile_vec, semantic.unpack(o.embedding)), embedder)
        for o in offers
    }


def import_manual_offer(
    repo: Repository,
    profile: Profile,
    *,
    url: str,
    title: str,
    description: str,
    company: str = "",
    location: str = "",
    embedder: semantic.Embedder | None = None,
) -> tuple[JobOffer, bool]:
    """Añade una oferta pegada a mano (p. ej. de LinkedIn) y la puntúa.

    Devuelve la oferta y si es nueva. Si coincide con otra ya guardada de otra
    fuente, se marca como duplicada de ella.
    """
    url, title, description = url.strip(), title.strip(), description.strip()
    if not title or not description:
        raise ValueError("Hacen falta al menos el título y el texto de la oferta.")
    source_id = url or hashlib.sha1(f"{title}\n{description}".encode()).hexdigest()[:16]
    offer = JobOffer(
        id=offer_id("manual", source_id),
        source="manual",
        source_id=source_id,
        url=url,
        title=title,
        company=company.strip(),
        description=description,
        location_text=location.strip(),
    )
    offer = enrich(offer)
    is_new = repo.upsert(offer)
    if is_new:
        original = find_duplicate(offer, repo.recent_originals())
        if original:
            repo.mark_duplicate(offer.id, original.id)
    score_pending(repo, profile, embedder, force=not is_new)
    return offer, is_new


def list_offers(
    repo: Repository,
    profile: Profile,
    *,
    min_score: float = 0,
    sources: list[str] | None = None,
    modalities: list[str] | None = None,
    statuses: list[OfferStatus] | None = None,
    only_new: bool = False,
    filtered: bool = False,
) -> list[OfferRow]:
    """Ofertas puntuadas con el perfil actual, ordenadas por puntuación."""
    profile_hash = profile.fingerprint()
    rows = []
    for row in repo.rows():
        if row.score is None or row.score.profile_hash != profile_hash:
            continue
        if row.score.filtered != filtered or row.score.total < min_score:
            continue
        if sources and row.offer.source not in sources:
            continue
        if modalities and row.offer.modality not in modalities:
            continue
        if statuses and row.status not in statuses:
            continue
        if only_new and row.status != OfferStatus.NEW:
            continue
        rows.append(row)
    return sorted(rows, key=lambda r: r.score.total, reverse=True)


def set_status(
    repo: Repository, offer_id: str, status: OfferStatus, notes: str | None = None
) -> None:
    repo.set_status(offer_id, status, notes)


def default_repository() -> Repository:
    from jobmatch.storage import make_engine

    return Repository(make_engine(settings.db_path))
