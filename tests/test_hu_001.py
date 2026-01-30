import pytest
from unittest.mock import MagicMock, patch
from app.ai.tools.bq_queries.turnover_metrics import get_advanced_turnover_metrics

@patch("app.ai.tools.bq_queries.turnover_metrics.get_bq_service")
def test_get_advanced_turnover_metrics_logic(mock_get_service):
    """
    Verifica que la lógica de construcción de SQL en get_advanced_turnover_metrics
    cumpla con las reglas críticas de HU-001.
    """
    # Mock del cliente BQ
    mock_job = MagicMock()
    mock_job.result.return_value = []  # Retorno dummy
    mock_client = MagicMock()
    mock_client.query.return_value = mock_job
    
    mock_service_instance = MagicMock()
    mock_service_instance.client = mock_client
    mock_get_service.return_value = mock_service_instance
    
    # 1. Ejecución con parámetros básicos
    periods = ["2025-01-01", "2025-02-01"]
    filters = {"division": "TALENTO"}
    group_by = ["area"]
    
    get_advanced_turnover_metrics(periods=periods, filters=filters, group_by=group_by)
    
    # Capturar la query generada
    generated_query = mock_client.query.call_args[0][0]
    
    # --- ASERCIONES CRÍTICAS (HU-001) ---
    
    # 1. Exclusión de Practicantes (Regla #1)
    assert "segmento != 'PRACTICANTE'" in generated_query, "Falla Regla 1: No se excluyen practicantes."
    
    # 2. Filtrado por Periodos (Regla #2)
    assert "'2025-01-01'" in generated_query
    assert "'2025-02-01'" in generated_query
    
    # 3. Filtros Dinámicos (Validar Mapeo division -> uo2)
    assert "uo2 = 'TALENTO'" in generated_query, "Falla Mapeo: 'division' debió traducirse a 'uo2'."
    
    # 4. Agrupación (Group By) (Validar Mapeo area -> uo3)
    assert "COALESCE(uo3, 'N/A') as uo3" in generated_query, "No se manejan nulos o falla mapeo area->uo3."
    assert "GROUP BY 1" in generated_query
    
    # 5. Denominador Promedio (Lógica OLAP)
    assert "AVG(hc_mes) as hc_avg" in generated_query, "No se está promediando el Headcount mensual."

    print("\n✅ HU-001 Verification Passed: SQL Logic is correct.")
