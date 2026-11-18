        return (
        f"/api/2.0/genie/spaces/{space_id}"
        f"/conversations/{conversation_id}"
        f"/messages/{message_id}"
    )


def consultar_genie(pregunta):
    """Inicia una conversacion y devuelve el mensaje REST completo."""
    client = obtener_cliente()
    space_id = os.environ["GENIE_SPACE_ID"]

    inicio = client.api_client.do(
        "POST",
        f"/api/2.0/genie/spaces/{space_id}/start-conversation",
        body={"content": pregunta},
    )
    conversation_id = inicio["conversation_id"]
    message_id = inicio["message_id"]
    ruta = ruta_mensaje(space_id, conversation_id, message_id)

    for _ in range(30):
        mensaje = client.api_client.do("GET", ruta)
        estado = str(mensaje.get("status", "")).split(".")[-1]
        if estado in ("COMPLETED", "FAILED", "CANCELLED"):
            return {
                "status": estado,
                "message": mensaje,
                "conversation_id": conversation_id,
                "message_id": message_id,
            }
        time.sleep(2)

    return {
        "status": "TIMEOUT",
        "message": None,
        "conversation_id": conversation_id,
        "message_id": message_id,
    }


def recuperar_resultado_sql(conversation_id, message_id, attachment_id):
    """Usa el ID real que viene en el JSON REST del mensaje."""
    if not attachment_id:
        raise ValueError("El adjunto SQL no incluye attachment_id")
    space_id = os.environ["GENIE_SPACE_ID"]
    ruta = (
        f"{ruta_mensaje(space_id, conversation_id, message_id)}"
        f"/attachments/{attachment_id}/query-result"
    )
    return obtener_cliente().api_client.do("GET", ruta)


def resultado_a_dataframe(datos):
    """Extrae las filas y columnas del resultado de Genie, si estan disponibles."""
    # La respuesta documentada incorpora statement_response.
    respuesta = datos.get("statement_response", datos)
    resultado = respuesta.get("result") or {}
    manifest = respuesta.get("manifest") or {}
    esquema = manifest.get("schema") or {}
    columnas_meta = esquema.get("columns") or []
    nombres = [c.get("name", f"col_{i+1}") for i, c in enumerate(columnas_meta)]
    filas = resultado.get("data_array") or []

    if not filas:
        return pd.DataFrame()

    if nombres and len(nombres) == len(filas[0]):
        df = pd.DataFrame(filas, columns=nombres)
    else:
        df = pd.DataFrame(filas)

    # La API devuelve valores como cadenas: detectar columnas numericas
    # solo cuando todas las observaciones no nulas pueden convertirse.
    for columna in df.columns:
        convertidos = pd.to_numeric(df[columna], errors="coerce")
        if df[columna].notna().any() and convertidos.notna().sum() == df[columna].notna().sum():
            df[columna] = convertidos
    return df
def mostrar_resultados_sql(resultado):
    """Recupera el adjunto SQL, muestra tabla y, cuando procede, grafico."""
    mensaje = resultado["message"] or {}
    adjuntos = mensaje.get("attachments") or []
    consultas = [a for a in adjuntos if a.get("query") is not None]

    if not consultas:
        return

    with st.expander("SQL generado"):
        for adjunto in consultas:
            consulta = (adjunto.get("query") or {}).get("query")
            if consulta:
                st.code(consulta, language="sql")

    for indice, adjunto in enumerate(consultas, start=1):
        with st.expander(f"Resultados SQL — consulta {indice}", expanded=True):
            attachment_id = adjunto.get("attachment_id")
            try:
                datos = recuperar_resultado_sql(
                    resultado["conversation_id"],
                    resultado["message_id"],
                    attachment_id,
                )
                df = resultado_a_dataframe(datos)
                if df.empty:
                    st.info("La consulta no devolvio filas en este resultado.")
                    with st.expander("Respuesta REST para diagnostico"):
                        st.json(datos)
                    continue

                st.dataframe(df, use_container_width=True, hide_index=True)

                # Grafico sencillo solo para tablas con categoria y valor.
                numericas = df.select_dtypes(include="number").columns.tolist()
                categorias = df.select_dtypes(exclude="number").columns.tolist()
                if numericas and categorias and len(df) <= 100:
                    eje_x = categorias[0]
                    eje_y = numericas[0]
                    fig = px.bar(
                        df.sort_values(eje_y, ascending=False),
                        x=eje_x,
                        y=eje_y,
                        title=f"{eje_y} por {eje_x}",
                        labels={eje_x: eje_x, eje_y: eje_y},
                    )
                    st.plotly_chart(fig, use_container_width=True)
                elif numericas and len(df) == 1:
                    st.metric(str(numericas[0]), str(df.iloc[0][numericas[0]]))
            except Exception as exc:
                st.warning("No se pudieron recuperar o visualizar las filas SQL.")
                st.code(str(exc))


# ---------- Interfaz ----------
st.set_page_config(page_title="Málaga Airbnb AI", page_icon="🏠", layout="wide")
st.title("🏠 Málaga Airbnb AI Analytics")
st.write("Plataforma inteligente de análisis de alojamientos turísticos en Málaga.")
st.divider()

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Alojamientos", "9.505")
with c2:
    st.metric("Precio medio anunciado", "213,35 €")
with c3:
    st.metric("Barrios", "11")
st.caption("Indicadores fijos del snapshot de septiembre de 2026; no se actualizan aún mediante Genie.")

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
                mensaje = resultado["message"] or {}

                if estado == "COMPLETED":
                    st.success("Genie ha completado la consulta.")
                    for adjunto in mensaje.get("attachments") or []:
                        texto = (adjunto.get("text") or {}).get("content")
                        if texto:
                            st.markdown(texto)
                    mostrar_resultados_sql(resultado)

                elif estado == "FAILED":
                    st.error("Genie ha fallado al procesar la consulta.")
                    error = mensaje.get("error") or {}
                    st.write("**Tipo:**", error.get("type", "Desconocido"))
                    st.write("**Detalle:**", error.get("error", "Sin detalle"))
                elif estado == "CANCELLED":
                    st.warning("Genie ha cancelado la consulta.")
                else:
                    st.warning("Genie no ha finalizado durante esta prueba.")

                with st.expander("Detalles técnicos"):
                    st.write("Estado:", estado)
                    st.write("Conversación:", resultado["conversation_id"])
                    st.write("Mensaje:", resultado["message_id"])

            except Exception as exc:
                st.error("Error de comunicación con Databricks.")
                st.code(str(exc))

