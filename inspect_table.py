import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client(project=os.getenv("PROJECT_ID"))
table_id = f"{os.getenv('PROJECT_ID')}.{os.getenv('BQ_DATASET')}.{os.getenv('BQ_TABLE_TURNOVER')}"

print(f"Inspeccionando tabla: {table_id}")
table = client.get_table(table_id)
print("\n--- SCHEMA ---")
for field in table.schema:
    print(f"{field.name} ({field.field_type})")

print("\n--- EJEMPLO DE FILA ---")
query = f"SELECT * FROM `{table_id}` LIMIT 1"
rows = client.query(query).to_dataframe()
for col in rows.columns:
    print(f"{col}: {rows[col].values[0]}")
