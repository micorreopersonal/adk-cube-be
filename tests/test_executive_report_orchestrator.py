import sys
import os
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.tools.executive_report_orchestrator import generate_executive_report

def mock_generate_critical_insight(periodo_display, headline_data, prev_data, granularity):
    """Mock LLM narrative generation."""
    return f"La rotación en {periodo_display} muestra una tendencia estable con ligeras variaciones respecto al período anterior. Los indicadores clave se mantienen dentro de rangos esperados para la organización."

async def mock_execute_semantic_query(intent, cube_query, metadata=None, **kwargs):
    """Mock execute_semantic_query responses based on section."""
    from app.schemas.payloads import (
        KPIBlock, KPIItem, ChartBlock, ChartPayload, 
        Dataset, TableBlock, TablePayload
    )
    
    # Determine section based on query parameters
    metrics = cube_query.get("metrics", [])
    dimensions = cube_query.get("dimensions", [])
    filters = cube_query.get("filters", [])
    
    # Section 1: Headline KPIs
    if intent == "SNAPSHOT" and not dimensions and set(metrics) == {"tasa_rotacion", "ceses_totales", "headcount_promedio"}:
        return {
            "content": [
                KPIBlock(
                    payload=[
                        KPIItem(label="Tasa de Rotación Global (%)", value=2.5),
                        KPIItem(label="Total Ceses", value=15),
                        KPIItem(label="Headcount Promedio", value=600)
                    ]
                )
            ]
        }
    
    # Section 2: Segmentation (FFVV vs ADMIN)
    if intent == "COMPARISON" and "grupo_segmento" in dimensions and "mes" in dimensions:
        return {
            "content": [
                ChartBlock(
                    payload=ChartPayload(
                        datasets=[
                            Dataset(label="Administrativo", data=[1.0, 1.2, 1.1]),
                            Dataset(label="Fuerza de Ventas", data=[4.5, 4.3, 4.6])
                        ],
                        labels=["ene", "feb", "mar"]
                    ),
                    metadata={"chart_type": "LINE"}
                )
            ]
        }
    
    # Section 3: Global Comparative
    if intent == "SNAPSHOT" and set(metrics) == {"tasa_rotacion", "tasa_rotacion_voluntaria", "tasa_rotacion_involuntaria"}:
        return {
            "content": [
                ChartBlock(
                    payload=ChartPayload(
                        datasets=[
                            Dataset(label="Rotación Total", data=[2.5]),
                            Dataset(label="Rotación Voluntaria", data=[1.8]),
                            Dataset(label="Rotación Involuntaria", data=[0.7])
                        ],
                        labels=["Organización"]
                    ),
                    metadata={"chart_type": "BAR"}
                )
            ]
        }
    
    # Section 4: Voluntary Focus
    if intent == "COMPARISON" and "uo2" in dimensions and "tasa_rotacion_voluntaria" in metrics:
        return {
            "content": [
                TableBlock(
                    payload=TablePayload(
                        rows=[
                            {"uo2": "DIVISION A", "tasa_rotacion_voluntaria": 3.5, "ceses_voluntarios": 10},
                            {"uo2": "DIVISION B", "tasa_rotacion_voluntaria": 2.8, "ceses_voluntarios": 8}
                        ]
                    )
                )
            ]
        }
    
    # Section 5: Talent Leakage
    if intent == "LISTING" and "nombre_completo" in dimensions:
        return {
            "content": [
                TableBlock(
                    payload=TablePayload(
                        rows=[
                            {"uo2": "DIVISION A", "nombre_completo": "Juan Pérez", "posicion": "Gerente", "talento": "HiPo", "motivo_cese": "Renuncia"},
                            {"uo2": "DIVISION B", "nombre_completo": "María García", "posicion": "Jefe", "talento": "HiPer", "motivo_cese": "Renuncia"}
                        ]
                    )
                )
            ]
        }
    
    # Section 6: Monthly Trend
    if intent == "TREND" and "mes" in dimensions and dimensions == ["mes"]:
        return {
            "content": [
                ChartBlock(
                    payload=ChartPayload(
                        datasets=[
                            Dataset(label="Tasa de Rotación Global (%)", data=[2.0, 2.2, 2.1, 2.5])
                        ],
                        labels=["ene", "feb", "mar", "abr"]
                    ),
                    metadata={"chart_type": "LINE"}
                )
            ]
        }
    
    # Default empty response
    return {"content": []}


@patch('app.ai.tools.executive_report_orchestrator.execute_semantic_query', side_effect=mock_execute_semantic_query)
@patch('app.ai.tools.executive_report_orchestrator.generate_critical_insight', side_effect=mock_generate_critical_insight)
def test_orchestrator_executive_report(mock_narrative, mock_query):
    print("\n🧪 TEST: Executive Report Orchestrator (New Pattern)")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(generate_executive_report("202504"))
    
    # Assertions on VisualDataPackage structure
    print(f"    📦 Response Type: {result.get('response_type')}")
    assert result.get("response_type") == "visual_package"
    
    print(f"    📊 Blocks Found: {len(result.get('content', []))}")
    assert len(result.get("content", [])) > 0
    
    # Verify query calls (should be 7 sections)
    print(f"    🔍 Query calls: {mock_query.call_count}")
    assert mock_query.call_count >= 6  # At least 6 sections (some may fail gracefully)
    
    # Verify narrative generation
    print(f"    📝 Narrative calls: {mock_narrative.call_count}")
    assert mock_narrative.call_count == 1
    
    # Verify section headers
    content = result.get("content", [])
    headers = [block for block in content if hasattr(block, 'variant') and block.variant == "h3"]
    print(f"    📋 Section headers: {len(headers)}")
    assert len(headers) >= 6  # Should have at least 6 section headers
    
    print("    ✅ All assertions passed!")
    print("\n✅ TEST PASSED: Orchestrator Executive Report")


if __name__ == "__main__":
    test_orchestrator_executive_report()
