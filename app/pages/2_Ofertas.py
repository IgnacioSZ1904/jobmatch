"""Ofertas ordenadas por compatibilidad, con desglose y gestión de estado."""

import streamlit as st
from ui_common import get_repo, require_profile

from jobmatch.connectors import all_connectors
from jobmatch.connectors.remoteok import ATTRIBUTION
from jobmatch.models import SENIORITY_LABELS, Modality, OfferStatus
from jobmatch.scoring.scorer import LABELS
from jobmatch.services import list_offers, set_status

st.set_page_config(page_title="Ofertas · JobMatch", page_icon="📋", layout="wide")
st.title("📋 Ofertas")

profile = require_profile()
repo = get_repo()

STATUS_LABELS = {
    OfferStatus.NEW: "🆕 Nueva",
    OfferStatus.SEEN: "👁 Vista",
    OfferStatus.INTERESTING: "⭐ Interesante",
    OfferStatus.DISCARDED: "🗑 Descartada",
    OfferStatus.APPLIED: "📨 Aplicada",
}

with st.sidebar:
    st.header("Filtros")
    min_score = st.slider("Puntuación mínima", 0, 100, 40)
    sources = st.multiselect("Fuentes", [c.name for c in all_connectors()] + ["manual"])
    modalities = st.multiselect("Modalidad", [m.value for m in Modality])
    statuses = st.multiselect(
        "Estado",
        list(OfferStatus),
        default=[OfferStatus.NEW, OfferStatus.SEEN, OfferStatus.INTERESTING],
        format_func=lambda s: STATUS_LABELS[s],
    )
    only_new = st.toggle("Solo nuevas")

tab_ranked, tab_filtered = st.tabs(["Ranking", "Filtradas"])


def render(rows, show_reason=False):
    if not rows:
        st.info("No hay ofertas con estos filtros. Prueba a actualizar desde el inicio.")
        return
    for row in rows:
        o, score = row.offer, row.score
        header = f"**{score.total:.0f}** · {o.title} — {o.company} · {STATUS_LABELS[row.status]}"
        with st.expander(header):
            b = score.breakdown
            if show_reason:
                st.warning(b.get("filtered_reason") or "")
            cols = st.columns(len(b["components"]))
            for col, (name, c) in zip(cols, b["components"].items(), strict=True):
                col.metric(LABELS[name], f"{c['points']:.0f}/{c['max']:.0f}")
                col.caption(c["detail"])
            for p in b.get("penalties", []):
                st.error(p)
            meta = [o.source, o.modality.value, o.location_text, SENIORITY_LABELS[o.seniority]]
            st.caption(" · ".join(m for m in meta if m and m not in ("unknown", "Sin indicar")))
            st.markdown(f"[Ver oferta original]({o.url})")
            dups = repo.duplicates_of(o.id)
            if dups:
                st.caption("También en: " + ", ".join(f"[{d.source}]({d.url})" for d in dups))
            st.text(o.description[:3000])

            c1, c2 = st.columns([1, 3])
            new_status = c1.selectbox(
                "Estado",
                list(OfferStatus),
                index=list(OfferStatus).index(row.status),
                format_func=lambda s: STATUS_LABELS[s],
                key=f"s_{o.id}",
            )
            notes = c2.text_input("Notas", row.notes, key=f"n_{o.id}")
            if new_status != row.status or notes != row.notes:
                set_status(repo, o.id, new_status, notes)
                st.rerun()


filters = dict(
    min_score=min_score,
    sources=sources or None,
    modalities=modalities or None,
    statuses=statuses or None,
    only_new=only_new,
)
with tab_ranked:
    render(list_offers(repo, profile, **filters))
with tab_filtered:
    render(list_offers(repo, profile, filtered=True, sources=sources or None), show_reason=True)

st.caption(
    ATTRIBUTION + " · Remotive (remotive.com) · Arbeitnow (arbeitnow.com) · InfoJobs (infojobs.net)"
)
