import pytest
from app.services.query_generator import build_analytical_query
from app.core.analytics.registry import METRICS_REGISTRY
import pandas as pd

# 1. Prueba de Generación Básica
def test_build_query_basic():
    params = {
        "metrics": ["tasa_rotacion"],
        "dimensions": ["uo2"],
        "filters": {"anio": 2025}
    }
    # Unpacking params to match function signature
    query = build_analytical_query(**params)
    
    # Verificaciones de Integridad
    assert "SELECT" in query
    assert "uo2 AS uo2" in query or "uo2_division" in query # Adjusted to what registry likely produces or aliases
    assert "SAFE_DIVIDE" in query  # Verifica que use la fórmula del registry
    assert "anio = 2025" in query or "anio = '2025'" in query
    assert "NOT (LOWER(segmento) LIKE '%practicante%')" in query # Regla de Oro

# 2. Prueba de Filtros Complejos (Inyección de Listas)
def test_build_query_complex_filters():
    params = {
        "metrics": ["ceses_voluntarios"],
        "dimensions": ["uo2", "mes"],
        "filters": {
            "talento": [7, 8, 9],
            "segmento": "FFVV"
        }
    }
    query = build_analytical_query(**params)
    
    # Checking for list inclusion syntax
    assert "IN (7, 8, 9)" in query or "IN ('7', '8', '9')" in query
    assert "LOWER(segmento) LIKE LOWER('%FFVV%')" in query
    assert "GROUP BY" in query

# 3. Prueba de Seguridad (Anti-Inyección SQL)
def test_query_generator_security_sanitization():
    params = {
        "metrics": ["tasa_rotacion"],
        "dimensions": ["uo2; DROP TABLE users;"], # Intento de inyección
        "filters": {"anio": 2025}
    }
    
    # El generador debe validar contra el DIMENSIONS_REGISTRY
    # Raises ValueError in current implementation, not KeyError
    with pytest.raises(ValueError):
        build_analytical_query(**params)

# 4. Prueba de Consistencia de Fórmulas
def test_metrics_formula_consistency():
    # Validamos que las métricas críticas sigan el estándar del negocio
    # Note: Registry uses 'Cesado' (Title Case)
    tasa_sql = METRICS_REGISTRY["tasa_rotacion"]["sql"]
    assert "estado = 'Cesado'" in tasa_sql
    
    ceses_sql = METRICS_REGISTRY["ceses_voluntarios"]["sql"]
    assert "motivo_cese" in ceses_sql.lower() or "motivo_cese" in ceses_sql
# 5. Prueba de Consolidación de Filtros (Multi-Filtro por Dimensión)
def test_execute_query_filter_aggregation():
    from app.ai.tools.universal_analyst import execute_semantic_query
    
    # Simular un request que tiene filtros repetidos (lo que el LLM podría generar)
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
        "metadata": {"title_suggestion": "Test Filter Aggregation"}
    }
    
    # No ejecutamos realmente en BQ aquí para no depender del entorno, 
    # pero podemos capturar el SQL generado si parcheamos build_analytical_query.
    from unittest.mock import patch
    with patch("app.ai.tools.universal_analyst.build_analytical_query") as mock_build:
        mock_build.return_value = "SELECT 1"
        with patch("app.ai.tools.universal_analyst.get_bq_service") as mock_bq:
            mock_bq.return_value.execute_query.return_value = pd.DataFrame()
            execute_semantic_query(**request)
            
            # Verificar los filtros que llegaron al generador
            args, kwargs = mock_build.call_args
            generated_filters = kwargs.get("filters")
            
            assert "anio" in generated_filters
            assert set(generated_filters["anio"]) == {2024, 2025}
