from app.ai.tools.bq_queries.turnover import get_turnover_deep_dive

def test_turnover_deep_dive():
    """
    HU-009: Validación de navegación jerárquica y detección de hotspots.
    """
    print("Testing get_turnover_deep_dive...")
    
    # Test 1: Parámetros por defecto (UO2="TOTAL")
    result = get_turnover_deep_dive()
    
    # Validar que retorna dict directamente (no JSON string)
    assert isinstance(result, dict), "La función debe retornar un diccionario"
    assert result["response_type"] == "visual_package"
    assert len(result["content"]) >= 3, "Debe incluir al menos insight, KPIs y gráfico"
    print("✅ Test 1: Parámetros por defecto - PASSED")
    
    # Test 2: Drilldown específico (UO2 → UO3)
    result_division = get_turnover_deep_dive(
        parent_level="UO2",
        parent_value="TOTAL",
        periodo="2025"
    )
    
    assert result_division["response_type"] == "visual_package"
    
    # Validar que contiene insight con información de benchmark
    insight_block = next((b for b in result_division["content"] if b.get("variant") == "insight"), None)
    assert insight_block is not None, "Debe incluir un bloque de insight"
    assert "tasa promedio" in insight_block["payload"].lower() or "benchmark" in insight_block["payload"].lower()
    print("✅ Test 2: Drilldown UO2→UO3 - PASSED")
    
    # Test 3: Validar estructura de KPIs (buscar por 'type', no 'variant')
    kpi_block = next((b for b in result_division["content"] if b.get("type") == "kpi_row"), None)
    assert kpi_block is not None, "Debe incluir un bloque de KPIs"
    assert len(kpi_block["payload"]) >= 3, "Debe incluir al menos 3 KPIs (Tasa, Áreas Críticas, Impacto)"
    print("✅ Test 3: Estructura de KPIs - PASSED")
    
    # Test 4: Validar gráfico comparativo (buscar por 'type' = 'plot')
    chart_block = next((b for b in result_division["content"] if b.get("type") == "plot"), None)
    assert chart_block is not None, "Debe incluir un gráfico comparativo"
    assert "data" in chart_block, "El gráfico debe contener datos"
    assert "x" in chart_block["data"] and "y" in chart_block["data"], "El gráfico debe tener ejes x e y"
    print("✅ Test 4: Gráfico comparativo - PASSED")

    # Test 5: Nuevo Soporte de Trimestres (Q4 2025)
    print("Testing Quarterly support (2025-Q4)...")
    result_q = get_turnover_deep_dive(
        parent_level="UO2",
        parent_value="TOTAL",
        periodo="2025-Q4"
    )
    assert result_q["response_type"] == "visual_package"
    insight_q = next((b for b in result_q["content"] if b.get("variant") == "insight"), None)
    assert "Q4 2025" in insight_q["payload"], "El insight debe mencionar el trimestre Q4 2025"
    
    # Test 6: Datos Nominales (HC y Ceses)
    print("Testing Nominal Data (HC & Ceses)...")
    table_block = next((b for b in result_q["content"] if b.get("type") == "table"), None)
    assert table_block is not None, "Debe incluir un bloque de tabla"
    assert "Headcount (Base)" in table_block["payload"][0], "La tabla debe incluir Headcount"
    
    chart_block = next((b for b in result_q["content"] if b.get("type") == "plot"), None)
    assert "hc" in chart_block["data"], "El gráfico debe incluir datos de HC"
    assert "ceses" in chart_block["data"], "El gráfico debe incluir datos de ceses"
    
    print("✅ Test 6: Datos Nominales e Interfaz Agente - PASSED")
    
    print("\n🎉 Todos los tests de HU-009 (incluyendo Trimestres y HC) pasaron exitosamente!")

if __name__ == "__main__":
    test_turnover_deep_dive()

