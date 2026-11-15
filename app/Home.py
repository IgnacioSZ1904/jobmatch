"""JobMatch: página principal."""

import streamlit as st
from ui_common import get_embedder, get_repo, require_profile

from jobmatch.config import settings
from jobmatch.connectors import all_connectors
from jobmatch.search_links import build_links
from jobmatch.services import (
    import_manual_offer,
    list_offers,
    refresh_offers,
    score_pending,
)

st.set_page_config(page_title="JobMatch", page_icon="🎯", layout="wide")
st.title("🎯 JobMatch")
st.caption("Ofertas de empleo de software ordenadas por compatibilidad con tu perfil.")

profile = require_profile()
repo = get_repo()

# Si el perfil ha cambiado, recalcula las puntuaciones existentes
if repo.unscored_ids(profile.fingerprint()):
    with st.spinner("Puntuando ofertas con tu perfil…"):
        score_pending(repo, profile, get_embedder())

if st.button("🔄 Actualizar ofertas", type="primary"):
    status = st.status("Descargando ofertas…", expanded=True)

    def progress(name, src):
        status.write(f"✔ {name}: {src.fetched} recibidas, {src.new} nuevas")

    report = refresh_offers(
        repo, profile, embedder=get_embedder(), raw_dir=settings.raw_dir, on_progress=progress
    )
    for name, src in report.sources.items():
        if src.error:
            status.write(f"✘ {name}: {src.error}")
    status.update(
        label=f"{report.new} nuevas · {report.duplicates} duplicadas",
        state="complete",
        expanded=False,
    )

ranked = list_offers(repo, profile)
new = [r for r in ranked if r.status == "new"]
c1, c2, c3 = st.columns(3)
c1.metric("Ofertas en ranking", len(ranked))
c2.metric("Nuevas sin ver", len(new))
c3.metric("Nuevas con >80 puntos", sum(r.score.total > 80 for r in new))

if ranked:
    st.page_link("pages/2_Ofertas.py", label="Ver ofertas →", icon="📋")

st.subheader("Fuentes")
for c in all_connectors():
    if c.is_configured():
        st.write(f"🟢 {c.name}")
    else:
        st.write(f"⚪ {c.name} — desactivada: faltan las credenciales en `.env`")

st.subheader("Buscar en otros portales")
st.caption(
    "LinkedIn, Indeed y otros portales no tienen API pública: estos enlaces abren la "
    "búsqueda con tu perfil. Si una oferta te interesa, añádela abajo para puntuarla."
)
cols = st.columns(4)
for col, link in zip(cols, build_links(profile), strict=False):
    col.link_button(link.portal, link.url, use_container_width=True)

with st.expander("➕ Añadir una oferta manualmente"):
    with st.form("manual_offer", clear_on_submit=True):
        url = st.text_input("URL de la oferta")
        title = st.text_input("Título del puesto *")
        c1, c2 = st.columns(2)
        company = c1.text_input("Empresa")
        location = c2.text_input("Ubicación", help="Ej.: Málaga (híbrido) o Remoto")
        text = st.text_area(
            "Texto de la oferta *", height=200, help="Copia y pega la descripción completa."
        )
        submitted = st.form_submit_button("Añadir y puntuar", type="primary")
    if submitted:
        try:
            offer, is_new = import_manual_offer(
                repo,
                profile,
                url=url,
                title=title,
                description=text,
                company=company,
                location=location,
                embedder=get_embedder(),
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            row = next(
                (
                    r
                    for r in list_offers(repo, profile) + list_offers(repo, profile, filtered=True)
                    if r.offer.id == offer.id
                ),
                None,
            )
            verb = "Añadida" if is_new else "Actualizada"
            if offer.duplicate_of:
                st.info(f"{verb}, pero ya tenías esta oferta de otra fuente.")
            elif row:
                st.success(f"{verb}: {offer.title} — {row.score.total:.0f} puntos.")
