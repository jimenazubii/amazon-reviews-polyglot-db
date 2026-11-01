# Lola Mancebo Olivares
# Jimena Zubizarreta Gómez

"""
Configuración del proyecto: nombres de las bases de datos, colecciones,
credenciales y rutas de los datasets.

Las credenciales NO se escriben en el código: se leen de variables de entorno,
que pueden definirse en un fichero `.env` en la raíz del repositorio
(ver `.env.example`). El fichero `.env` está en `.gitignore` y nunca se sube.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Raíz del repositorio (carpeta padre de src/)
ROOT_DIR = Path(__file__).resolve().parent.parent

# Carga las variables definidas en .env (si existe)
load_dotenv(ROOT_DIR / ".env")

# --- MySQL -------------------------------------------------------------------
mysql_host = os.getenv("MYSQL_HOST", "localhost")
mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
mysql_user = os.getenv("MYSQL_USER", "root")
mysql_pass = os.getenv("MYSQL_PASSWORD", "")
mysql_database = os.getenv("MYSQL_DATABASE", "amazon_reviews")

# --- MongoDB -----------------------------------------------------------------
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
mongo_database = os.getenv("MONGO_DATABASE", "amazon_reviews")
mongo_collection = os.getenv("MONGO_COLLECTION", "reviews_texto")

# --- Neo4j -------------------------------------------------------------------
neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.getenv("NEO4J_USER", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "")

# --- Datasets ----------------------------------------------------------------
# Carpeta con los ficheros JSON de reviews (por defecto, data/ en la raíz del repo)
datasets_path = Path(os.getenv("DATA_DIR", ROOT_DIR / "data"))

# Las cuatro categorías de la carga inicial (load_data.py)
datasets = [
    ("Toys_and_Games", datasets_path / "Toys_and_Games_5.json"),
    ("Video_Games", datasets_path / "Video_Games_5.json"),
    ("Digital_Music", datasets_path / "Digital_Music_5.json"),
    ("Musical_Instruments", datasets_path / "Musical_Instruments_5.json"),
]

# Dataset adicional para la inserción incremental (inserta_dataset.py)
nuevo_dataset = ("Grocery_and_Gourmet_Food", datasets_path / "Grocery_and_Gourmet_Food_5.json")

# Tamaño de los lotes de inserción
batch_size = int(os.getenv("BATCH_SIZE", "1000"))
