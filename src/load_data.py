# Lola Mancebo Olivares
# Jimena Zubizarreta Gómez

"""
PARTE 1: DISEÑO Y CARGA DE DATOS

Crea la base de datos MySQL y la colección de MongoDB y carga los cuatro
datasets de reviews definidos en configuracion.py.

Los ficheros se procesan línea a línea (nunca se cargan completos en memoria)
y las inserciones se agrupan en lotes para que la carga sea eficiente.

Uso:
    python src/load_data.py
"""

from configuracion import batch_size, datasets, mysql_database
from db import coleccion_mongo, conexion_mysql, parsear_review


def crear_mysql_database():
    """
    Crea la base de datos MySQL si todavía no existe.

    Esto permite que el script pueda ejecutarse desde cero sin necesidad
    de crear manualmente la base de datos antes de empezar.
    """
    conexion = conexion_mysql(con_base_datos=False)

    with conexion.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {mysql_database} "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )

    conexion.commit()
    conexion.close()


def crear_tablas_sql(conexion):
    """
    Crea las tablas principales del modelo relacional.

    El diseño separa la información en tres tablas:
    - usuarios
    - productos
    - reviews

    De esta forma se evita redundancia, ya que un mismo usuario puede tener
    reviews en varias categorías. Además, se crean índices sobre los campos
    de la tabla reviews más usados en las consultas.
    """
    create_users = """
    CREATE TABLE IF NOT EXISTS usuarios (
        reviewer_id VARCHAR(30) PRIMARY KEY,
        reviewer_name TEXT
    )
    """

    create_products = """
    CREATE TABLE IF NOT EXISTS productos (
        asin VARCHAR(20) PRIMARY KEY,
        categoria VARCHAR(50) NOT NULL
    )
    """

    create_reviews = """
    CREATE TABLE IF NOT EXISTS reviews (
        review_id BIGINT AUTO_INCREMENT PRIMARY KEY,
        reviewer_id VARCHAR(30) NOT NULL,
        asin VARCHAR(20) NOT NULL,
        overall FLOAT,
        helpful_yes INT,
        helpful_total INT,
        unix_review_time BIGINT,
        review_time DATE,
        FOREIGN KEY (reviewer_id) REFERENCES usuarios(reviewer_id),
        FOREIGN KEY (asin) REFERENCES productos(asin)
    )
    """

    create_indexes = [
        "CREATE INDEX idx_reviews_reviewer ON reviews(reviewer_id)",
        "CREATE INDEX idx_reviews_asin ON reviews(asin)",
        "CREATE INDEX idx_reviews_time ON reviews(review_time)",
    ]

    with conexion.cursor() as cursor:
        cursor.execute(create_users)
        cursor.execute(create_products)
        cursor.execute(create_reviews)

        # Los índices se crean dentro de un try/except para que el script no falle
        # si ya existían de una ejecución anterior.
        for query in create_indexes:
            try:
                cursor.execute(query)
            except Exception:
                pass

    conexion.commit()


def vaciar_tablas_sql(conexion):
    """
    Vacía las tablas de MySQL antes de volver a cargar todos los datos.

    Como existe dependencia entre tablas mediante claves foráneas,
    se desactivan temporalmente las restricciones para poder truncarlas.
    """
    with conexion.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE reviews")
        cursor.execute("TRUNCATE TABLE productos")
        cursor.execute("TRUNCATE TABLE usuarios")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    conexion.commit()


def insertar_datos_mysql(conexion, batch_users, batch_products, batch_reviews):
    """
    Inserta en MySQL los datos acumulados en memoria en forma de lotes.

    Trabajar por lotes mejora mucho el rendimiento frente a insertar fila a fila.
    Usuarios y productos usan ON DUPLICATE KEY UPDATE porque pueden repetirse
    entre lotes y entre datasets; cada review es un registro independiente.
    """
    if not batch_users and not batch_products and not batch_reviews:
        return

    with conexion.cursor() as cursor:
        if batch_users:
            cursor.executemany(
                """
                INSERT INTO usuarios (reviewer_id, reviewer_name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE reviewer_name = VALUES(reviewer_name)
                """,
                batch_users,
            )

        if batch_products:
            cursor.executemany(
                """
                INSERT INTO productos (asin, categoria)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE categoria = VALUES(categoria)
                """,
                batch_products,
            )

        if batch_reviews:
            cursor.executemany(
                """
                INSERT INTO reviews (
                    reviewer_id, asin, overall, helpful_yes, helpful_total,
                    unix_review_time, review_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                batch_reviews,
            )

    conexion.commit()

    # Vaciamos las listas para reutilizarlas en el siguiente lote
    batch_users.clear()
    batch_products.clear()
    batch_reviews.clear()


def insertar_datos_mongo(collection, batch_mongo):
    """
    Inserta en MongoDB los documentos acumulados en el lote actual.
    """
    if batch_mongo:
        collection.insert_many(batch_mongo)
        batch_mongo.clear()


def procesar_datos(conexion, collection, categoria, ruta_fichero):
    """
    Procesa un dataset JSON línea a línea e inserta su contenido en MySQL y MongoDB.

    - MySQL almacena usuarios, productos y datos numéricos de las reviews.
    - MongoDB almacena el texto de la review y su resumen.
    """
    batch_users, batch_products, batch_reviews, batch_mongo = [], [], [], []
    total_reviews = 0

    # Se recorre el fichero línea a línea para no cargar el dataset entero en memoria
    with open(ruta_fichero, "r", encoding="utf-8") as fichero:
        for linea in fichero:
            usuario, producto, review, documento = parsear_review(linea, categoria)

            batch_users.append(usuario)
            batch_products.append(producto)
            batch_reviews.append(review)
            batch_mongo.append(documento)
            total_reviews += 1

            if len(batch_reviews) >= batch_size:
                insertar_datos_mysql(conexion, batch_users, batch_products, batch_reviews)
                insertar_datos_mongo(collection, batch_mongo)

    # Último lote pendiente, normalmente más pequeño que batch_size
    insertar_datos_mysql(conexion, batch_users, batch_products, batch_reviews)
    insertar_datos_mongo(collection, batch_mongo)

    print(f"Dataset {categoria}: {total_reviews} reviews procesadas.")


def main():
    """
    Carga completa de la infraestructura de datos desde cero.
    """
    faltan = [str(ruta) for _, ruta in datasets if not ruta.exists()]
    if faltan:
        print("No se encuentran estos ficheros de datos (revisa DATA_DIR en .env):")
        for ruta in faltan:
            print(f"  - {ruta}")
        return

    print("Creando base de datos MySQL...")
    crear_mysql_database()

    conexion = conexion_mysql()
    mongo_client, collection = coleccion_mongo()

    try:
        print("Creando tablas MySQL...")
        crear_tablas_sql(conexion)

        print("Limpiando tablas MySQL y colección MongoDB...")
        vaciar_tablas_sql(conexion)
        collection.delete_many({})

        for categoria, ruta in datasets:
            print(f"Cargando dataset: {categoria}")
            procesar_datos(conexion, collection, categoria, ruta)

        print("Carga completada correctamente.")

    except Exception as e:
        # Si ocurre un error, se deshacen los cambios pendientes en MySQL
        conexion.rollback()
        print(f"Error durante la carga: {e}")

    finally:
        conexion.close()
        mongo_client.close()


if __name__ == "__main__":
    main()
