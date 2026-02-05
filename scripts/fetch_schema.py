from app.services.bigquery import get_bq_service
from app.core.config.config import get_settings

def print_schema():
    try:
        settings = get_settings()
        bq = get_bq_service()
        table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"
        
        print(f"Fetching schema for: {table_id}")
        
        # Method 1: Get Table Resource
        table = bq.client.get_table(table_id)
        print("\n--- SCHEMA ---")
        for schema_field in table.schema:
            print(f"{schema_field.name} ({schema_field.field_type})")
            
    except Exception as e:
        print(f"Error fetching schema: {e}")

if __name__ == "__main__":
    print_schema()
