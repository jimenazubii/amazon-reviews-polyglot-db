# Lola Mancebo Olivares
# Jimena Zubizarreta Gómez

from db import conexion_mysql, driver_neo4j

# Número de usuarios para el cálculo de similitudes (apartado 4.1).
# Basta con cambiar este valor para usar otro número de usuarios.
NUM_USUARIOS_SIMILITUD = 30

driver = driver_neo4j()


def borrar_grafo():
    with driver.session() as session:
        consulta = "MATCH (n) DETACH DELETE n"
        session.run(consulta)


def probar_conexion_neo4j():
    with driver.session() as session:
        consulta = "RETURN 'Neo4J conectado correctamente' AS mensaje"
        resultado = session.run(consulta)
        for fila in resultado.data():
            print(fila["mensaje"])

def calcular_pearson(ratings_u, ratings_v):
    """
    Calcula la correlación de Pearson entre dos usuarios a partir
    de sus diccionarios de ratings {asin: nota}.
    Solo se tienen en cuenta los artículos puntuados por ambos.
    """
    comunes = set(ratings_u.keys()).intersection(set(ratings_v.keys()))

    if len(comunes) == 0:
        return None

    notas_u = [ratings_u[asin] for asin in comunes]
    notas_v = [ratings_v[asin] for asin in comunes]

    media_u = sum(notas_u) / len(notas_u)
    media_v = sum(notas_v) / len(notas_v)

    numerador = sum((ru - media_u) * (rv - media_v) for ru, rv in zip(notas_u, notas_v))
    denominador_u = sum((ru - media_u) ** 2 for ru in notas_u) ** 0.5
    denominador_v = sum((rv - media_v) ** 2 for rv in notas_v) ** 0.5
    denominador = denominador_u * denominador_v

    if denominador == 0:
        return 0

    return numerador / denominador


def opcion_1_similitudes(driver):
    """
    Obtiene los NUM_USUARIOS_SIMILITUD (por defecto 30) usuarios con más reviews, calcula la similitud de Pearson
    entre ellos y carga el grafo en Neo4J. Después muestra por pantalla el
    usuario con más vecinos.
    """
    conexion = conexion_mysql()

    try:
        with conexion.cursor() as cursor:
            # Obtenemos los N usuarios con más reviews
            consulta_top_usuarios = """
            SELECT 
                u.reviewer_id,
                u.reviewer_name,
                COUNT(*) AS num_reviews
            FROM reviews r
            JOIN usuarios u ON r.reviewer_id = u.reviewer_id
            GROUP BY u.reviewer_id, u.reviewer_name
            ORDER BY num_reviews DESC
            LIMIT %s
            """
            cursor.execute(consulta_top_usuarios, (NUM_USUARIOS_SIMILITUD,))
            top_usuarios = cursor.fetchall()

            if not top_usuarios:
                print("No se han encontrado usuarios.")
                return

            ids_usuarios = [fila[0] for fila in top_usuarios]
            placeholders = ",".join(["%s"] * len(ids_usuarios))

            # Recuperamos las reviews de esos usuarios
            consulta_reviews = f"""
            SELECT
                u.reviewer_id,
                u.reviewer_name,
                r.asin,
                r.overall
            FROM reviews r
            JOIN usuarios u ON r.reviewer_id = u.reviewer_id
            WHERE u.reviewer_id IN ({placeholders})
            """
            cursor.execute(consulta_reviews, ids_usuarios)
            reviews = cursor.fetchall()

        # Construimos una estructura por usuario con sus ratings
        usuarios_info = {}

        for reviewer_id, reviewer_name, asin, overall in reviews:
            if reviewer_id not in usuarios_info:
                usuarios_info[reviewer_id] = {
                    "name": reviewer_name,
                    "ratings": {}
                }

            usuarios_info[reviewer_id]["ratings"][asin] = float(overall)

        # Limpiamos el grafo antes de cargar esta opción
        borrar_grafo()

        # Creamos los nodos de usuario
        with driver.session() as session:
            for reviewer_id, info in usuarios_info.items():
                session.run("""
                    MERGE (u:Usuario {reviewer_id: $reviewer_id})
                    SET u.reviewer_name = $reviewer_name
                """, reviewer_id=reviewer_id, reviewer_name=info["name"])

            # Calculamos similitudes entre pares de usuarios
            ids = list(usuarios_info.keys())

            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    user1 = ids[i]
                    user2 = ids[j]

                    ratings_u = usuarios_info[user1]["ratings"]
                    ratings_v = usuarios_info[user2]["ratings"]

                    comunes = set(ratings_u.keys()).intersection(set(ratings_v.keys()))

                    # Solo almacenamos similitudes si tienen algún artículo en común
                    if len(comunes) > 0:
                        pearson = calcular_pearson(ratings_u, ratings_v)

                        session.run("""
                            MATCH (u1:Usuario {reviewer_id: $user1})
                            MATCH (u2:Usuario {reviewer_id: $user2})
                            MERGE (u1)-[r:SIMILITUD]->(u2)
                            SET r.pearson = $pearson,
                                r.articulos_comunes = $num_comunes
                        """,
                        user1=user1,
                        user2=user2,
                        pearson=pearson,
                        num_comunes=len(comunes)
                        )

            # Consulta para obtener el usuario con más vecinos
            resultado = session.run("""
                MATCH (u:Usuario)-[:SIMILITUD]-(:Usuario)
                WITH u, count(*) AS num_vecinos
                RETURN u.reviewer_id AS reviewer_id,
                       u.reviewer_name AS reviewer_name,
                       num_vecinos
                ORDER BY num_vecinos DESC
                LIMIT 1
            """)

            fila = resultado.single()

            print("Similitudes cargadas en Neo4J correctamente.")
            if fila:
                print(
                    f"El usuario con más vecinos es {fila['reviewer_name']} "
                    f"({fila['reviewer_id']}) con {fila['num_vecinos']} vecinos."
                )

    except Exception as e:
        print(f"Error en la opción 1: {e}")

    finally:
        conexion.close()

def opcion_2_usuario_articulo(driver):
    """
    Pide al usuario una categoría y un número de artículos aleatorios.
    Después carga en Neo4J esos artículos y todos los usuarios que los han puntuado.
    En la relación se almacena la nota y el momento temporal de la review.
    """
    categoria = input("Introduce la categoría (Toys_and_Games, Video_Games, Digital_Music, Musical_Instruments): ")

    try:
        num_articulos = int(input("Introduce el número de artículos aleatorios que quieres mostrar: "))
    except ValueError:
        print("Debes introducir un número entero.")
        return

    conexion = conexion_mysql()

    try:
        with conexion.cursor() as cursor:
            # Primero obtenemos los artículos aleatorios de esa categoría
            consulta_asins = """
            SELECT asin
            FROM productos
            WHERE categoria = %s
            ORDER BY RAND()
            LIMIT %s
            """
            cursor.execute(consulta_asins, (categoria, num_articulos))
            asins = [fila[0] for fila in cursor.fetchall()]

            if not asins:
                print("No se han encontrado artículos para esa categoría.")
                return

            # Construimos la consulta dinámica con tantos %s como artículos tengamos
            placeholders = ",".join(["%s"] * len(asins))

            consulta_reviews = f"""
            SELECT 
                u.reviewer_id,
                u.reviewer_name,
                p.asin,
                p.categoria,
                r.overall,
                r.unix_review_time
            FROM reviews r
            JOIN usuarios u ON r.reviewer_id = u.reviewer_id
            JOIN productos p ON r.asin = p.asin
            WHERE p.asin IN ({placeholders})
            ORDER BY p.asin, u.reviewer_id
            """

            cursor.execute(consulta_reviews, asins)
            resultados = cursor.fetchall()

        if not resultados:
            print("No se han encontrado reviews para los artículos seleccionados.")
            return

        # Limpiamos el grafo antes de cargar los nuevos datos
        borrar_grafo()

        with driver.session() as session:
            for fila in resultados:
                reviewer_id = fila[0]
                reviewer_name = fila[1]
                asin = fila[2]
                categoria_articulo = fila[3]
                overall = fila[4]
                unix_review_time = fila[5]

                consulta_neo4j = """
                MERGE (u:Usuario {reviewer_id: $reviewer_id})
                SET u.reviewer_name = $reviewer_name

                MERGE (a:Articulo {asin: $asin})
                SET a.categoria = $categoria

                MERGE (u)-[r:PUNTUO]->(a)
                SET r.overall = $overall,
                    r.unix_review_time = $unix_review_time
                """

                session.run(
                    consulta_neo4j,
                    reviewer_id=reviewer_id,
                    reviewer_name=reviewer_name,
                    asin=asin,
                    categoria=categoria_articulo,
                    overall=overall,
                    unix_review_time=unix_review_time
                )

        print("Carga en Neo4J completada correctamente.")
        print("Ya puedes consultar los nodos y relaciones en Neo4J Browser.")

    except Exception as e:
        print(f"Error en la opción 2: {e}")

    finally:
        conexion.close()


def opcion_3_usuarios_multicategoria(driver):
    """
    Selecciona los primeros 400 usuarios ordenados por nombre y, de entre ellos,
    carga en Neo4J únicamente aquellos que han puntuado artículos de más de una
    categoría. La relación con cada categoría almacena cuántos artículos de ese
    tipo ha consumido el usuario.
    """
    conexion = conexion_mysql()

    try:
        with conexion.cursor() as cursor:
            # Primero obtenemos los 400 primeros usuarios ordenados por nombre
            consulta_usuarios = """
            SELECT reviewer_id, reviewer_name
            FROM usuarios
            ORDER BY reviewer_name ASC
            LIMIT 400
            """
            cursor.execute(consulta_usuarios)
            usuarios_top = cursor.fetchall()

            if not usuarios_top:
                print("No se han encontrado usuarios.")
                return

            ids_usuarios = [fila[0] for fila in usuarios_top]
            placeholders = ",".join(["%s"] * len(ids_usuarios))

            # Para esos 400 usuarios calculamos cuántos artículos distintos
            # ha consumido cada uno en cada categoría
            consulta_categorias = f"""
            SELECT
                u.reviewer_id,
                u.reviewer_name,
                p.categoria,
                COUNT(DISTINCT r.asin) AS num_articulos
            FROM reviews r
            JOIN usuarios u ON r.reviewer_id = u.reviewer_id
            JOIN productos p ON r.asin = p.asin
            WHERE u.reviewer_id IN ({placeholders})
            GROUP BY u.reviewer_id, u.reviewer_name, p.categoria
            ORDER BY u.reviewer_name ASC, p.categoria ASC
            """
            cursor.execute(consulta_categorias, ids_usuarios)
            datos = cursor.fetchall()

        if not datos:
            print("No se han encontrado datos para los usuarios seleccionados.")
            return

        # Agrupamos por usuario para saber cuántas categorías distintas tiene cada uno
        usuarios_info = {}

        for reviewer_id, reviewer_name, categoria, num_articulos in datos:
            if reviewer_id not in usuarios_info:
                usuarios_info[reviewer_id] = {
                    "reviewer_name": reviewer_name,
                    "categorias": []
                }

            usuarios_info[reviewer_id]["categorias"].append((categoria, num_articulos))

        # Nos quedamos solo con usuarios que tengan más de una categoría distinta
        usuarios_filtrados = {
            reviewer_id: info
            for reviewer_id, info in usuarios_info.items()
            if len(info["categorias"]) > 1
        }

        if not usuarios_filtrados:
            print("No hay usuarios multicategoría entre los primeros 400.")
            return

        # Limpiamos Neo4J antes de cargar esta opción
        borrar_grafo()

        with driver.session() as session:
            for reviewer_id, info in usuarios_filtrados.items():
                reviewer_name = info["reviewer_name"]

                session.run("""
                    MERGE (u:Usuario {reviewer_id: $reviewer_id})
                    SET u.reviewer_name = $reviewer_name
                """, reviewer_id=reviewer_id, reviewer_name=reviewer_name)

                for categoria, num_articulos in info["categorias"]:
                    session.run("""
                        MERGE (c:Categoria {nombre: $categoria})
                    """, categoria=categoria)

                    session.run("""
                        MATCH (u:Usuario {reviewer_id: $reviewer_id})
                        MATCH (c:Categoria {nombre: $categoria})
                        MERGE (u)-[r:INTERACTUA_CON]->(c)
                        SET r.num_articulos = $num_articulos
                    """, reviewer_id=reviewer_id, categoria=categoria, num_articulos=num_articulos)

        print("Usuarios multicategoría cargados en Neo4J correctamente.")

    except Exception as e:
        print(f"Error en la opción 3: {e}")

    finally:
        conexion.close()


def opcion_4_populares_comunes(driver):
    """
    Carga en Neo4J los 5 artículos más populares que tengan menos de 40 reviews,
    junto con todos los usuarios que los han puntuado. Además, crea relaciones
    entre usuarios indicando cuántos artículos de esos 5 tienen en común.
    """
    conexion = conexion_mysql()

    try:
        with conexion.cursor() as cursor:
            # Obtenemos los 5 artículos más populares con menos de 40 reviews
            consulta_articulos = """
            SELECT 
                p.asin,
                p.categoria,
                COUNT(*) AS num_reviews
            FROM reviews r
            JOIN productos p ON r.asin = p.asin
            GROUP BY p.asin, p.categoria
            HAVING COUNT(*) < 40
            ORDER BY num_reviews DESC
            LIMIT 5
            """
            cursor.execute(consulta_articulos)
            articulos_top = cursor.fetchall()

            if not articulos_top:
                print("No se han encontrado artículos que cumplan la condición.")
                return

            asins = [fila[0] for fila in articulos_top]
            placeholders = ",".join(["%s"] * len(asins))

            # Sacamos todas las reviews de esos artículos
            consulta_reviews = f"""
            SELECT
                u.reviewer_id,
                u.reviewer_name,
                p.asin,
                p.categoria,
                r.overall,
                r.unix_review_time
            FROM reviews r
            JOIN usuarios u ON r.reviewer_id = u.reviewer_id
            JOIN productos p ON r.asin = p.asin
            WHERE p.asin IN ({placeholders})
            ORDER BY p.asin, u.reviewer_id
            """
            cursor.execute(consulta_reviews, asins)
            reviews = cursor.fetchall()

        if not reviews:
            print("No se han encontrado reviews para los artículos seleccionados.")
            return

        # Limpiamos el grafo antes de cargar esta opción
        borrar_grafo()

        # Diccionario para luego calcular artículos en común entre usuarios
        usuario_articulos = {}

        with driver.session() as session:
            for fila in reviews:
                reviewer_id = fila[0]
                reviewer_name = fila[1]
                asin = fila[2]
                categoria = fila[3]
                overall = fila[4]
                unix_review_time = fila[5]

                # Guardamos qué artículos ha puntuado cada usuario
                if reviewer_id not in usuario_articulos:
                    usuario_articulos[reviewer_id] = {
                        "name": reviewer_name,
                        "articulos": set()
                    }
                usuario_articulos[reviewer_id]["articulos"].add(asin)

                # Creamos nodos y relación usuario-artículo
                consulta_neo4j = """
                MERGE (u:Usuario {reviewer_id: $reviewer_id})
                SET u.reviewer_name = $reviewer_name

                MERGE (a:Articulo {asin: $asin})
                SET a.categoria = $categoria

                MERGE (u)-[r:PUNTUO]->(a)
                SET r.overall = $overall,
                    r.unix_review_time = $unix_review_time
                """

                session.run(
                    consulta_neo4j,
                    reviewer_id=reviewer_id,
                    reviewer_name=reviewer_name,
                    asin=asin,
                    categoria=categoria,
                    overall=overall,
                    unix_review_time=unix_review_time
                )

            # Ahora calculamos artículos en común entre usuarios
            ids_usuarios = list(usuario_articulos.keys())

            for i in range(len(ids_usuarios)):
                for j in range(i + 1, len(ids_usuarios)):
                    user1 = ids_usuarios[i]
                    user2 = ids_usuarios[j]

                    articulos_comunes = usuario_articulos[user1]["articulos"].intersection(
                        usuario_articulos[user2]["articulos"]
                    )

                    if len(articulos_comunes) > 0:
                        session.run("""
                            MATCH (u1:Usuario {reviewer_id: $user1})
                            MATCH (u2:Usuario {reviewer_id: $user2})
                            MERGE (u1)-[r:TIENE_EN_COMUN]->(u2)
                            SET r.articulos_comunes = $num_comunes
                        """,
                        user1=user1,
                        user2=user2,
                        num_comunes=len(articulos_comunes)
                        )

        print("Artículos populares y artículos en común cargados en Neo4J correctamente.")
        print("Ya puedes consultar los nodos y relaciones en Neo4J Browser.")

    except Exception as e:
        print(f"Error en la opción 4: {e}")

    finally:
        conexion.close()

def menu():
    opcion = ""
    while opcion != "5":
        print("\n--- MENÚ NEO4J ---")
        print("1. Similitudes entre usuarios")
        print("2. Enlaces entre usuarios y artículos")
        print("3. Usuarios con más de un tipo de artículo")
        print("4. Artículos populares y artículos en común")
        print("5. Salir")

        opcion = input("Selecciona una opción: ")

        if opcion == "1":
            opcion_1_similitudes(driver)
        elif opcion == "2":
            opcion_2_usuario_articulo(driver)
        elif opcion == "3":
            opcion_3_usuarios_multicategoria(driver)
        elif opcion == "4":
            opcion_4_populares_comunes(driver)
        elif opcion == "5":
            print("Saliendo del programa...")
        else:
            print("Opción no válida.")


if __name__ == "__main__":
    probar_conexion_neo4j()
    menu()
    driver.close()