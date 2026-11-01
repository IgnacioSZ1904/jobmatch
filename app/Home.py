"""JobMatch: página principal."""

import streamlit as st
from ui_common import get_embedder, get_repo, require_profile

from jobmatch.config import settings
from jobmatch.connectors import all_connectors
from jobmatch.services import list_offers, refresh_offers, score_pending

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

st.subheader("Fuentes")
for c in all_connectors():
    st.write(f"{'🟢' if c.is_configured() else '⚪'} {c.name}")

if ranked:
    st.page_link("pages/2_Ofertas.py", label="Ver ofertas →", icon="📋")
