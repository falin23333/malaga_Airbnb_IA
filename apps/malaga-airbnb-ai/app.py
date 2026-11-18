def obtener_mensaje_rest(client, space_id, conversation_id, message_id):
    """Devuelve los adjuntos originales, incluidos sus attachment_id."""
    ruta = (
        f"/api/2.0/genie/spaces/{space_id}"
        f"/conversations/{conversation_id}"
        f"/messages/{message_id}"
    )
    return client.api_client.do("GET", ruta)


def recuperar_resultado_sql(client, space_id, conversation_id, message_id, attachment_id):
    """Recupera el resultado SQL del adjunto original de Genie."""
    ruta = (
        f"/api/2.0/genie/spaces/{space_id}"
        f"/conversations/{conversation_id}"
        f"/messages/{message_id}"
        f"/attachments/{attachment_id}/query-result"
    )
    return client.api_client.do("GET", ruta)


# Interfaz Streamlit
st.set_page_config(page_title="Málaga Airbnb AI", page_icon="🏠", layout="wide")
st.title("🏠 Málaga Airbnb AI Analytics")
st.write("Plataforma inteligente de análisis de alojamientos turísticos en Málaga.")
st.divider()

# Indicadores estáticos del dataset de septiembre de 2026
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Alojamientos", "9.505")
with col2:
    st.metric("Precio medio", "213,35 €")
with col3:
    st.metric("Barrios", "11")

st.subheader("🤖 Asistente de análisis")
st.caption("Consultas en lenguaje natural sobre las tablas Gold de Airbnb Málaga.")
pregunta = st.chat_input("Pregunta algo sobre los alojamientos de Málaga...")

if pregunta:
    with st.chat_message("user"):
        st.write(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando Genie..."):
            try:
                resultado = consultar_genie(pregunta)
                estado = resultado["status"]

                if estado == "COMPLETED":
                    st.success("Genie ha completado la consulta.")
                    mensaje = resultado["message"]
                    adjuntos = mensaje.attachments or []

                    # Mostrar las respuestas escritas del agente
                    textos = [
                        a.text.content
                        for a in adjuntos
                        if getattr(a, "text", None) is not None
                        and getattr(a.text, "content", None)
                    ]
                    for texto in textos:
                        st.write(texto)

                    # Mostrar SQL si existe
                    consultas = [a for a in adjuntos if getattr(a, "query", None) is not None]
                    if consultas:
                        with st.expander("SQL generado"):
                            for adjunto in consultas:
                                sql = getattr(adjunto.query, "query", None)
                                if sql:
                                    st.code(sql, language="sql")
                                else:
                                    st.info("No hay SQL visible en este adjunto.")

                        # El SDK puede omitir attachment_id: usar la respuesta REST ORIGINAL.
                        client = WorkspaceClient()
                        space_id = os.environ["GENIE_SPACE_ID"]
                        try:
                            mensaje_rest = obtener_mensaje_rest(
                                client,
                                space_id,
                                resultado["conversation_id"],
                                resultado["message_id"],
                            )
                            adjuntos_sql_rest = [
                                a for a in mensaje_rest.get("attachments", [])
                                if a.get("query") is not None
                            ]
                        except Exception as error_rest:
                            st.warning("No se pudieron obtener los adjuntos originales de Genie.")
                            st.code(str(error_rest))
                            adjuntos_sql_rest = []

                        for indice, adjunto_rest in enumerate(adjuntos_sql_rest, start=1):
                            with st.expander(f"Datos SQL recibidos — consulta {indice}"):
                                attachment_id = adjunto_rest.get("attachment_id")
                                if not attachment_id:
                                    st.warning("La respuesta REST no incluye attachment_id para esta consulta.")
                                    st.json(adjunto_rest)
                                    continue

                                try:
                                    datos = recuperar_resultado_sql(
                                        client=client,
                                        space_id=space_id,
                                        conversation_id=resultado["conversation_id"],
                                        message_id=resultado["message_id"],
                                        attachment_id=attachment_id,
                                    )
                                    st.write("Resultado tabular devuelto por Genie:")
                                    st.json(datos)
                                except Exception as error_sql:
                                    st.warning("No se pudo recuperar el resultado tabular.")
                                    st.code(str(error_sql))
                    elif not textos:
                        st.info("Genie completó el mensaje sin respuesta visible.")

                elif estado == "FAILED":
                    st.error("Genie ha fallado al procesar la consulta.")
                    st.write("**Tipo de error:**", resultado["error_type"])
                    st.write("**Detalle del error:**", resultado["error_detail"])
                elif estado == "CANCELLED":
                    st.warning("La consulta se ha cancelado.")
                elif estado == "TIMEOUT":
                    st.warning("Genie no ha terminado durante el período de comprobación.")

                with st.expander("Detalles técnicos"):
                    st.write("Estado:", estado)
                    st.write("Conversación:", resultado["conversation_id"])
                    st.write("Mensaje:", resultado["message_id"])

            except Exception as error:
                st.error("Error de comunicación con Databricks.")
                st.code(str(error))
