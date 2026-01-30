from app.ai.tools.bq_queries.hr_metrics import get_headcount_stats
import json

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def validate_response(result, title):
    print(f"Validando: {title}")
    if result.get("response_type") == "visual_package":
        # Extraer KPI
        kpi_block = next((b for b in result["content"] if b.get("type") == "kpi_row"), None)
        if kpi_block:
            kpi = kpi_block["payload"][0]
            print(f"✅ KPI: {kpi['label']} = {kpi['value']}")
        
        # Extraer Tabla
        table_block = next((b for b in result["content"] if b.get("type") == "table"), None)
        if table_block:
            rows = len(table_block["payload"])
            print(f"✅ Tabla: {rows} registros de desglose encontrados")
            
        print("✅ Estructura VisualPackage: OK")
    else:
        print("❌ Error: La respuesta no es un visual_package")

if __name__ == "__main__":
    # Escenario 1: Headcount Corporativo 2025
    print_section("Escenario 1: Headcount Corporativo (2025)")
    res1 = get_headcount_stats(periodo="2025")
    validate_response(res1, "Corporativo Anual")

    # Escenario 2: Headcount por División (FINANZAS) Q4
    print_section("Escenario 2: Headcount División FINANZAS (2025-Q4)")
    res2 = get_headcount_stats(periodo="2025-Q4", uo_level="uo2", uo_value="FINANZAS")
    validate_response(res2, "División Q4")

    # Escenario 3: Snapshot Mensual
    print_section("Escenario 3: Snapshot Mensual (2025-12)")
    res3 = get_headcount_stats(periodo="2025-12")
    validate_response(res3, "Mensual Diciembre")
