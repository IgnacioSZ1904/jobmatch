"""Enlaces de búsqueda en portales sin API pública (LinkedIn, Indeed…).

No se descarga nada de esos portales: solo se construye la URL de búsqueda con
los datos del perfil para abrirla en el navegador. Las ofertas que interesen se
pueden añadir a JobMatch con la importación manual.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlencode

from jobmatch.models import Modality, Seniority
from jobmatch.profile.model import Profile

# Filtros de LinkedIn Jobs: nivel (f_E) y modalidad (f_WT)
_LINKEDIN_LEVEL = {
    Seniority.INTERN: "1,2",
    Seniority.JUNIOR: "1,2",
    Seniority.MID: "3",
    Seniority.SENIOR: "4",
    Seniority.LEAD: "4,5",
}
_LINKEDIN_MODALITY = {Modality.ONSITE: "1", Modality.REMOTE: "2", Modality.HYBRID: "3"}


@dataclass(frozen=True)
class SearchLink:
    portal: str
    url: str


def search_keywords(profile: Profile) -> str:
    """Texto de búsqueda: el puesto deseado o, si no hay, rol + tecnología principal."""
    if profile.desired_title:
        return re.split(r"[|·,(]", profile.desired_title)[0].strip()
    top = sorted(profile.skills, key=lambda s: (not s.must_have, -s.level))
    parts = [top[0].name] if top else []
    parts.append(f"{profile.roles[0]} developer" if profile.roles else "developer")
    return " ".join(parts)


def build_links(profile: Profile) -> list[SearchLink]:
    keywords = search_keywords(profile)
    location = profile.city or profile.country or "España"
    keywords_es = f"prácticas {keywords}" if profile.seniority == Seniority.INTERN else keywords

    linkedin = {"keywords": keywords, "location": location}
    if profile.seniority in _LINKEDIN_LEVEL:
        linkedin["f_E"] = _LINKEDIN_LEVEL[profile.seniority]
    modalities = [_LINKEDIN_MODALITY[m] for m in profile.modalities if m in _LINKEDIN_MODALITY]
    if modalities:
        linkedin["f_WT"] = ",".join(modalities)

    return [
        SearchLink("LinkedIn", "https://www.linkedin.com/jobs/search/?" + urlencode(linkedin)),
        SearchLink(
            "InfoJobs",
            "https://www.infojobs.net/jobsearch/search-results/list.xhtml?"
            + urlencode({"keyword": keywords_es}),
        ),
        SearchLink(
            "Indeed", "https://es.indeed.com/jobs?" + urlencode({"q": keywords_es, "l": location})
        ),
        SearchLink(
            "Tecnoempleo",
            "https://www.tecnoempleo.com/ofertas-trabajo/?" + urlencode({"te": keywords}),
        ),
    ]
