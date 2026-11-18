# --- diagnostics bootstrap: install crash/exception logging before app code ---
import os as _diag_os
import sys as _diag_sys

_diag_dir = _diag_os.path.dirname(_diag_os.path.abspath(__file__))
if _diag_dir not in _diag_sys.path:
    _diag_sys.path.insert(0, _diag_dir)
import app_diagnostics  # noqa: E402

app_diagnostics.install_diagnostics()
# --- end diagnostics bootstrap ---


import pandas as pd

import streamlit as st

st.set_page_config(
    page_title="Málaga Airbnb AI",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Málaga Airbnb AI Analytics")

st.write(
    "Plataforma inteligente de análisis de alojamientos "
    "turísticos en Málaga."
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Alojamientos", "9.505")

with col2:
    st.metric("Precio medio", "213,35 €")

with col3:
    st.metric("Barrios", "11")

st.subheader("🤖 Asistente de análisis")

pregunta = st.chat_input(
    "Pregunta algo sobre los alojamientos de Málaga..."
)

if pregunta:
    with st.chat_message("user"):
        st.write(pregunta)

    with st.chat_message("assistant"):
        st.info(
            "La conexión con Databricks Genie "
            "se implementará en el siguiente paso."
        )
