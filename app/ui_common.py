"""Recursos compartidos por las páginas de Streamlit (cacheados)."""

from __future__ import annotations

import streamlit as st

from jobmatch.profile.model import Profile
from jobmatch.profile.store import load_profile
from jobmatch.scoring.semantic import Embedder, default_embedder
from jobmatch.services import default_repository
from jobmatch.storage import Repository


@st.cache_resource
def get_repo() -> Repository:
    return default_repository()


@st.cache_resource(show_spinner="Cargando modelo de embeddings…")
def get_embedder() -> Embedder:
    return default_embedder()


def require_profile() -> Profile:
    """Devuelve el perfil o manda al cuestionario si no existe."""
    profile = load_profile()
    if profile is None:
        st.info("Primero crea tu perfil.")
        st.switch_page("pages/1_Perfil.py")
        st.stop()
    return profile
