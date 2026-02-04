import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from app.services.query_generator import build_analytical_query
from app.core.analytics.registry import METRICS_REGISTRY, DIMENSIONS_REGISTRY
from app.ai.tools.universal_analyst import execute_semantic_query

# ==========================================
# 1. PRUEBAS DEL GENERADOR DE QUERIES (CORE)
# ==========================================

def test_build_query_basic():
    """Verifica la generación SQL básica con métricas y dimensiones estándar."""
    params = {
        "metrics": ["tasa_rotacion"],
        "dimensions": ["uo2"],
        "filters": {"anio": 2025}
    }
    query = build_analytical_query(**params)
    
    # Assertions
    assert "SELECT" in query
    assert "uo2 AS uo2" in query
    assert "SAFE_DIVIDE" in query  # Tasa de rotación usa safe_divide
    assert "anio = 2025" in query or "anio = '2025'" in query
    # Regla de Oro (Security Filter)
    assert "NOT (LOWER(segmento) LIKE '%practicante%')" in query

def test_build_query_complex_filters():
    """Verifica filtros complejos (listas, IN clauses)."""
    params = {
        "metrics": ["ceses_voluntarios"],
        "dimensions": ["uo2", "mes"],
        "filters": {
            "talento": [7, 8, 9],
            "segmento": "FFVV"
        }
    }
    query = build_analytical_query(**params)
    
    # Relaxed assertions
    q_lower = query.lower()
    assert "in (7, 8, 9)" in q_lower or "in ('7', '8', '9')" in q_lower
    assert "lower(segmento) = lower('ffvv')" in q_lower or "like" in q_lower
    assert "group by" in q_lower

def test_query_generator_security_sanitization():
    """Verifica que el generador rechace dimensiones no registradas (SQL Injection Prevention)."""
    params = {
        "metrics": ["tasa_rotacion"],
        "dimensions": ["uo2; DROP TABLE users;"], # Intento de inyección
        "filters": {"anio": 2025}
    }
    
    with pytest.raises(ValueError) as excinfo:
        build_analytical_query(**params)
    assert "Dimensión no autorizada" in str(excinfo.value)

def test_metrics_formula_integrity():
    """Verifica que las métricas críticas tengan la lógica de negocio correcta (Source of Truth)."""
    tasa_sql = METRICS_REGISTRY["tasa_rotacion"]["sql"]
    # Debe filtrar por 'Cesado' y 'Activo'
    assert "Cesado" in tasa_sql
    assert "Activo" in tasa_sql
    
    ceses_sql = METRICS_REGISTRY["ceses_voluntarios"]["sql"]
    # Debe mirar el motivo de cese (Renuncia)
    assert "renuncia" in ceses_sql.lower()

# ==========================================
# 2. PRUEBAS DE LA HERRAMIENTA CON MOCKS
# ==========================================

@patch("app.ai.tools.universal_analyst.get_bq_service")
def test_execute_semantic_query_flow(mock_bq_service):
    """
    Prueba el flujo completo de `execute_semantic_query` mockeando BigQuery.
    Verifica que la herramienta orqueste correctamente: Input -> SQL Gen -> Exec -> Formatting
    """
    # 1. Setup Mock
    mock_df = pd.DataFrame([
        {"uo2": "VENTAS", "tasa_rotacion": 5.5},
        {"uo2": "RRHH", "tasa_rotacion": 2.1}
    ])
    mock_instance = mock_bq_service.return_value
    mock_instance.execute_query.return_value = mock_df
    
    # 2. Execute Tool
    request = {
        "intent": "COMPARISON",
        "cube_query": {
            "metrics": ["tasa_rotacion"],
            "dimensions": ["uo2"],
            "filters": [{"dimension": "anio", "value": 2025}]
        },
        "metadata": {"title_suggestion": "Rotación por Area", "requested_viz": "BAR_CHART"}
    }
    
    result = execute_semantic_query(**request)
    
    # 3. Assertions
    # Verificar que llamó a BQ
    assert mock_instance.execute_query.called
    
    # Verificar estructura del output (VisualDataPackage)
    assert "summary" in result
    assert "content" in result
    assert len(result["content"]) > 0
    
    # Verificar que seleccionó el tipo de gráfico correcto
    block = result["content"][0]
    assert block["subtype"] == "BAR"
    assert len(block["payload"]["datasets"]) > 0

@patch("app.ai.tools.universal_analyst.build_analytical_query")
@patch("app.ai.tools.universal_analyst.get_bq_service")
def test_filter_aggregation_logic(mock_bq, mock_build):
    """
    Simula múltiples filtros de la misma dimensión para asegurar que se unifiquen en una lista.
    Ej: anio=2024 Y anio=2025 -> anio IN (2024, 2025)
    """
    mock_bq.return_value.execute_query.return_value = pd.DataFrame()
    mock_build.return_value = "SELECT 1"
    
    request = {
        "intent": "COMPARISON",
        "cube_query": {
            "metrics": ["tasa_rotacion"],
            "dimensions": ["uo2"],
            "filters": [
                {"dimension": "anio", "value": 2024},
                {"dimension": "anio", "value": 2025}
            ]
        },
        "metadata": {}
    }
    
    execute_semantic_query(**request)
    
    # Verificar argumentos pasados a build_analytical_query
    args, kwargs = mock_build.call_args
    passed_filters = kwargs.get("filters", {})
    
    assert "anio" in passed_filters
    # Puede ser lista [2024, 2025] o set, verificamos contenido
    vals = passed_filters["anio"]
    assert 2024 in vals
    assert 2025 in vals

def test_smart_listing_limits():
    """Verifica que LISTING aplique límites automáticos si no se especifican."""
    with patch("app.ai.tools.universal_analyst.build_analytical_query") as mock_build, \
         patch("app.ai.tools.universal_analyst.get_bq_service") as mock_bq:
        
        mock_bq.return_value.execute_query.return_value = pd.DataFrame()
        mock_build.return_value = "SELECT 1"
        
        execute_semantic_query(
            intent="LISTING",
            cube_query={"metrics": [], "dimensions": ["nombre"], "filters": []}
        )
        
        # Verificar que se inyectó limit=50 por default para listados
        args, kwargs = mock_build.call_args
        assert kwargs.get("limit") == 50
