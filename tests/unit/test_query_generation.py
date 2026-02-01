import pytest
from app.ai.tools.bq_queries.hr_metrics import get_monthly_attrition, get_talent_alerts
import json

import pandas as pd

# Mock del servicio de BigQuery para que no intente conectar a GCP
@pytest.fixture
def mock_bq_service(mocker):
    mock = mocker.patch("app.ai.tools.bq_queries.hr_metrics.bq_service")
    # Configurar el mock para devolver un DataFrame vacío (comportamiento real)
    mock.execute_query.return_value = pd.DataFrame() 
    return mock

def test_monthly_attrition_query_structure(mock_bq_service):
    """
    Validar que la query SQL generada contiene las cláusulas clave para Enero 2025.
    No ejecutamos la query real, solo inspeccionamos la llamada al mock.
    """
    # Ejecutar la función con el nuevo nombre de parámetro estandarizado
    get_monthly_attrition(month=1, year=2025, segmento="FFVV")
    
    # Obtener el argumento con el que se llamó a execute_query
    args, _ = mock_bq_service.execute_query.call_args
    query_sql = args[0]
    
    # Validaciones de estructura SQL
    assert "WITH" in query_sql
    assert "HcInicial AS" in query_sql
    assert "Cesados AS" in query_sql
    assert "COALESCE(h.hc, 0) as hc_inicial" in query_sql
    assert "segmento = 'EMPLEADO FFVV'" in query_sql
    assert "EXTRACT(YEAR FROM fecha_cese) = 2025" in query_sql

def test_talent_alerts_query_structure(mock_bq_service):
    """Validar query de alertas de talento."""
    get_talent_alerts(month=1, year=2025)
    
    args, _ = mock_bq_service.execute_query.call_args
    query_sql = args[0]
    
    assert "mapeo_talento_ultimo_anio IN (7, 8, 9)" in query_sql
    assert "EXTRACT(MONTH FROM fecha_cese) = 1" in query_sql
