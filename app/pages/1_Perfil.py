"""Cuestionario guiado para crear o editar el perfil."""

import pandas as pd
import streamlit as st

from jobmatch.normalize.skills import skill_names
from jobmatch.profile.model import Profile
from jobmatch.profile.questionnaire import STEPS, Question
from jobmatch.profile.store import load_profile, load_raw_profile, save_profile

st.set_page_config(page_title="Perfil · JobMatch", page_icon="👤", layout="wide")
st.title("👤 Tu perfil")

if "draft" not in st.session_state:
    existing = load_profile()
    if existing:
        st.session_state.draft = existing.model_dump(mode="json")
    else:
        # Perfil inexistente o corrupto: se recupera lo que se pueda
        base = Profile().model_dump(mode="json")
        base.update({k: v for k, v in load_raw_profile().items() if k in base})
        st.session_state.draft = base
    st.session_state.step = 0

draft: dict = st.session_state.draft
step_idx: int = st.session_state.step
step = STEPS[step_idx]
st.progress((step_idx + 1) / len(STEPS), text=f"Paso {step_idx + 1}/{len(STEPS)}: {step.title}")


def widget(q: Question):
    value = draft.get(q.field)
    key = f"q_{q.field}"
    if q.kind == "multiselect":
        return st.multiselect(
            q.label,
            q.options,
            default=[v for v in value if v in q.options],
            key=key,
            help=q.help or None,
        )
    if q.kind == "select":
        return st.selectbox(
            q.label, q.options, index=q.options.index(value) if value in q.options else 0, key=key
        )
    if q.kind == "text":
        return st.text_input(q.label, value or "", key=key, help=q.help or None)
    if q.kind == "textarea":
        return st.text_area(q.label, value or "", key=key, help=q.help or None)
    if q.kind == "number":
        return st.number_input(q.label, min_value=0.0, value=float(value or 0), key=key)
    if q.kind == "bool":
        return st.toggle(q.label, bool(value), key=key)
    if q.kind == "tags":
        text = st.text_input(
            q.label,
            ", ".join(value or []),
            key=key,
            help=(q.help + " · " if q.help else "") + "Separadas por comas",
        )
        return [t.strip() for t in text.split(",") if t.strip()]
    if q.kind == "skills":
        df = pd.DataFrame(value or [], columns=["name", "level", "must_have"])
        edited = st.data_editor(
            df,
            num_rows="dynamic",
            key=key,
            use_container_width=True,
            column_config={
                "name": st.column_config.SelectboxColumn(
                    "Tecnología", options=skill_names(), required=True
                ),
                "level": st.column_config.NumberColumn(
                    "Nivel", min_value=1, max_value=5, default=3
                ),
                "must_have": st.column_config.CheckboxColumn("Imprescindible", default=False),
            },
        )
        return [r for r in edited.to_dict("records") if r.get("name")]
    if q.kind == "languages":
        df = pd.DataFrame(value or [], columns=["code", "level"])
        edited = st.data_editor(
            df,
            num_rows="dynamic",
            key=key,
            column_config={
                "code": st.column_config.TextColumn("Idioma (es, en, de…)", required=True),
                "level": st.column_config.SelectboxColumn("Nivel", options=q.options, default="B2"),
            },
        )
        return [r for r in edited.to_dict("records") if r.get("code")]
    raise ValueError(q.kind)


with st.form(f"step_{step_idx}"):
    answers = {q.field: widget(q) for q in step.questions}
    cols = st.columns([1, 1, 4])
    back = cols[0].form_submit_button("← Anterior", disabled=step_idx == 0)
    last = step_idx == len(STEPS) - 1
    forward = cols[1].form_submit_button("Guardar" if last else "Siguiente →", type="primary")

if back or forward:
    if answers.get("min_salary") == 0:
        answers["min_salary"] = None
    draft.update(answers)
    if back:
        st.session_state.step -= 1
        st.rerun()
    if not last:
        st.session_state.step += 1
        st.rerun()
    try:
        profile = Profile.model_validate(draft)
    except Exception as exc:
        st.error(f"Revisa los datos: {exc}")
    else:
        save_profile(profile)
        st.success("Perfil guardado. Las ofertas se volverán a puntuar.")
        st.session_state.step = 0
        st.page_link("Home.py", label="Ir al inicio →", icon="🏠")
