
# ============================================================
# MALAGA AIRBNB AI ANALYTICS
# Streamlit + Databricks Genie
# ============================================================

# 1. Diagnósticos originales de Databricks Apps
import os as _diag_os
import sys as _diag_sys

_diag_dir = _diag_os.path.dirname(_diag_os.path.abspath(__file__))
if _diag_dir not in _diag_sys.path:
    _diag_sys.path.insert(0, _diag_dir)

import app_diagnostics
app_diagnostics.install_diagnostics()


# 2. Librerías
import os
import time

import streamlit as st
from databricks.sdk import WorkspaceClient


# 3. Consulta a Genie

def consultar_genie(pregunta):
    space_id = os.environ["GENIE_SPACE_ID"]
    client = WorkspaceClient()

    inicio = client.api_client.do(
        "POST",
        f"/api/2.0/genie/spaces/{space_id}/start-conversation",
        body={"content": pregunta},
    )

    conversation_id = inicio["conversation_id"]
    message_id = inicio["message_id"]

    for _ in range(30):
        mensaje = client.genie.get_message(
            space_id=space_id,
            conversation_id=conversation_id,
            message_id=message_id,
        )

        estado = str(mensaje.status).split(".")[-1]

        if estado in ("COMPLETED", "FAILED", "CANCELLED"):
            error = getattr(mensaje, "error", None)

            return {
                "status": estado,
                "message": mensaje,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "error_type": str(
                    getattr(error, "type", "UNKNOWN")
                ),
                "error_detail": str(
                    getattr(error, "error", "Sin detalle disponible")
                ),
            }

        time.sleep(2)

    return {
        "status": "TIMEOUT",
        "message": None,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "error_type": None,
        "error_detail": None,
    }


# 4. Recuperar resultados SQL mediante API REST

def recuperar_resultado_sql(
    client,
    space_id,
    conversation_id,
    message_id,
    attachment_id
):
    ruta = (
        f"/api/2.0/genie/spaces/{space_id}"
        f"/conversations/{conversation_id}"
        f"/messages/{message_id}"
        f"/attachments/{attachment_id}/query-result"
    )

    return client.api_client.do("GET", ruta)


# 5. Interfaz de Streamlit

st.set_page_config(
    page_title="Málaga Airbnb AI",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 Málaga Airbnb AI Analytics")

st.write(
    "Plataforma inteligente de análisis de alojamientos "
    "turísticos en Málaga."
)

st.divider()

# Indicadores estáticos del snapshot del proyecto
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Alojamientos", "9.505")

with col2:
    st.metric("Precio medio", "213,35 €")

with col3:
    st.metric("Barrios", "11")


# 6. Asistente de análisis

st.subheader("🤖 Asistente de análisis")

st.caption(
    "Consultas en lenguaje natural sobre las tablas "
    "Gold de Airbnb Málaga."
)

pregunta = st.chat_input(
    "Pregunta algo sobre los alojamientos de Málaga..."
)


# 7. Procesar preguntas

if pregunta:

    with st.chat_message("user"):
        st.write(pregunta)

    with st.chat_message("assistant"):

        with st.spinner("Consultando Genie..."):

            try:
                resultado = consultar_genie(pregunta)
                estado = resultado["status"]

                # RESPUESTA COMPLETADA
                if estado == "COMPLETED":

                    st.success(
                        "Genie ha completado la consulta."
                    )

                    mensaje = resultado["message"]
                    adjuntos = mensaje.attachments or []

                    # Mostrar respuesta textual
                    textos = [
                        a.text.content
                        for a in adjuntos
                        if getattr(a, "text", None) is not None
                        and getattr(a.text, "content", None)
                    ]

                    for texto in textos:
                        st.write(texto)

                    # Identificar adjuntos SQL
                    consultas = [
                        a for a in adjuntos
                        if getattr(a, "query", None) is not None
                    ]

                    if consultas:

                        # Mostrar el SQL generado
                        with st.expander("SQL generado"):

                            for adjunto in consultas:
                                sql = getattr(
                                    adjunto.query, "query", None
                                )

                                if sql:
                                    st.code(sql, language="sql")
                                else:
                                    st.info(
                                        "Este adjunto no contiene "
                                        "SQL visible."
                                    )

                        # Recuperar resultados tabulares
                        client = WorkspaceClient()
                        space_id = os.environ["GENIE_SPACE_ID"]

                        for indice, adjunto in enumerate(
                            consultas, start=1
                        ):

                            with st.expander(
                                f"Datos SQL recibidos — consulta {indice}"
                            ):

                                try:
                                    datos = recuperar_resultado_sql(
                                        client=client,
                                        space_id=space_id,
                                        conversation_id=resultado[
                                            "conversation_id"
                                        ],
                                        message_id=resultado[
                                            "message_id"
                                        ],
                                        attachment_id=adjunto.attachment_id,
                                    )

                                    st.json(datos)

                                except Exception as error_sql:
                                    st.warning(
                                        "No se pudo recuperar "
                                        "el resultado tabular."
                                    )
                                    st.code(str(error_sql))

                    elif not textos:
                        st.info(
                            "Genie completó el mensaje "
                            "sin adjuntos visibles."
                        )

                # RESPUESTA FALLIDA
                elif estado == "FAILED":

                    st.error(
                        "Genie ha fallado al procesar la consulta."
                    )

                    st.write(
                        "**Tipo de error:**",
                        resultado["error_type"]
                    )

                    st.write(
                        "**Detalle del error:**",
                        resultado["error_detail"]
                    )

                # CONSULTA CANCELADA
                elif estado == "CANCELLED":

                    st.warning(
                        "La consulta se ha cancelado."
                    )

                # TIEMPO DE PRUEBA SUPERADO
                elif estado == "TIMEOUT":

                    st.warning(
                        "Genie no ha terminado durante "
                        "el período de comprobación."
                    )

                # DIAGNÓSTICO
                with st.expander("Detalles técnicos"):

                    st.write("Estado:", estado)

                    st.write(
                        "Conversación:",
                        resultado["conversation_id"]
                    )

                    st.write(
                        "Mensaje:",
                        resultado["message_id"]
                    )

            except Exception as error:

                st.error(
                    "Error de comunicación con Databricks."
                )

                st.code(str(error))
