import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Clase Interactiva", layout="centered")
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

BASE_DIR = Path(__file__).parent
ESTADO_PATH = BASE_DIR / "estado.txt"
ESTADO_VISUALIZACION_PATH = BASE_DIR / "estado_visualizacion.txt"
TIMER_DURACION_PATH = BASE_DIR / "timer_duracion.txt"
TIMER_INICIO_PATH = BASE_DIR / "timer_inicio.txt"
PREGUNTAS_ACTIVAS_PATH = BASE_DIR / "preguntas_activas.csv"
ESTADO_VISUALIZACION_PATH = (
    BASE_DIR / "estado_visualizacion.txt"
)
ARCHIVO_PREGUNTAS_NOMBRE_PATH = (
    BASE_DIR / "archivo_preguntas_nombre.txt"
)
CONFIG_PATH = BASE_DIR / "config.txt"

query_params = st.query_params
modo_profesor = query_params.get("modo") == "profesor"

if not modo_profesor:

    st_autorefresh(
        interval=1000,
        key="refresh_alumno"
    )

else:

    contador_refresh = st_autorefresh(
        interval=1000,
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

def leer_estado_visualizacion():

    if not ESTADO_VISUALIZACION_PATH.exists():
        return "votando"

    return (
        ESTADO_VISUALIZACION_PATH
        .read_text()
        .strip()
    )


def guardar_estado_visualizacion(
    estado
):
    ESTADO_VISUALIZACION_PATH.write_text(
        estado
    )

def leer_estado_visualizacion():
    if not ESTADO_VISUALIZACION_PATH.exists():
        return "votando"

    return ESTADO_VISUALIZACION_PATH.read_text().strip()


def guardar_estado_visualizacion(estado):
    ESTADO_VISUALIZACION_PATH.write_text(estado)    

def guardar_timer_duracion(segundos):
    TIMER_DURACION_PATH.write_text(str(segundos))


def leer_timer_duracion():
    if not TIMER_DURACION_PATH.exists():
        return 30
    return int(TIMER_DURACION_PATH.read_text().strip())


def iniciar_timer():
    TIMER_INICIO_PATH.write_text(str(datetime.now().timestamp()))


def leer_tiempo_restante():
    duracion = leer_timer_duracion()

    if not TIMER_INICIO_PATH.exists():
        return duracion

    inicio = float(TIMER_INICIO_PATH.read_text().strip())
    transcurrido = int(datetime.now().timestamp() - inicio)

    restante = duracion - transcurrido

    return max(restante, 0)    

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

        duracion_timer = st.number_input(
            "Tiempo por pregunta (segundos)",
            min_value=10,
            max_value=300,
            value=leer_timer_duracion(),
            step=5
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

                preguntas_temp.columns = (
                    preguntas_temp.columns
                    .str.strip()
                    .str.lower()
                )

                primera_pregunta = str(
                    preguntas_temp.iloc[0]["id"]
                )

                ESTADO_PATH.write_text(primera_pregunta)

                guardar_estado_visualizacion("votando")

                guardar_timer_duracion(duracion_timer)

                iniciar_timer()

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

    if "nombre_alumno" not in st.session_state:
        st.session_state["nombre_alumno"] = ""

    if st.session_state["nombre_alumno"] == "":

        nombre_ingresado = st.text_input("Nombre")

        if nombre_ingresado.strip():
            st.session_state["nombre_alumno"] = nombre_ingresado.strip()
            st.rerun()

        nombre = ""

    else:

            nombre = st.session_state["nombre_alumno"]

            mensaje_respuesta = ""

            if (
                "mensaje_exito_pregunta_id"
                in st.session_state
                and st.session_state["mensaje_exito_pregunta_id"]
                == str(pregunta["id"])
            ):

                mensaje_respuesta = "  ✅ Respuesta registrada"

            st.info(
                f"Alumno: {nombre}"
                f"{mensaje_respuesta}"
            )

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

    tiempo_restante_alumno = (
        leer_tiempo_restante()
    )

    respuesta = st.radio(
            "Seleccione una alternativa:",
            list(opciones.keys()),
            format_func=lambda x: f"{x}. {opciones[x]}",
            index=None,
            disabled=(tiempo_restante_alumno == 0)
    )

    minutos = tiempo_restante_alumno // 60
    segundos = tiempo_restante_alumno % 60

    texto_timer = f"{minutos:02}:{segundos:02}"

    if tiempo_restante_alumno > 10:

        st.success(
                f"Tiempo restante: {texto_timer}"
        )

    elif tiempo_restante_alumno > 5:

            st.warning(
                f"Tiempo restante: {texto_timer}"
            )

    elif tiempo_restante_alumno > 0:

        st.error(
                f"Tiempo restante: {texto_timer}"
        )

    else:

            estado_visualizacion_alumno = (
                leer_estado_visualizacion()
    )

            if estado_visualizacion_alumno == "correcta":

                correcta_alumno = str(
                    pregunta.get("correcta", "")
                ).strip().upper()

                st.success(
                    f"Respuesta correcta: {correcta_alumno}"
                )

            else:

                st.error(
                        "Tiempo finalizado"
                )


else:

    respuesta = None


# -----------------------------
# GUARDAR RESPUESTA
# -----------------------------

if (
    not modo_profesor
    and tiempo_restante_alumno > 0
    and st.button("Enviar respuesta")
):

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

    st.divider()

    if RESPUESTAS_PATH.exists():
        respuestas = pd.read_csv(RESPUESTAS_PATH)
    else:
        respuestas = pd.DataFrame()

    if (
        not respuestas.empty
        and "pregunta_id" in respuestas.columns
    ):
        respuestas_pregunta = respuestas[
            respuestas["pregunta_id"].astype(str) == str(pregunta["id"])
        ]

        alumnos_registrados = respuestas[
            respuestas["pregunta_id"].astype(str) == "0"
        ]["nombre"].nunique()

    else:
        respuestas_pregunta = pd.DataFrame()
        alumnos_registrados = 0

    if (
        not respuestas_pregunta.empty
        and "nombre" in respuestas_pregunta.columns
    ):
        respondieron_actual = respuestas_pregunta["nombre"].nunique()
    else:
        respondieron_actual = 0

    st.subheader(f"Pregunta {pregunta['id']}")

    st.write(
        f"Respuestas: "
        f"{respondieron_actual}/"
        f"{alumnos_registrados}"
    )

    tiempo_restante = leer_tiempo_restante()

    duracion_total = leer_timer_duracion()

    minutos = tiempo_restante // 60
    segundos = tiempo_restante % 60

    texto_timer = f"{minutos:02}:{segundos:02}"

    if tiempo_restante > 10:

        st.success(
            f"Tiempo restante: {texto_timer}"
    )

    elif tiempo_restante > 5:

        st.warning(
            f"Tiempo restante: {texto_timer}"
    )

    elif tiempo_restante > 0:

        st.error(
            f"Tiempo restante: {texto_timer}"
    )

    else:

        st.error(
            "Tiempo finalizado"
        )

    estado_visualizacion = leer_estado_visualizacion()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Mostrar resultados"):
            guardar_estado_visualizacion("resultados")
            st.rerun()

    with col2:
        if st.button("Mostrar correcta"):
            guardar_estado_visualizacion("correcta")
            st.rerun()

    with col3:
            if st.button("Siguiente pregunta"):
                guardar_estado_visualizacion("votando")
                iniciar_timer ()

                indice_actual = ids_preguntas.index(pregunta_id)

                if indice_actual < len(ids_preguntas) - 1:
                    pregunta_id = ids_preguntas[indice_actual + 1]
                    ESTADO_PATH.write_text(pregunta_id)
                    st.rerun()
                else:
                    st.warning("Ya estás en la última pregunta.")

    if (
        respondieron_actual > 0
        and estado_visualizacion != "votando"
    ):

        conteo = (
            respuestas_pregunta["respuesta"]
            .value_counts()
            .reindex(["A", "B", "C", "D"], fill_value=0)
        )

        porcentajes = round(
            conteo / respondieron_actual * 100,
            1
        )

        resultados = pd.DataFrame({
            "Alternativa": conteo.index,
            "Respuestas": conteo.values,
            "Porcentaje": porcentajes.values
        })

        correcta = str(pregunta.get("correcta", "")).strip().upper()

        if (
            estado_visualizacion == "correcta"
            and correcta in ["A", "B", "C", "D"]
        ):
            resultados["Estado"] = resultados["Alternativa"].apply(
                lambda x: "Correcta" if x == correcta else "Otra"
            )
        else:
            resultados["Estado"] = "Otra"

        correctas = conteo.get(correcta, 0)

        if estado_visualizacion == "correcta":
            mensaje_correcta = (
                    f"Respuesta correcta: {correcta} "
                    f"({correctas} respuestas)"
            )
        else:
                mensaje_correcta = "&nbsp;"

        st.markdown(
                f"""
                <div style="
                        min-height: 48px;
                        display: flex;
                        align-items: center;
                        font-size: 28px;
                        font-weight: 600;
                ">
                        {mensaje_correcta}
                </div>
                """,
                unsafe_allow_html=True
        )

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
                "Alternativa": ["A", "B", "C", "D"]
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
        st.info("Votación en curso. El gráfico está oculto.")
