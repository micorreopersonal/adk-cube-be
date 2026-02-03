import os
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv()
client = bigquery.Client(project=os.getenv("PROJECT_ID"))
table_id = f"{os.getenv('PROJECT_ID')}.{os.getenv('BQ_DATASET')}.{os.getenv('BQ_TABLE_TURNOVER')}"

print(f"Inspeccionando tabla: {table_id}")
table = client.get_table(table_id)
print("\nColumnas encontradas:")
for field in table.schema:
    print(f"- {field.name}: {field.field_type}")

query_sample = f"SELECT * FROM `{table_id}` LIMIT 1"
df = client.query(query_sample).to_dataframe()
print("\nEjemplo de datos (1 fila):")
print(df.to_dict(orient='records')[0])
