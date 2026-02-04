from google.cloud import bigquery
from app.core.config.config import get_settings

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
        """Ejecuta una consulta SQL en BigQuery con Cost Guardrails (1 GB Limit)."""
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=10**9,  # 1 GB Limit (~$0.005 USD) per query
            use_query_cache=True
        )
        query_job = self.client.query(query, job_config=job_config)
        return query_job.to_dataframe()

def get_bq_service():
    return BigQueryService()
