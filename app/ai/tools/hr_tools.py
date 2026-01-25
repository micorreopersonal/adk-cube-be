from app.services.bigquery import get_bq_service
from app.ai.tools.bq_queries.attrition_queries import get_monthly_attrition_query, get_talent_attrition_query

bq_service = get_bq_service()

def get_attrition_metrics(year: int, month: int, uo_level: str = None, uo_value: str = None):
    """
    Tool para calcular métricas de rotación.
    """
    query = get_monthly_attrition_query(year, month, uo_level, uo_value)
    df = bq_service.execute_query(query)
    return df.to_dict(orient="records")[0] if not df.empty else {}

def get_critical_talent_leaks():
    """
    Tool para identificar fugas de talento crítico.
    """
    query = get_talent_attrition_query()
    df = bq_service.execute_query(query)
    return df.to_dict(orient="records")
