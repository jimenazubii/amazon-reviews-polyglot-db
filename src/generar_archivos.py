# Lola Mancebo Olivares 
# Jimena Zubizarreta Gómez

"""
Exporta a CSV (carpeta exports/) los datos usados para reproducir tres gráficas
en Tableau: reviews por año, popularidad de artículos y frecuencia de palabras.

Uso:
    python src/generar_archivos.py
"""

from collections import Counter

import pandas as pd

from configuracion import ROOT_DIR
from db import coleccion_mongo, conexion_mysql

EXPORTS_DIR = ROOT_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

conn = conexion_mysql()

# 1. Reviews por año
df1 = pd.read_sql("""
SELECT YEAR(review_time) as anio, COUNT(*) as total
FROM reviews
WHERE review_time IS NOT NULL
GROUP BY YEAR(review_time)
ORDER BY YEAR(review_time)
""", conn)
df1.to_csv(EXPORTS_DIR / "reviews_por_anio.csv", index=False)


# 2. Popularidad 
df2 = pd.read_sql("""
SELECT asin, COUNT(*) as total
FROM reviews
GROUP BY asin
ORDER BY total DESC
""", conn)
df2["posicion"] = range(1, len(df2) + 1)
df2.to_csv(EXPORTS_DIR / "popularidad.csv", index=False)


# 3. Nube de palabras 
client, collection = coleccion_mongo()

palabras = []

for doc in collection.find({"categoria": "Toys_and_Games"}, {"summary": 1}):
    if doc.get("summary"):
        palabras += [p.lower() for p in doc["summary"].split() if len(p) > 3]

conteo = Counter(palabras)

df4 = pd.DataFrame(conteo.items(), columns=["palabra", "frecuencia"])
df4 = df4.sort_values(by="frecuencia", ascending=False)
df4 = df4.head(200)
df4.to_csv(EXPORTS_DIR / "nube_palabras.csv", index=False)

client.close()
conn.close()