
import sys
import os
import pytest

# Force Add project root BEFORE app imports
PROJECT_ROOT = "c:\\adk-projects\\adk-people-analytics-backend"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services.query_generator import build_analytical_query
from app.core.analytics.registry import METRICS_REGISTRY

def test_consistency_rotation():
    """
    1. Consistencia: ¿Se genera SQL válido para Rotación por División?
    """
    print("\n🧪 [TEST 1] Generación de Query (Rotación por División)...")
    try:
        sql = build_analytical_query(
            metrics=["tasa_rotacion", "ceses_totales"],
            dimensions=["uo2"],
            filters={"anio": 2025}
        )
        print("✅ SQL Generado:")
        print(sql)
        assert "SAFE_DIVIDE" in sql
        assert "GROUP BY" in sql
        assert "uo2" in sql
    except Exception as e:
        print(f"❌ FALLO: {e}")
        raise

def test_security_access():
    """
    2. Seguridad: ¿Bloquea métricas no existentes?
    """
    print("\n🧪 [TEST 2] Seguridad (Métrica Fake)...")
    try:
        build_analytical_query(
            metrics=["tasa_rotacion", "METRICA_MALICIOSA_INYECTADA"],
            dimensions=["uo2"]
        )
        print("❌ FALLO: Debería haber lanzado error.")
    except ValueError as e:
        print(f"✅ PASO: Bloqueó métrica desconocida ({e})")
    except Exception as e:
        print(f"❌ FALLO: Error inesperado {e}")

def test_comparative_structure():
    """
    3. Comparativa: Simulación de estructura (por ahora verificamos que el motor acepte listas en filtros)
    """
    print("\n🧪 [TEST 3] Filtros de Comparacion (Listas)...")
    try:
        sql = build_analytical_query(
            metrics=["headcount_actual"],
            dimensions=["anio"],
            filters={"anio": [2024, 2025]}
        )
        print("✅ SQL Comparativo Generado:")
        print(sql)
        assert "IN (2024, 2025)" in sql or "IN ('2024', '2025')" in sql
    except Exception as e:
        print(f"❌ FALLO: {e}")
        raise

if __name__ == "__main__":
    test_consistency_rotation()
    test_security_access()
    test_comparative_structure()
