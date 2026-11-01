# Lola Mancebo Olivares
# Jimena Zubizarreta Gómez

from db import conexion_mysql


def recomendar_populares_no_consumidos(reviewer_id, categoria):
    """
    Genera una lista de recomendaciones para un usuario concreto dentro de una categoría.

    La idea es sencilla: buscamos los artículos más populares (más número de reviews)
    dentro de la categoría indicada, pero excluyendo aquellos que el usuario ya ha
    consumido previamente.

    Además de la popularidad, también se calcula el rating medio para poder ordenar
    mejor los resultados en caso de empate.
    """
    conexion = conexion_mysql()

    try:
        with conexion.cursor() as cursor:

            # La consulta hace varias cosas a la vez:
            # 1. Filtra por categoría
            # 2. Excluye los artículos que ya ha valorado el usuario
            # 3. Calcula popularidad (COUNT) y calidad (AVG rating)
            # 4. Agrupa por producto
            # 5. Ordena primero por popularidad y luego por rating medio
            consulta = """
            SELECT 
                p.asin,
                p.categoria,
                COUNT(*) AS popularidad,
                AVG(r.overall) AS rating_medio
            FROM reviews r
            JOIN productos p ON r.asin = p.asin
            WHERE p.categoria = %s
              AND p.asin NOT IN (
                  SELECT asin
                  FROM reviews
                  WHERE reviewer_id = %s
              )
            GROUP BY p.asin, p.categoria
            ORDER BY popularidad DESC, rating_medio DESC
            LIMIT 10
            """

            # Ejecutamos la consulta pasando los parámetros de forma segura
            cursor.execute(consulta, (categoria, reviewer_id))

            # Recuperamos todos los resultados (top 10)
            resultados = cursor.fetchall()

            return resultados

    finally:
        # Cerramos siempre la conexión para evitar fugas de recursos
        conexion.close()


def mostrar_recomendaciones(resultados, reviewer_id, categoria):
    """
    Muestra las recomendaciones por pantalla de forma clara y legible.

    Se formatea la salida para que sea fácil interpretar cada recomendación,
    incluyendo identificador del producto, categoría, popularidad y rating medio.
    """
    print(f"\nRecomendaciones para el usuario {reviewer_id} en la categoría {categoria}:\n")

    # Si no hay resultados, informamos al usuario
    if not resultados:
        print("No se han encontrado recomendaciones para ese usuario y esa categoría.")
        return

    # Recorremos los resultados y los mostramos numerados
    for i, fila in enumerate(resultados, start=1):
        asin = fila[0]
        categoria = fila[1]
        popularidad = fila[2]
        rating_medio = fila[3]

        # Se muestra tanto la popularidad como el rating medio para dar contexto
        print(
            f"{i}. ASIN: {asin} | Categoría: {categoria} | "
            f"Popularidad: {popularidad} reviews | Rating medio: {rating_medio:.2f}"
        )


if __name__ == "__main__":
    # Pedimos por teclado el usuario y la categoría sobre la que generar recomendaciones
    reviewer_id = input("Introduce el reviewer_id del usuario: ")
    categoria = input("Introduce la categoría: ")

    # Generamos las recomendaciones
    resultados = recomendar_populares_no_consumidos(reviewer_id, categoria)

    # Mostramos los resultados por pantalla
    mostrar_recomendaciones(resultados, reviewer_id, categoria)