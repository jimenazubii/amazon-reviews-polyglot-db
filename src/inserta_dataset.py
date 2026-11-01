# Lola Mancebo Olivares
# Jimena Zubizarreta Gómez

"""
PARTE 4: NUEVOS DATOS

Inserta de forma incremental un nuevo dataset (por defecto, Grocery and
Gourmet Food) sobre la base de datos ya construida con load_data.py, sin
reconstruir nada desde cero.

Incluye control de duplicados: si el script se ejecuta varias veces, las
reviews que ya existen no se vuelven a insertar.

Uso:
    python src/inserta_dataset.py
"""

from configuracion import batch_size, nuevo_dataset
from db import coleccion_mongo, conexion_mysql, parsear_review
from load_data import insertar_datos_mongo, insertar_datos_mysql


def existe_review_mysql(cursor, reviewer_id, asin, unix_review_time):
    """
    Comprueba si una review ya existe en MySQL.

    Una review queda identificada por la combinación de
    reviewer_id, asin y unix_review_time.
    """
    cursor.execute(
        """
        SELECT 1
        FROM reviews
        WHERE reviewer_id = %s AND asin = %s AND unix_review_time = %s
        LIMIT 1
        """,
        (reviewer_id, asin, unix_review_time),
    )
    return cursor.fetchone() is not None


def insertar_dataset_incremental(categoria, ruta_fichero):
    """
    Inserta un nuevo dataset sobre la base de datos ya existente,
    manteniendo la separación MySQL (estructurado) / MongoDB (texto).
    """
    if not ruta_fichero.exists():
        print(f"No se encuentra el fichero {ruta_fichero} (revisa DATA_DIR en .env).")
        return

    conexion = conexion_mysql()
    mongo_client, collection = coleccion_mongo()

    total_reviews = reviews_nuevas = reviews_duplicadas = 0
    batch_users, batch_products, batch_reviews, batch_mongo = [], [], [], []

    # Claves de las reviews añadidas en esta ejecución: detecta también
    # duplicados dentro del propio fichero que aún no se han insertado.
    vistas = set()

    try:
        with open(ruta_fichero, "r", encoding="utf-8") as fichero, conexion.cursor() as cursor:
            for linea in fichero:
                usuario, producto, review, documento = parsear_review(linea, categoria)
                total_reviews += 1

                # Usuarios y productos: el duplicado se controla con la clave
                # primaria y ON DUPLICATE KEY UPDATE.
                batch_users.append(usuario)
                batch_products.append(producto)

                clave = (review[0], review[1], review[5])  # reviewer_id, asin, unix_review_time
                if clave in vistas or existe_review_mysql(cursor, *clave):
                    reviews_duplicadas += 1
                else:
                    vistas.add(clave)
                    batch_reviews.append(review)
                    batch_mongo.append(documento)
                    reviews_nuevas += 1

                if total_reviews % batch_size == 0:
                    insertar_datos_mysql(conexion, batch_users, batch_products, batch_reviews)
                    insertar_datos_mongo(collection, batch_mongo)
                    print(f"{total_reviews} reviews procesadas...", flush=True)

            # Último lote pendiente
            insertar_datos_mysql(conexion, batch_users, batch_products, batch_reviews)
            insertar_datos_mongo(collection, batch_mongo)

        print("Inserción del nuevo dataset completada correctamente.")
        print(f"Reviews leídas: {total_reviews}")
        print(f"Reviews nuevas insertadas: {reviews_nuevas}")
        print(f"Reviews duplicadas detectadas: {reviews_duplicadas}")

    except Exception as e:
        conexion.rollback()
        print(f"Error durante la inserción del nuevo dataset: {e}")

    finally:
        conexion.close()
        mongo_client.close()


if __name__ == "__main__":
    insertar_dataset_incremental(*nuevo_dataset)
