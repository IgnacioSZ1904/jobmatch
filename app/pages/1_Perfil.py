"""Cuestionario guiado para crear o editar el perfil."""

import pandas as pd
import streamlit as st

from jobmatch.normalize.skills import skill_names
from jobmatch.profile.linkedin import parse_linkedin_pdf
from jobmatch.profile.model import (
    MUST_HAVE_HELP,
    SKILL_LEVELS,
    Profile,
    parse_skill_level_label,
    skill_level_label,
)
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


def reset_widgets() -> None:
    """Fuerza widgets nuevos (claves nuevas) para que muestren el borrador actualizado."""
    st.session_state.form_version = st.session_state.get("form_version", 0) + 1


with st.expander("📥 Importar desde LinkedIn", expanded=st.session_state.step == 0):
    st.markdown(
        "En tu perfil de LinkedIn pulsa **Más → Guardar en PDF** y sube aquí el archivo. "
        "Se rellenarán tecnologías, años de experiencia, puesto, ubicación, idiomas y "
        "resumen; después revisa cada paso y ajusta lo que haga falta."
    )
    uploaded = st.file_uploader("PDF del perfil", type="pdf", key="linkedin_pdf")
    if uploaded and st.button("Importar", type="primary"):
        imported = parse_linkedin_pdf(uploaded.getvalue())
        for warning in imported.warnings:
            st.warning(warning)
        if imported.fields:
            draft.update(imported.fields)
            reset_widgets()
            st.session_state.step = 0
            st.session_state.imported = sorted(imported.fields)
            st.rerun()

if st.session_state.get("imported"):
    st.success(
        "Importado de LinkedIn: "
        + ", ".join(st.session_state.pop("imported"))
        + ". Revisa los pasos y ajusta los niveles."
    )

step_idx: int = st.session_state.step
step = STEPS[step_idx]
st.progress((step_idx + 1) / len(STEPS), text=f"Paso {step_idx + 1}/{len(STEPS)}: {step.title}")


def widget(q: Question):
    value = draft.get(q.field)
    key = f"q_{q.field}_{st.session_state.get('form_version', 0)}"
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
        rows = [{**r, "level": skill_level_label(int(r.get("level") or 3))} for r in value or []]
        df = pd.DataFrame(rows, columns=["name", "level", "must_have"])
        labels = [skill_level_label(n) for n in SKILL_LEVELS]
        edited = st.data_editor(
            df,
            num_rows="dynamic",
            key=key,
            use_container_width=True,
            column_config={
                "name": st.column_config.SelectboxColumn(
                    "Tecnología", options=skill_names(), required=True
                ),
                "level": st.column_config.SelectboxColumn(
                    "Nivel",
                    options=labels,
                    default=labels[2],
                    required=True,
                    help="Mira la escala de niveles debajo de la tabla.",
                ),
                "must_have": st.column_config.CheckboxColumn(
                    "Imprescindible", default=False, help=MUST_HAVE_HELP
                ),
            },
        )
        scale = "\n".join(
            f"- **{skill_level_label(n)}**: {desc}" for n, (_, desc) in SKILL_LEVELS.items()
        )
        st.markdown(f"**Escala de niveles**\n\n{scale}\n\n**Imprescindible**: {MUST_HAVE_HELP}")
        return [
            {
                **r,
                "level": parse_skill_level_label(r.get("level") or labels[2]),
                "must_have": bool(r.get("must_have")),
            }
            for r in edited.to_dict("records")
            if r.get("name")
        ]
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
