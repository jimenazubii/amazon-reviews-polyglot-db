# Lola Mancebo Olivares
# Jimena Zubizarreta Gómez

"""
Funciones comunes de conexión a MySQL, MongoDB y Neo4j, y utilidades
compartidas por varios scripts del proyecto.

Centralizar aquí las conexiones evita repetir el mismo código en cada fichero
y garantiza que todos usan la misma configuración.
"""

from datetime import datetime

import pymongo
import pymysql

from configuracion import (
    mongo_collection,
    mongo_database,
    mongo_uri,
    mysql_database,
    mysql_host,
    mysql_pass,
    mysql_port,
    mysql_user,
    neo4j_password,
    neo4j_uri,
    neo4j_user,
)


def conexion_mysql(con_base_datos=True, autocommit=False):
    """
    Devuelve una conexión a MySQL.

    Si `con_base_datos` es False, se conecta al servidor sin seleccionar
    ninguna base de datos (útil para crearla desde cero).
    Se usa utf8mb4 para soportar correctamente caracteres especiales y emojis.
    """
    parametros = dict(
        host=mysql_host,
        port=mysql_port,
        user=mysql_user,
        password=mysql_pass,
        charset="utf8mb4",
        autocommit=autocommit,
    )
    if con_base_datos:
        parametros["database"] = mysql_database
    return pymysql.connect(**parametros)


def coleccion_mongo():
    """
    Devuelve el cliente y la colección de MongoDB con la parte textual
    de las reviews. El cliente debe cerrarse al terminar.
    """
    client = pymongo.MongoClient(mongo_uri)
    collection = client[mongo_database][mongo_collection]
    return client, collection


def driver_neo4j():
    """
    Devuelve un driver de Neo4j. Se importa aquí para que el resto de scripts
    no necesiten tener instalado el paquete neo4j si no lo usan.
    """
    from neo4j import GraphDatabase

    return GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))


def formato_fecha(fecha_texto):
    """
    Convierte una fecha en texto al tipo date de Python.

    En los datasets de Amazon la fecha aparece con un formato como
    '07 9, 2012'. Si la fecha no existe o no cumple el formato esperado,
    se devuelve None.
    """
    if not fecha_texto:
        return None

    try:
        return datetime.strptime(fecha_texto, "%m %d, %Y").date()
    except ValueError:
        return None


def parsear_review(linea, categoria):
    """
    Convierte una línea JSON del dataset en las tuplas/documentos que se
    insertan en cada base de datos.

    Devuelve (usuario, producto, review_mysql, documento_mongo):
    - MySQL almacena la parte estructurada (usuario, producto, nota, votos, fechas).
    - MongoDB almacena la parte textual (texto completo y resumen), junto con
      los identificadores necesarios para relacionarla con MySQL.
    """
    import json

    review = json.loads(linea)

    reviewer_id = review.get("reviewerID")
    asin = review.get("asin")
    unix_review_time = review.get("unixReviewTime")

    # El campo helpful es una lista [votos útiles, votos totales]
    helpful = review.get("helpful") or [None, None]
    helpful_yes = helpful[0] if len(helpful) > 0 else None
    helpful_total = helpful[1] if len(helpful) > 1 else None

    usuario = (reviewer_id, review.get("reviewerName"))
    producto = (asin, categoria)
    review_mysql = (
        reviewer_id,
        asin,
        review.get("overall"),
        helpful_yes,
        helpful_total,
        unix_review_time,
        formato_fecha(review.get("reviewTime")),
    )
    documento_mongo = {
        "reviewerID": reviewer_id,
        "asin": asin,
        "categoria": categoria,
        "unix_review_time": unix_review_time,
        "reviewText": review.get("reviewText"),
        "summary": review.get("summary"),
    }
    return usuario, producto, review_mysql, documento_mongo
