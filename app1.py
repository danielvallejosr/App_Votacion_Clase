import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Votación Clase", layout="centered")

BASE_DIR = Path(__file__).parent
ESTADO_PATH = BASE_DIR / "estado.txt"
PREGUNTAS_ACTIVAS_PATH = BASE_DIR / "preguntas_activas.csv"
ARCHIVO_PREGUNTAS_NOMBRE_PATH = (
    BASE_DIR / "archivo_preguntas_nombre.txt"
)
CONFIG_PATH = BASE_DIR / "config.txt"

query_params = st.query_params
modo_profesor = query_params.get("modo") == "profesor"

if not modo_profesor:

    st_autorefresh(
        interval=3000,
        key="refresh_alumno"
    )

else:

    contador_refresh = st_autorefresh(
        interval=1500,
        key="refresh_profesor"
    )

def leer_config():
    if CONFIG_PATH.exists():
        lineas = CONFIG_PATH.read_text().splitlines()
        if len(lineas) >= 1:
            return lineas[0].strip()
    return ""


def guardar_config(nombre_respuestas):
    CONFIG_PATH.write_text(nombre_respuestas.strip())


def get_respuestas_path():
    nombre = leer_config()
    if not nombre:
        return None
    if not nombre.endswith(".csv"):
        nombre += ".csv"
    return BASE_DIR / nombre

def guardar_en_google_sheets(nueva_respuesta):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    gc = gspread.authorize(credentials)

    sheet = gc.open("Respuestas_App_Clase").worksheet("Respuestas")

    fila = [
        nueva_respuesta["fecha_hora"],
        nueva_respuesta["archivo_preguntas"],
        nueva_respuesta["nombre"],
        nueva_respuesta["pregunta_id"],
        nueva_respuesta["pregunta"],
        nueva_respuesta["respuesta"],
        nueva_respuesta["respuesta_texto"],
        nueva_respuesta["correcta"],
    ]

    sheet.append_row(fila)


# -----------------------------
# CONFIGURACIÓN PROFESOR
# -----------------------------

if modo_profesor:
    st.sidebar.title("Panel profesor")

    with st.sidebar.expander("Configuración de clase", expanded=False):

        archivo_preguntas = st.file_uploader(
            "Subir archivo de preguntas CSV",
            type=["csv"]
        )

        nombre_respuestas = st.text_input(
            "Archivo de respuestas",
            value=leer_config() or "respuestas_clase.csv"
        )

        if st.button("Iniciar / actualizar clase"):

            if archivo_preguntas is not None:
                contenido = archivo_preguntas.getvalue()
                PREGUNTAS_ACTIVAS_PATH.write_bytes(contenido)
                ARCHIVO_PREGUNTAS_NOMBRE_PATH.write_text(
                        archivo_preguntas.name
)
                guardar_config(nombre_respuestas)

                preguntas_temp = pd.read_csv(
                    PREGUNTAS_ACTIVAS_PATH,
                    sep=None,
                    engine="python",
                    encoding="utf-8-sig"
                )
                preguntas_temp.columns = preguntas_temp.columns.str.strip().str.lower()

                primera_pregunta = str(preguntas_temp.iloc[0]["id"])
                ESTADO_PATH.write_text(primera_pregunta)

                st.success("Clase configurada correctamente.")

            else:
                st.warning("Debe subir un archivo CSV de preguntas.")


# -----------------------------
# VALIDAR CLASE INICIADA
# -----------------------------

if not PREGUNTAS_ACTIVAS_PATH.exists() or get_respuestas_path() is None:
    st.title("Respuesta")
    st.info("La clase aún no ha comenzado.")
    st.stop()

RESPUESTAS_PATH = get_respuestas_path()


# -----------------------------
# CARGAR PREGUNTAS
# -----------------------------

preguntas = pd.read_csv(
    PREGUNTAS_ACTIVAS_PATH,
    sep=None,
    engine="python",
    encoding="utf-8-sig"
)

preguntas.columns = preguntas.columns.str.strip().str.lower()
ids_preguntas = preguntas["id"].astype(str).tolist()


# -----------------------------
# PREGUNTA ACTIVA GLOBAL
# -----------------------------

if modo_profesor:

    st.sidebar.divider()
    st.sidebar.subheader("Control de preguntas")

    if ESTADO_PATH.exists():
        pregunta_guardada = ESTADO_PATH.read_text().strip()
    else:
        pregunta_guardada = ids_preguntas[0]

    if pregunta_guardada not in ids_preguntas:
        pregunta_guardada = ids_preguntas[0]

    indice_default = ids_preguntas.index(pregunta_guardada)

    pregunta_id = st.sidebar.selectbox(
        "Pregunta activa",
        ids_preguntas,
        index=indice_default
    )

    pregunta_id = str(pregunta_id).strip()

    if st.sidebar.button("Siguiente pregunta"):

        if "mostrar_correcta_id" in st.session_state:
            st.session_state["mostrar_correcta_id"] = None

        indice_actual = ids_preguntas.index(pregunta_id)

        if indice_actual < len(ids_preguntas) - 1:
            pregunta_id = ids_preguntas[indice_actual + 1]
            ESTADO_PATH.write_text(pregunta_id)
            st.rerun()
        else:
            st.sidebar.warning("Ya estás en la última pregunta.")

    else:
        ESTADO_PATH.write_text(pregunta_id)

    if "mostrar_correcta_id" not in st.session_state:
        st.session_state["mostrar_correcta_id"] = None

    if st.sidebar.button("Mostrar respuesta correcta"):
        st.session_state["mostrar_correcta_id"] = pregunta_id

    mostrar_correcta = (
        st.session_state["mostrar_correcta_id"] == pregunta_id
    )

else:

    mostrar_correcta = False

    if ESTADO_PATH.exists():
        pregunta_id = ESTADO_PATH.read_text().strip()
    else:
        pregunta_id = ids_preguntas[0]

    if pregunta_id not in ids_preguntas:
        pregunta_id = ids_preguntas[0]


pregunta_id = str(pregunta_id).strip()

pregunta = preguntas[
    preguntas["id"].astype(str).str.strip() == pregunta_id
].iloc[0]


# -----------------------------
# PANTALLA PRINCIPAL
# -----------------------------

if not modo_profesor:

    st.title("Respuesta")

    if (
    "mensaje_exito" in st.session_state
    and st.session_state.get("mensaje_exito_pregunta_id") == str(pregunta["id"])
):

        st.success(
            st.session_state["mensaje_exito"]
        )

    nombre = st.text_input("Nombre")

    st.subheader(f"Pregunta {pregunta['id']}")
    st.write(pregunta["pregunta"])

else:

    st.title("Resultados en vivo")
    nombre = ""


opciones = {
    "A": pregunta["a"],
    "B": pregunta["b"],
    "C": pregunta["c"],
    "D": pregunta["d"],
}


if not modo_profesor:

    respuesta = st.radio(
        "Seleccione una alternativa:",
        list(opciones.keys()),
        format_func=lambda x: f"{x}. {opciones[x]}",
        index=None
    )

else:

    respuesta = None


# -----------------------------
# GUARDAR RESPUESTA
# -----------------------------

if not modo_profesor and st.button("Enviar respuesta"):

    if not nombre.strip():
        st.warning("Ingrese su nombre")

    elif respuesta is None:
        st.warning("Seleccione una alternativa")

    else:
        nombre_limpio = nombre.strip()

        if RESPUESTAS_PATH.exists():
            respuestas_previas = pd.read_csv(RESPUESTAS_PATH)
        else:
            respuestas_previas = pd.DataFrame()

        duplicada = False

        if not respuestas_previas.empty:
            duplicada = (
                (
                    respuestas_previas["nombre"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    == nombre_limpio.lower()
                )
                &
                (
                    respuestas_previas["pregunta_id"]
                    .astype(str)
                    == str(pregunta["id"])
                )
            ).any()

        if duplicada:
            st.error("Ya registraste una respuesta para esta pregunta.")

        else:
            nueva_respuesta_dict = {
                "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "archivo_preguntas": (
                    ARCHIVO_PREGUNTAS_NOMBRE_PATH.read_text().strip()
                     if ARCHIVO_PREGUNTAS_NOMBRE_PATH.exists()
                     else ""
                ),
                "nombre": nombre_limpio,
                "pregunta_id": str(pregunta["id"]),
                "pregunta": str(pregunta["pregunta"]),
                "respuesta": respuesta,
                "respuesta_texto": opciones[respuesta],
                "correcta": str(pregunta.get("correcta", "")),
            }

            nueva_respuesta = pd.DataFrame([nueva_respuesta_dict])

            respuestas = pd.concat(
                [respuestas_previas, nueva_respuesta],
                ignore_index=True
            )

            respuestas.to_csv(RESPUESTAS_PATH, index=False)

            st.session_state["mensaje_exito"] = (
                f"{nombre_limpio}, "
                f"su respuesta {respuesta} "
                f"fue registrada."
            )

            st.session_state["mensaje_exito_pregunta_id"] = str(
                pregunta["id"]
            )

            guardar_en_google_sheets(nueva_respuesta_dict)

            try:
                guardar_en_google_sheets(nueva_respuesta_dict)

                st.session_state["mensaje_exito"] = (
                    f"{nombre_limpio}, "
                    f"su respuesta {respuesta} "
                    f"fue registrada."
                )

                st.session_state["mensaje_exito_pregunta_id"] = str(
                     pregunta["id"]
                )

            except Exception as e:
                   st.error(f"Error al guardar en Google Sheets: {e}")

            st.session_state["mensaje_exito"] = (
                f"{nombre_limpio}, "
                f"su respuesta {respuesta} "
                f"fue registrada."
            )

            st.session_state["mensaje_exito_pregunta_id"] = str(
                pregunta["id"]
            )


# -----------------------------
# RESULTADOS EN VIVO
# -----------------------------

if modo_profesor:

    if RESPUESTAS_PATH.exists():
        respuestas = pd.read_csv(RESPUESTAS_PATH)
    else:
        respuestas = pd.DataFrame()

    if not respuestas.empty:
        respuestas_pregunta = respuestas[
            respuestas["pregunta_id"].astype(str) == str(pregunta["id"])
        ]
    else:
        respuestas_pregunta = pd.DataFrame()

    total = len(respuestas_pregunta)

    st.subheader(f"Pregunta {pregunta['id']}")
    st.write(f"Total respuestas: {total}")

    if total > 0:

        conteo = (
            respuestas_pregunta["respuesta"]
            .value_counts()
            .reindex(["A", "B", "C", "D"], fill_value=0)
        )

        porcentajes = round(conteo / total * 100, 1)

        resultados = pd.DataFrame({
            "Alternativa": conteo.index,
            "Respuestas": conteo.values,
            "Porcentaje": porcentajes.values
        })

        correcta = str(pregunta.get("correcta", "")).strip().upper()

        if mostrar_correcta and correcta in ["A", "B", "C", "D"]:
            resultados["Estado"] = resultados["Alternativa"].apply(
                lambda x: "Correcta" if x == correcta else "Otra"
            )
        else:
            resultados["Estado"] = "Otra"

        fig = px.bar(
            resultados.iloc[::-1],
            x="Respuestas",
            y="Alternativa",
            orientation="h",
            text="Porcentaje",
            color="Estado",
            color_discrete_map={
                "Correcta": "#2ecc71",
                "Otra": "#4c78a8"
            },
            category_orders={
                "Alternativa": ["D", "C", "B", "A"]
            },
            height=360
        )

        fig.update_traces(
            texttemplate="%{text}%",
            textposition="outside",
            textfont_size=34,
            cliponaxis=False
        )

        fig.update_layout(
            xaxis_title="Número de respuestas",
            yaxis_title="",
            showlegend=False,
            bargap=0.65,
            height=360,
            font=dict(size=22),
            xaxis=dict(
                tickfont=dict(size=20),
                title_font=dict(size=22)
            ),
            yaxis=dict(
                tickfont=dict(size=26),
                autorange="reversed"
            ),
            margin=dict(
                l=40,
                r=120,
                t=20,
                b=40
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )
            
    else:
        st.info("Aún no hay respuestas para esta pregunta.")
