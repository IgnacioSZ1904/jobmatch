"""Similitud semántica perfil ↔ oferta mediante embeddings.

`SentenceTransformerEmbedder` usa el modelo multilingüe local (extra `semantic`).
`HashingEmbedder` es un respaldo sin dependencias (bolsa de palabras con hashing),
útil en tests y si no se ha instalado sentence-transformers.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from array import array
from typing import Protocol

from jobmatch.config import EMBEDDING_MODEL
from jobmatch.models import JobOffer
from jobmatch.normalize.text import fold

log = logging.getLogger(__name__)


class Embedder(Protocol):
    name: str
    # Rango típico de similitudes coseno del modelo, para reescalar a 0–1
    low: float
    high: float

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    name = "hashing"
    low, high = 0.0, 0.5
    _token = re.compile(r"[a-z0-9+#.]{2,}")

    def __init__(self, dim: int = 512):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in self._token.findall(fold(text)):
                h = int(hashlib.md5(tok.encode()).hexdigest()[:8], 16)
                vec[h % self.dim] += 1.0
            out.append(_normalize(vec))
        return out


class SentenceTransformerEmbedder:
    name = EMBEDDING_MODEL
    low, high = 0.15, 0.75

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vectors]


def default_embedder() -> Embedder:
    try:
        return SentenceTransformerEmbedder()
    except ImportError:
        log.info("sentence-transformers no instalado: se usa HashingEmbedder")
        return HashingEmbedder()


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def rescale(similarity: float, embedder: Embedder) -> float:
    value = (similarity - embedder.low) / (embedder.high - embedder.low)
    return max(0.0, min(1.0, value))


def offer_text(offer: JobOffer) -> str:
    return f"{offer.title}. {' '.join(offer.skills)}. {offer.description[:2000]}"


def pack(vector: list[float]) -> bytes:
    return array("f", vector).tobytes()


def unpack(blob: bytes) -> list[float]:
    arr = array("f")
    arr.frombytes(blob)
    return arr.tolist()
