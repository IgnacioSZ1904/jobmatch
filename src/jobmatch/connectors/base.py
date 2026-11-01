"""Interfaz común de los conectores y utilidades HTTP."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import httpx

from jobmatch.config import HTTP_RETRIES, HTTP_TIMEOUT, USER_AGENT
from jobmatch.models import JobOffer

log = logging.getLogger(__name__)

RawOffer = dict[str, Any]


@dataclass
class SearchQuery:
    """Búsqueda derivada del perfil."""

    keywords: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    country: str = "es"


class Connector(Protocol):
    name: str
    requires_credentials: bool

    def is_configured(self) -> bool: ...
    def fetch(self, query: SearchQuery) -> list[RawOffer]: ...
    def to_offer(self, raw: RawOffer) -> JobOffer: ...


def get_json(url: str, params: dict | None = None, client: httpx.Client | None = None) -> Any:
    """GET con timeout, User-Agent propio y reintentos con espera exponencial ante 5xx/429."""
    own_client = client is None
    client = client or httpx.Client(
        timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    )
    try:
        for attempt in range(HTTP_RETRIES + 1):
            resp = client.get(url, params=params)
            retryable = resp.status_code == 429 or resp.status_code >= 500
            if retryable and attempt < HTTP_RETRIES:
                time.sleep(2**attempt)
                continue
            resp.raise_for_status()
            return resp.json()
    finally:
        if own_client:
            client.close()


def save_raw(raw_dir: Path, source: str, payload: Any) -> Path:
    """Guarda la respuesta cruda para depurar y para crear fixtures."""
    folder = raw_dir / source
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now(UTC):%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, int | float):
            return datetime.fromtimestamp(value, UTC)
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, OSError):
        return None
