# Lola Mancebo Olivares
# Jimena Zubizarreta Gómez

"""
OPCIONAL: VISUALIZACIÓN INTERACTIVA CON STREAMLIT

Dashboard web equivalente al menú de menu_visualizacion.py: un desplegable
para elegir la categoría y otro para elegir la gráfica.

Uso:
    streamlit run src/mejora_visualizacion.py
"""

from collections import Counter
from datetime import datetime

import matplotlib.pyplot as plt
import streamlit as st
from wordcloud import WordCloud

from db import coleccion_mongo, conexion_mysql


def consulta_mysql(sql, parametros=None):
    """
    Ejecuta una consulta en MySQL y devuelve todas las filas.
    Abre y cierra la conexión en cada llamada.
    """
    conn = conexion_mysql()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchall()
    finally:
        conn.close()


def filtro_categoria(tipo):
    """
    Devuelve el JOIN, la condición WHERE y los parámetros necesarios para
    filtrar por categoría. Si el tipo es "todo", no se filtra.
    """
    if tipo == "todo":
        return "", "", ()
    return "JOIN productos p ON r.asin = p.asin", "AND p.categoria = %s", (tipo,)


@st.cache_data(show_spinner=False)
def obtener_categorias():
    """
    Obtiene las categorías disponibles en la tabla productos.
    """
    return [fila[0] for fila in consulta_mysql("SELECT DISTINCT categoria FROM productos")]


@st.cache_data(show_spinner="Consultando MySQL...")
def datos_reviews_por_anio(tipo):
    """Número de reviews por año, opcionalmente filtrado por categoría."""
    join, where, params = filtro_categoria(tipo)
    return consulta_mysql(f"""
        SELECT YEAR(r.review_time), COUNT(*)
        FROM reviews r {join}
        WHERE r.review_time IS NOT NULL {where}
        GROUP BY YEAR(r.review_time)
        ORDER BY YEAR(r.review_time)
    """, params)


@st.cache_data(show_spinner="Consultando MySQL...")
def datos_popularidad(tipo):
    """Número de reviews por artículo, de mayor a menor."""
    join, where, params = filtro_categoria(tipo)
    filas = consulta_mysql(f"""
        SELECT r.asin, COUNT(*)
        FROM reviews r {join}
        WHERE 1 = 1 {where}
        GROUP BY r.asin
        ORDER BY COUNT(*) DESC
    """, params)
    return [fila[1] for fila in filas]


@st.cache_data(show_spinner="Consultando MySQL...")
def datos_notas(tipo):
    """Número de reviews por nota (overall)."""
    join, where, params = filtro_categoria(tipo)
    return consulta_mysql(f"""
        SELECT r.overall, COUNT(*)
        FROM reviews r {join}
        WHERE 1 = 1 {where}
        GROUP BY r.overall
        ORDER BY r.overall
    """, params)


@st.cache_data(show_spinner="Consultando MySQL...")
def datos_evolucion_temporal(tipo):
    """Instantes (unix time) de todas las reviews, en orden cronológico."""
    join, where, params = filtro_categoria(tipo)
    filas = consulta_mysql(f"""
        SELECT r.unix_review_time
        FROM reviews r {join}
        WHERE r.unix_review_time IS NOT NULL {where}
        ORDER BY r.unix_review_time
    """, params)
    return [fila[0] for fila in filas]


@st.cache_data(show_spinner="Consultando MySQL...")
def datos_reviews_por_usuario():
    """Distribución del número de reviews por usuario (sin filtrar por categoría)."""
    filas = consulta_mysql("SELECT reviewer_id, COUNT(*) FROM reviews GROUP BY reviewer_id")
    conteo = Counter(fila[1] for fila in filas)
    return sorted(conteo.items())


@st.cache_data(show_spinner="Consultando MySQL...")
def datos_media_por_articulo():
    """Media de puntuación de cada artículo."""
    return [float(fila[1]) for fila in consulta_mysql("SELECT asin, AVG(overall) FROM reviews GROUP BY asin")]


@st.cache_data(show_spinner="Consultando MongoDB...")
def datos_nube_palabras(tipo):
    """Texto con las palabras de más de 3 letras del campo summary de una categoría."""
    client, collection = coleccion_mongo()
    try:
        palabras = []
        for doc in collection.find({"categoria": tipo}, {"summary": 1}):
            if doc.get("summary"):
                palabras.extend(p for p in doc["summary"].split() if len(p) > 3)
        return " ".join(palabras)
    finally:
        client.close()


def grafica_barras(x, y, titulo, xlabel, ylabel):
    """Dibuja un gráfico de barras en Streamlit."""
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x, y)
    ax.set_title(titulo)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    st.pyplot(fig)


# --- Interfaz -----------------------------------------------------------------
# set_page_config debe ser la primera llamada de Streamlit
st.set_page_config(page_title="Reviews de Amazon", layout="wide")

st.title("REVIEWS DE AMAZON")
st.markdown("Aplicación interactiva para explorar la información de las reviews de Amazon.")

try:
    categorias = obtener_categorias()
except Exception as e:
    st.error(f"No se ha podido conectar a MySQL. ¿Has ejecutado load_data.py? Detalle: {e}")
    st.stop()

tipo = st.selectbox("Selecciona tipo de producto", ["todo"] + categorias)

opcion = st.selectbox("Selecciona gráfica", [
    "Evolución de reviews por año",
    "Popularidad de artículos",
    "Histograma de notas",
    "Evolución temporal acumulada",
    "Reviews por usuario",
    "Nube de palabras",
    "Media puntuaciones por artículo",
])

if opcion == "Evolución de reviews por año":
    datos = datos_reviews_por_anio(tipo)
    grafica_barras([f[0] for f in datos], [f[1] for f in datos],
                   f"Reviews por año ({tipo})", "Año", "Número de reviews")

elif opcion == "Popularidad de artículos":
    popularidad = datos_popularidad(tipo)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(popularidad)
    ax.set_title(f"Popularidad de los artículos ({tipo})")
    ax.set_xlabel("Artículos ordenados por popularidad")
    ax.set_ylabel("Número de reviews")
    st.pyplot(fig)

elif opcion == "Histograma de notas":
    datos = datos_notas(tipo)
    grafica_barras([f[0] for f in datos], [f[1] for f in datos],
                   f"Reviews por nota ({tipo})", "Nota", "Número de reviews")

elif opcion == "Evolución temporal acumulada":
    tiempos = datos_evolucion_temporal(tipo)
    fechas = [datetime.fromtimestamp(t) for t in tiempos]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(fechas, range(1, len(fechas) + 1))
    ax.set_title(f"Evolución acumulada de las reviews ({tipo})")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Número de reviews hasta ese momento")
    st.pyplot(fig)

elif opcion == "Reviews por usuario":
    st.caption("Esta gráfica no distingue por tipo de producto.")
    datos = datos_reviews_por_usuario()
    grafica_barras([f[0] for f in datos], [f[1] for f in datos],
                   "Reviews por usuario", "Número de reviews", "Número de usuarios")

elif opcion == "Nube de palabras":
    if tipo == "todo":
        st.warning("Selecciona una categoría para la nube de palabras.")
    else:
        texto = datos_nube_palabras(tipo)
        if texto:
            wc = WordCloud(width=800, height=400, background_color="white").generate(texto)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wc)
            ax.axis("off")
            st.pyplot(fig)
        else:
            st.info("No hay resúmenes para esta categoría.")

elif opcion == "Media puntuaciones por artículo":
    st.caption("Esta gráfica no distingue por tipo de producto.")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(datos_media_por_articulo(), bins=20)
    ax.set_title("Media de puntuaciones por artículo")
    ax.set_xlabel("Media")
    ax.set_ylabel("Número de artículos")
    st.pyplot(fig)
