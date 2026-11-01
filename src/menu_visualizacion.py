# Lola Mancebo Olivares
# Jimena Zubizarreta Gómez

# PARTE 2: APLICACIÓN PYTHON PARA EL ACCESO Y VISUALIZACIÓN DE DATOS 

import matplotlib.pyplot as plt
from collections import Counter
from wordcloud import WordCloud
from db import coleccion_mongo, conexion_mysql


def conectar_mysql():
    """
    Devuelve una conexión a la base de datos MySQL.
    """
    return conexion_mysql()


def conectar_mongo():
    """
    Devuelve la colección de MongoDB.
    """
    _, collection = coleccion_mongo()
    return collection


def obtener_categorias():
    """
    Obtiene las categorías disponibles.
    """
    conn = conectar_mysql()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT categoria FROM productos")
    categorias = [fila[0] for fila in cursor.fetchall()]

    cursor.close()
    conn.close()

    return categorias


def evolucion_reviews_por_anio():
    """
    Muestra un histograma con el número de reviews por año.
    """
    # Pedir al usuario el tipo de review que se quiere mostrar 
    categorias = obtener_categorias()

    while True:
        print("Categorías disponibles:", categorias)
        tipo = input("Introduce tipo de producto o 'todo': ")
        if tipo.lower() == "todo" or tipo in categorias:
            break
        else:
            print("Categoría no válida")

    # Conseguir la información mediante la conexión a la base de datos
    conn = conectar_mysql()
    cursor = conn.cursor()

    if tipo.lower() == "todo":
        cursor.execute("""
        SELECT YEAR(review_time), COUNT(*)
        FROM reviews
        WHERE review_time IS NOT NULL
        GROUP BY YEAR(review_time)
        ORDER BY YEAR(review_time)
        """)
        # YEAR: extrae el año
        # COUNT: cuenta reviews por año
        # GROUP BY: agrupa por año
        # ORDER BY: orden cronológico

    else:
        cursor.execute("""
        SELECT YEAR(r.review_time), COUNT(*)
        FROM reviews r
        JOIN productos p ON r.asin = p.asin
        WHERE r.review_time IS NOT NULL AND p.categoria = %s
        GROUP BY YEAR(r.review_time)
        ORDER BY YEAR(r.review_time)
        """, (tipo,))
        # JOIN: une reviews con productos
        # WHERE: filtra por categoría
        # COUNT: número de reviews por año

    datos = cursor.fetchall()

    anios = [fila[0] for fila in datos]
    counts = [fila[1] for fila in datos]

    plt.bar(anios, counts)
    plt.title(f"Reviews por año de {tipo.lower()}")
    plt.xlabel("Años")
    plt.ylabel("Número de reviews")
    plt.show()

    cursor.close()
    conn.close()


def evolucion_popularidad_articulos():
    """
    Muestra una curva de los artículos ordenados de mayor a 
    menor popularidad (número de reviews).
    """

    # Obtener la curva por tipo de producto o por todos a la vez 
    categorias = obtener_categorias()

    while True:
        print("Categorías disponibles:", categorias)
        tipo = input("Introduce tipo de producto o 'todo': ")
        if tipo.lower() == "todo" or tipo in categorias:
            break
        else:
            print("Categoría no válida")

    conn = conectar_mysql()
    cursor = conn.cursor()

    if tipo.lower() == "todo":
        cursor.execute("""
        SELECT asin, COUNT(*)
        FROM reviews
        GROUP BY asin
        ORDER BY COUNT(*) DESC
        """)
        # COUNT: número de reviews por artículo
        # GROUP BY: agrupa por asin
        # ORDER BY DESC: orden de más popular a menos

    else:
        cursor.execute("""
        SELECT r.asin, COUNT(*)
        FROM reviews r
        JOIN productos p ON r.asin = p.asin
        WHERE p.categoria = %s
        GROUP BY r.asin
        ORDER BY COUNT(*) DESC
        """, (tipo,))
        # JOIN: relaciona tablas
        # WHERE: filtra categoría
        # COUNT: calcula popularidad

    datos = cursor.fetchall()

    popularidad = [fila[1] for fila in datos]

    plt.plot(popularidad)
    plt.title(f"Evolución de la popularidad de {tipo.lower()}")
    plt.xlabel("Artículos")
    plt.ylabel("Número de reviews")
    plt.show()

    cursor.close()
    conn.close()


def histograma_por_nota():
    """
    Muestra un histograma con la distribución de notas (overall).
    """

    # Permite al usuario calcular el histograma para un artículo en concreto 
    # Si el artículo introducido no existe, indicarlo 

    conn = conectar_mysql()
    cursor = conn.cursor()

    while True:
        asin = input("Introduce asin o 'todo': ")

        if asin.lower() == "todo":
            break

        cursor.execute("SELECT COUNT(*) FROM reviews WHERE asin = %s", (asin,))
        if cursor.fetchone()[0] > 0:
            break
        else:
            print("Artículo no existe")

    if asin.lower() == "todo":
        cursor.execute("""
        SELECT overall, COUNT(*)
        FROM reviews
        GROUP BY overall
        ORDER BY overall
        """)
        # GROUP BY overall: agrupa por nota
        # COUNT: frecuencia de cada nota

    else:
        cursor.execute("""
        SELECT overall, COUNT(*)
        FROM reviews
        WHERE asin = %s
        GROUP BY overall
        ORDER BY overall
        """, (asin,))
        # WHERE: filtra artículo
        # COUNT: frecuencia de notas

    datos = cursor.fetchall()

    notas = [fila[0] for fila in datos]
    counts = [fila[1] for fila in datos]

    plt.bar(notas, counts)
    plt.title(f"Reviews por nota de {asin.lower()}")
    plt.xlabel("Nota")
    plt.ylabel("Número de reviews")
    plt.show()

    cursor.close()
    conn.close()


def evolucion_reviews_temporal():
    """
    Muestra la evolución acumulada de reviews a lo largo del tiempo.
    """

    # Mostrar la evolución para cada tipo de producto
    categorias = obtener_categorias()

    while True:
        print("Categorías disponibles:", categorias)
        tipo = input("Introduce tipo de producto o 'todo': ")
        if tipo.lower() == "todo" or tipo in categorias:
            break
        else:
            print("Categoría no válida")

    conn = conectar_mysql()
    cursor = conn.cursor()

    if tipo.lower() == "todo":
        cursor.execute("""
        SELECT unix_review_time
        FROM reviews
        WHERE unix_review_time IS NOT NULL
        ORDER BY unix_review_time
        """)
        # ORDER BY: ordena cronológicamente

    else:
        cursor.execute("""
        SELECT r.unix_review_time
        FROM reviews r
        JOIN productos p ON r.asin = p.asin
        WHERE r.unix_review_time IS NOT NULL AND p.categoria = %s
        ORDER BY r.unix_review_time
        """, (tipo,))
        # JOIN: une tablas
        # WHERE: filtra categoría
        # ORDER BY: orden temporal

    datos = cursor.fetchall()

    tiempos = [fila[0] for fila in datos]

    acumulado = list(range(1, len(tiempos) + 1))

    plt.plot(tiempos, acumulado)
    plt.title(f"Evolución de las reviews a lo largo del tiempo de {tipo.lower()}")
    plt.xlabel("Tiempo")
    plt.ylabel("Número de reviews hasta ese momento")
    plt.show()

    cursor.close()
    conn.close()


def histograma_reviews_usuario():
    """
    Muestra el número de reviews por usuario, sin distinguir el tipo de producto.
    """

    conn = conectar_mysql()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT reviewer_id, COUNT(*)
    FROM reviews
    GROUP BY reviewer_id
    """)
    # GROUP BY reviewer_id: agrupa por usuario
    # COUNT: número de reviews por usuario

    datos = cursor.fetchall()

    reviews_por_usuario = [fila[1] for fila in datos]

    conteo = Counter(reviews_por_usuario)

    x = list(conteo.keys())
    y = list(conteo.values())

    plt.bar(x, y)
    plt.title("Reviews por usuario")
    plt.xlabel("Número de reviews")
    plt.ylabel("Número de usuarios")
    plt.show()

    cursor.close()
    conn.close()


def nube_palabras():
    """
    Genera una nube de palabras en función de la categoría considerando el 
    campo summary de MongoDB.
    """

    # Para eliminar conectores, solo tener en cuenta palabras con len > 3 
    categorias = obtener_categorias()

    while True:
        print("Categorías disponibles:", categorias)
        tipo = input("Introduce tipo de producto: ")
        if tipo in categorias:
            break
        else:
            print("Categoría no válida")

    collection = conectar_mongo()

    textos = []

    for doc in collection.find({"categoria": tipo}, {"summary": 1}):
        # Filtra documentos por categoría
        if doc.get("summary"):
            palabras = doc["summary"].split()
            palabras = [p for p in palabras if len(p) > 3]
            textos.extend(palabras)

    texto_final = " ".join(textos)

    wc = WordCloud(width=800, height=400).generate(texto_final)

    plt.imshow(wc)
    plt.axis("off")
    plt.title(f"Nube de palabras del producto {tipo}")
    plt.show()


def grafica_extra():
    """
    Gráfica que muestra datos distintos a los mostrados anteriormente. 
    Ejemplo: media de puntuaciones por artículo.
    """

    conn = conectar_mysql()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT asin, AVG(overall)
    FROM reviews
    GROUP BY asin
    """)
    # AVG(overall): media de notas
    # GROUP BY asin: por artículo

    datos = cursor.fetchall()

    medias = [fila[1] for fila in datos]

    plt.hist(medias)
    plt.title("Media de puntuaciones por artículo")
    plt.xlabel("Media")
    plt.ylabel("Frecuencia")
    plt.show()

    cursor.close()
    conn.close()


if __name__ == "__main__":
    # El menú se repite hasta que el usuario seleccione la opción de salir 
    while True: 
        print("\n--- MENÚ VISUALIZACIÓN ---")
        print("1. Evolución de reviews por año")
        print("2. Popularidad de artículos")
        print("3. Histograma de notas")
        print("4. Evolución temporal acumulada")
        print("5. Reviews por usuario")
        print("6. Nube de palabras")
        print("7. Media puntuaciones por artículo")
        print("0. Salir")

        opcion = input("Elige una opción: ")

        if opcion == "1":
            evolucion_reviews_por_anio()

        elif opcion == "2":
            evolucion_popularidad_articulos()

        elif opcion == "3":
            histograma_por_nota()

        elif opcion == "4":
            evolucion_reviews_temporal()

        elif opcion == "5":
            histograma_reviews_usuario()

        elif opcion == "6":
            nube_palabras()

        elif opcion == "7":
            grafica_extra()

        elif opcion == "0":
            print("Saliendo...")
            break

        else:
            print("Opción no válida")