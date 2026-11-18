
# ============================================================
# MALAGA AIRBNB AI ANALYTICS
# Aplicación Streamlit conectada con Databricks Genie
# ============================================================

# ------------------------------------------------------------
# 1. Sistema de diagnóstico original de Databricks
# ------------------------------------------------------------

import os as _diag_os
import sys as _diag_sys

_diag_dir = _diag_os.path.dirname(
    _diag_os.path.abspath(__file__)
)

if _diag_dir not in _diag_sys.path:
    _diag_sys.path.insert(0, _diag_dir)

import app_diagnostics

app_diagnostics.install_diagnostics()


# ------------------------------------------------------------
# 2. Librerías
# ------------------------------------------------------------

import os
import time

import streamlit as st
from databricks.sdk import WorkspaceClient


# ------------------------------------------------------------
# 3. Configuración de Streamlit
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# 4. Indicadores principales
# Valores estáticos de nuestro dataset de septiembre de 2026
# ------------------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Alojamientos",
        value="9.505"
    )

with col2:
    st.metric(
        label="Precio medio",
        value="213,35 €"
    )

with col3:
    st.metric(
        label="Barrios",
        value="11"
    )


# ------------------------------------------------------------
# 5. Función para consultar Genie
# ------------------------------------------------------------

def consultar_genie(pregunta):

    # Identificador del recurso autorizado en Databricks Apps
    space_id = os.environ["GENIE_SPACE_ID"]

    # Cliente autenticado con la identidad de la aplicación
    client = WorkspaceClient()

    # Iniciar conversación mediante la API de Genie
    inicio = client.api_client.do(
        "POST",
        f"/api/2.0/genie/spaces/{space_id}/start-conversation",
        body={
            "content": pregunta
        }
    )

    conversation_id = inicio["conversation_id"]
    message_id = inicio["message_id"]

    # Consultar periódicamente el estado de la respuesta
    for intento in range(30):

        mensaje = client.genie.get_message(
            space_id=space_id,
            conversation_id=conversation_id,
            message_id=message_id
        )

        # Convertir el estado a una cadena sencilla
        estado = str(mensaje.status).split(".")[-1]

        # Caso 1: Genie ha completado la consulta
        if estado == "COMPLETED":

            return {
                "status": "COMPLETED",
                "message": mensaje,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "error": None
            }

        # Caso 2: Genie ha fallado
        if estado == "FAILED":

            error = mensaje.error

            return {
                "status": "FAILED",
                "message": mensaje,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "error": {
                    "type": str(
                        getattr(error, "type", "UNKNOWN")
                    ),
                    "detail": getattr(
                        error, "error", "Sin detalle disponible"
                    )
                }
            }

        # Caso 3: La consulta se ha cancelado
        if estado == "CANCELLED":

            return {
                "status": "CANCELLED",
                "message": mensaje,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "error": None
            }

        # Genie sigue procesando
        time.sleep(2)

    # No hemos obtenido un estado final
    return {
        "status": "TIMEOUT",
        "message": None,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "error": None
    }


# ------------------------------------------------------------
# 6. Interfaz del asistente
# ------------------------------------------------------------

st.subheader("🤖 Asistente de análisis")

st.caption(
    "Consulta los datos de Airbnb Málaga mediante "
    "lenguaje natural utilizando Databricks Genie."
)

pregunta = st.chat_input(
    "Pregunta algo sobre los alojamientos de Málaga..."
)


# ------------------------------------------------------------
# 7. Procesar la pregunta
# ------------------------------------------------------------

if pregunta:

    with st.chat_message("user"):
        st.write(pregunta)

    with st.chat_message("assistant"):

        with st.spinner("Consultando Genie..."):

            try:

                resultado = consultar_genie(pregunta)

                estado = resultado["status"]

                # --------------------------------------------
                # RESPUESTA COMPLETADA
                # --------------------------------------------

                if estado == "COMPLETED":

                    st.success(
                        "Genie ha completado la consulta."
                    )

                    mensaje = resultado["message"]
                    client = WorkspaceClient()
                    space_id = os.environ["GENIE_SPACE_ID"]
                    
                    for adjunto in (mensaje.attachments or []):
                    
                        if adjunto.query is None:
                            continue
                    
                        datos = client.genie.get_message_attachment_query_result(
                            space_id=space_id,
                            conversation_id=resultado["conversation_id"],
                            message_id=resultado["message_id"],
                            attachment_id=adjunto.attachment_id
                        )

                        # Inspeccionar la estructura devuelta por la API
                        with st.expander("Datos SQL recibidos"):
                            st.json(datos.as_dict())

                    # Mostrar texto devuelto por Genie
                    hay_texto = False

                    for adjunto in (mensaje.attachments or []):

                        if (
                            adjunto.text is not None
                            and adjunto.text.content
                        ):
                            st.write(adjunto.text.content)
                            hay_texto = True

                    if not hay_texto:
                        st.info(
                            "Genie ha completado el mensaje. "
                            "Puede haber generado SQL o datos "
                            "que recuperaremos en la siguiente fase."
                        )

                    # Mostrar SQL generado, si existe
                    with st.expander("SQL generado"):

                        hay_sql = False

                        for adjunto in (
                            mensaje.attachments or []
                        ):

                            consulta = getattr(
                                adjunto, "query", None
                            )

                            if (
                                consulta is not None
                                and getattr(
                                    consulta, "query", None
                                )
                            ):
                                st.code(
                                    consulta.query,
                                    language="sql"
                                )
                                hay_sql = True

                        if not hay_sql:
                            st.write(
                                "No se ha encontrado SQL "
                                "en los adjuntos."
                            )

                # --------------------------------------------
                # RESPUESTA FALLIDA
                # --------------------------------------------

                elif estado == "FAILED":

                    st.error(
                        "Genie ha fallado al procesar la consulta."
                    )

                    error = resultado["error"] or {}

                    st.write(
                        "**Tipo de error:**",
                        error.get("type", "Desconocido")
                    )

                    st.write(
                        "**Detalle del error:**",
                        error.get(
                            "detail",
                            "No disponible"
                        )
                    )

                # --------------------------------------------
                # CONSULTA CANCELADA
                # --------------------------------------------

                elif estado == "CANCELLED":

                    st.warning(
                        "La consulta ha sido cancelada."
                    )

                # --------------------------------------------
                # TIEMPO DE PRUEBA SUPERADO
                # --------------------------------------------

                elif estado == "TIMEOUT":

                    st.warning(
                        "Genie todavía no ha terminado "
                        "la consulta durante esta prueba."
                    )

                # --------------------------------------------
                # INFORMACIÓN TÉCNICA
                # --------------------------------------------

                with st.expander("Detalles técnicos"):

                    st.write(
                        "Estado:",
                        resultado["status"]
                    )

                    st.write(
                        "Conversación:",
                        resultado["conversation_id"]
                    )

                    st.write(
                        "Mensaje:",
                        resultado["message_id"]
                    )

            except Exception as e:

                st.error(
                    "Error de comunicación con Databricks."
                )

                st.write(
                    "**Detalle técnico:**",
                    str(e)
                )

