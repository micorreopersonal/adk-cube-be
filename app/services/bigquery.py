from google.cloud import bigquery
from app.core.config import get_settings

class BigQueryService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BigQueryService, cls).__new__(cls)
            cls._instance._client = None
        return cls._instance

    @property
    def client(self) -> bigquery.Client:
        if self._client is None:
            settings = get_settings()
            self._client = bigquery.Client(project=settings.PROJECT_ID)
        return self._client

    def execute_query(self, query: str):
        """Ejecuta una consulta SQL en BigQuery."""
        query_job = self.client.query(query)
        return query_job.to_dataframe()

def get_bq_service():
    return BigQueryService()
