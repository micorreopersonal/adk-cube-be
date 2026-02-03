import os
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()

client = bigquery.Client(project=os.getenv("PROJECT_ID"))

table_id = f"{os.getenv('PROJECT_ID')}.{os.getenv('BQ_DATASET')}.{os.getenv('BQ_TABLE_TURNOVER')}"

query = f"""
SELECT DISTINCT segmento, COUNT(*) as count
FROM `{table_id}`
GROUP BY 1
ORDER BY 2 DESC
"""

print(f"Ejecutando query de diagnóstico en {table_id}...")
df = client.query(query).to_dataframe()
print("\nValores encontrados en 'segmento':")
print(df)

query_total = f"""
SELECT COUNT(*) as total_rows
FROM `{table_id}`
WHERE segmento = 'TOTAL'
"""
df_total = client.query(query_total).to_dataframe()
print(f"\nNúmero de filas con segmento = 'TOTAL': {df_total.iloc[0,0]}")
