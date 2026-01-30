"""
Script de Validación Manual - HU-009 Drilldown Organizacional
Prueba diferentes escenarios de navegación jerárquica y detección de hotspots.
"""
import json
from app.ai.tools.bq_queries.turnover import get_turnover_deep_dive

def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def validate_response(result, scenario_name):
    """Valida la estructura de la respuesta"""
    print(f"📊 Escenario: {scenario_name}")
    print("-" * 80)
    
    assert result["response_type"] == "visual_package", "❌ Tipo de respuesta incorrecto"
    print("✅ Tipo de respuesta: visual_package")
    
    # Contar bloques
    insights = [b for b in result["content"] if b.get("variant") == "insight"]
    kpis = [b for b in result["content"] if b.get("type") == "kpi_row"]
    charts = [b for b in result["content"] if b.get("type") == "plot"]
    
    print(f"✅ Bloques de insight: {len(insights)}")
    print(f"✅ Bloques de KPIs: {len(kpis)}")
    print(f"✅ Gráficos: {len(charts)}")
    
    # Mostrar insight principal
    if insights:
        insight_text = insights[0]["payload"]
        print(f"\n💡 Insight Principal:")
        print(f"   {insight_text[:200]}...")
    
    # Mostrar KPIs
    if kpis:
        print(f"\n📈 KPIs:")
        for kpi in kpis[0]["payload"]:
            print(f"   • {kpi['label']}: {kpi['value']}")
    
    # Mostrar info del gráfico
    if charts:
        chart = charts[0]
        print(f"\n📊 Gráfico: {chart.get('title', 'Sin título')}")
        print(f"   Tipo: {chart.get('subtype', 'N/A')}")
        print(f"   Datos: {len(chart['data']['x'])} categorías")
    
    print("\n" + "="*80 + "\n")

def main():
    print_section("VALIDACIÓN MANUAL HU-009: Drilldown Organizacional")
    
    # Escenario 1: Drilldown por defecto (TOTAL → UO3)
    print_section("Escenario 1: Análisis General (UO2=TOTAL → UO3)")
    result1 = get_turnover_deep_dive(
        parent_level="UO2",
        parent_value="TOTAL",
        periodo="2025"
    )
    validate_response(result1, "Drilldown General UO2→UO3")
    
    # Escenario 2: Drilldown de División específica
    print_section("Escenario 2: División Específica (UO2=FINANZAS → UO3)")
    try:
        result2 = get_turnover_deep_dive(
            parent_level="UO2",
            parent_value="FINANZAS",
            periodo="2025"
        )
        validate_response(result2, "Drilldown División Finanzas")
    except Exception as e:
        print(f"⚠️  División FINANZAS no encontrada o sin datos: {e}")
    
    # Escenario 3: Rotación Voluntaria con Hotspots
    print_section("Escenario 3: Rotación Voluntaria (UO2=TOTAL)")
    result3 = get_turnover_deep_dive(
        parent_level="UO2",
        parent_value="TOTAL",
        tipo_rotacion="VOLUNTARIA",
        periodo="2025"
    )
    validate_response(result3, "Rotación Voluntaria con Hotspots")
    
    # Escenario 4: Drilldown UO3 → UO4
    print_section("Escenario 4: Drilldown Nivel 3 (UO3 → UO4)")
    try:
        result4 = get_turnover_deep_dive(
            parent_level="UO3",
            parent_value="CONTABILIDAD",
            periodo="2025"
        )
        validate_response(result4, "Drilldown UO3→UO4")
    except Exception as e:
        print(f"⚠️  Área CONTABILIDAD no encontrada o sin datos: {e}")
    
    # Escenario 5: Periodo mensual
    print_section("Escenario 5: Análisis Mensual (2025-01)")
    result5 = get_turnover_deep_dive(
        parent_level="UO2",
        parent_value="TOTAL",
        periodo="2025-01"
    )
    validate_response(result5, "Análisis Mensual Enero 2025")

    # Escenario 6: Soporte de Trimestres (NEW)
    print_section("Escenario 6: Soporte de Trimestres (2025-Q4)")
    result6 = get_turnover_deep_dive(
        parent_level="UO2",
        parent_value="TOTAL",
        periodo="2025-Q4"
    )
    validate_response(result6, "Análisis Trimestral Q4 2025")
    
    print_section("✅ VALIDACIÓN COMPLETADA")
    print("Todos los escenarios fueron ejecutados exitosamente.")
    print("Revisa los resultados arriba para verificar la calidad de los insights y visualizaciones.")

if __name__ == "__main__":
    main()
