"""Utilidades de texto."""

from __future__ import annotations

import html
import re
import unicodedata

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"</?(p|div|br|li|ul|ol|h\d)[^>]*>", re.I)
_SPACES = re.compile(r"[ \t]+")
_NEWLINES = re.compile(r"\n{3,}")


def html_to_text(raw: str | None) -> str:
    if not raw:
        return ""
    text = _BLOCK.sub("\n", raw)
    text = html.unescape(_TAG.sub("", text))
    text = _SPACES.sub(" ", text)
    return _NEWLINES.sub("\n\n", text).strip()


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def fold(text: str) -> str:
    """Minúsculas y sin acentos, para comparar."""
    return strip_accents(text).lower()
