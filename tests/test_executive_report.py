import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.tools.executive_reporter import get_executive_turnover_report

def mock_generate_critical_insight(periodo_display, headline_data, prev_data, granularity):
    """Mock LLM narrative generation."""
    return f"La rotación en {periodo_display} muestra una tendencia estable con ligeras variaciones respecto al período anterior. Los indicadores clave se mantienen dentro de rangos esperados para la organización."

def mock_semantic_query(intent, cube_query, metadata, **kwargs):
    """Mocks the Semantic Engine responses based on intent/context."""
    
    # Debug Mock Inputs
    with open("test_debug.log", "a", encoding="utf-8") as f:
        f.write(f"MOCK CALL: Intent={intent}, Dims={cube_query.get('dimensions')}\n")

    # 1. Headline (Snapshot)
    if intent == "SNAPSHOT":
        return {
            "content": [{
                "payload": {"items": [
                    {"label": "Tasa de Rotación Global (%)", "value": 2.5},
                    {"label": "Total Ceses", "value": 15},
                    {"label": "Headcount Promedio", "value": 600}
                ]}
            }]
        }
    
    
    # 2. Segmentation (COMPARISON by grupo_segmento - calculated dimension)
    if intent == "COMPARISON" and "grupo_segmento" in cube_query.get("dimensions", []):
        # grupo_segmento is a calculated dimension that aggregates segmento values
        return {
            "content": [{
                "payload": {"rows": [
                    {"grupo_segmento": "Administrativo", "tasa_rotacion": 1.0, "ceses_totales": 10},
                    {"grupo_segmento": "Fuerza de Ventas", "tasa_rotacion": 4.5, "ceses_totales": 20}
                ]}
            }]
        }
    
    # 3. Section 3: Global Comparative Rotation (SNAPSHOT with 3 metrics)
    metrics = cube_query.get("metrics", [])
    if intent == "SNAPSHOT" and "tasa_rotacion_involuntaria" in metrics and not cube_query.get("dimensions"):
        # Global level: No dimensions
        return {
            "content": [{
                "payload": {"items": [
                    {"label": "Tasa de Rotación Global (%)", "value": 4.66},
                    {"label": "Tasa de Rotación Voluntaria (%)", "value": 2.80},
                    {"label": "Tasa de Rotación Involuntaria (%)", "value": 1.86}
                ]}
            }]
        }
    
    # 3b. OLD Voluntary Focus (COMPARISON) - Fallback for table
    if intent == "COMPARISON" and "uo2" in cube_query.get("dimensions", []):
        return {
            "content": [{
                "payload": {"rows": [
                    {"uo2": "DIVISIÓN FINANZAS", "tasa_rotacion_voluntaria": 11.11, "ceses_voluntarios": 1},
                    {"uo2": "Logistica", "tasa_rotacion_voluntaria": 2.1, "ceses_voluntarios": 3},
                    {"uo2": "Finanzas", "tasa_rotacion_voluntaria": 0.5, "ceses_voluntarios": 1},
                    {"uo2": "RRHH", "tasa_rotacion_voluntaria": 0.0, "ceses_voluntarios": 0},
                    {"uo2": "IT", "tasa_rotacion_voluntaria": 3.2, "ceses_voluntarios": 4},
                    {"uo2": "Marketing", "tasa_rotacion_voluntaria": 4.1, "ceses_voluntarios": 5}
                ]}
            }]
        }

    # 4. Talent Leakage (Listing)
    if intent == "LISTING":
        return {
            "content": [{
                "payload": {"rows": [
                    {"nombre": "Juan Pérez", "posicion": "Gerente Ventas", "talento": "9 - Star", "motivo": "Mejor Oferta"},
                    {"nombre": "Maria Gomez", "posicion": "Analista Senior", "talento": "7 - Top Performer", "motivo": "Estudios"},
                    {"nombre": "Pedro Ruiz", "posicion": "Jefe", "talento": "8 - High Potential", "motivo": "Renuncia"}
                ]}
            }]
        }
    
    # 5. Trend / Prev Month (Mock for Comparative Logic)
    if intent == "TREND":
        # A) Segment Trend
        dims = cube_query.get("dimensions", [])
        metrics = cube_query.get("metrics", [])
        
        if "segmento" in dims:
            return {
                "content": [{
                    "payload": {
                        "labels": ["2024-01", "2024-02", "2024-03"],
                        "datasets": [
                            {"label": "Administrativo", "data": [1.0, 1.1, 1.2]},
                            {"label": "Fuerza de Ventas", "data": [4.0, 4.2, 4.5]}
                        ]
                    }
                }]
            }
        
        # B) Voluntary Trend
        elif "tasa_rotacion_voluntaria" in metrics:
             return {
                "content": [{
                    "payload": {
                        "labels": ["2024-01", "2024-02", "2024-03"],
                        "datasets": [
                            {"label": "Tasa Rotación Voluntaria (%)", "data": [2.0, 2.1, 2.2]},
                            {"label": "Ceses Voluntarios", "data": [10, 15, 12]}
                        ]
                    }
                }]
            }

        # C) Global Trend (Default)
        return {
            "content": [{
                "payload": {"datasets": [
                    {"label": "Tasa de Rotación Global (%)", "data": [2.0, 2.2, 2.1]}, # Avg ~ 2.1
                    {"label": "Total Ceses", "data": [10, 12, 11]}, # Avg ~ 11
                    {"label": "Headcount Promedio", "data": [590, 595, 600]}, # Avg ~ 595
                    # Add period for x-axis
                    
                ], "labels": ["2024-01", "2024-02", "2024-03"]}
            }]
        }
    
    # Prev Month (Snapshot with different values? Or same?)
    # If we return same as Snapshot (2.5), Variation is 0.
    # To test variation, we might want different values. 
    # But for "Availability" test, same is fine.
    
    return {"content": []}

@patch('app.ai.tools.executive_reporter.execute_semantic_query', side_effect=mock_semantic_query)
@patch('app.ai.tools.executive_reporter.generate_critical_insight', side_effect=mock_generate_critical_insight)
def test_executive_report_generation(mock_narrative, mock_query):
    print("\n🧪 TEST: Executive Report Orchestrator (Visual Blocks)")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(get_executive_turnover_report("202404"))
    
    # Assertions on VisualDataPackage structure
    print(f"    📦 Response Type: {result.get('response_type')}")
    assert result.get("response_type") == "visual_package"
    
    content = result.get("content", [])
    print(f"    Blocks Found: {len(content)}")
    
    # Verify 7-Point Structure Headers
    texts = [b['payload'] for b in content if b['type'] == 'text']
    assert any("1. Insight Crítico" in t for t in texts)
    assert any("4. Alerta de Talento Clave" in t for t in texts)
    assert any("7. Recomendaciones" in t for t in texts)
    assert any("3.1 Focos de Concentración" in t for t in texts)
    print("    ✅ 7-Point Headers Present")

    # 1. Headline (KPIBlock)
    kpi_block = next((b for b in content if b['type'] == 'KPI_ROW'), None)
    assert kpi_block is not None
    print("    ✅ KPI Block Present")
    metrics = {k['label']: k['value'] for k in kpi_block['payload']}
    print("    ✅ KPI Block Present")
    metrics = {k['label']: k['value'] for k in kpi_block['payload']}
    # KPI Formatting check: 2 decimals string
    assert metrics["Tasa de Rotación Global (%)"] == "2.50"
    
    # 2. Segmentation (ChartBlock - LINE vs LINE)
    # Was subtype="BAR", now "LINE"
    chart_block = next((b for b in content if b['type'] == 'CHART' and "ADMI" in b.get('metadata', {}).get('title', '')), None)
    assert chart_block is not None
    assert chart_block['subtype'] == "LINE"
    print("    ✅ Segmentation Chart Present (Standard LINE)")
    
    # Check Datasets (Mock returns 2 series)
    ds = chart_block['payload']['datasets']
    assert len(ds) == 2
    assert "Administrativo" in [d['label'] for d in ds]

    # 3. Global Comparative Rotation Chart (BAR - Total vs Voluntary vs Involuntary)
    comp_rot_chart = next((b for b in content if b['type'] == 'CHART' and "Comparativa" in b.get('metadata', {}).get('title', '') and "Global" in b.get('metadata', {}).get('title', '')), None)
    assert comp_rot_chart is not None
    assert comp_rot_chart['subtype'] == "BAR"
    # Should have 3 datasets (Total, Voluntary, Involuntary)
    assert len(comp_rot_chart['payload']['datasets']) == 3
    # Should have single label "Organización"
    assert comp_rot_chart['payload']['labels'] == ["Organización"]
    dataset_labels = [ds['label'] for ds in comp_rot_chart['payload']['datasets']]
    assert "Rotación Total" in dataset_labels
    assert "Rotación Voluntaria" in dataset_labels
    assert "Rotación Involuntaria" in dataset_labels
    print("    ✅ Global Comparative Rotation Chart Present (3 series)")
    
    # 3b. Optional Voluntary Focus Table (if kept)
    # Find table following header or just presence of TABLE in general (since we have multiple)
    # We can distinguish by headers in payload
    vol_table = None
    for b in content:
        if b['type'] == 'TABLE':
            h = b['payload'].get('headers', [])
            if "tasa_rotacion_voluntaria" in h or "ceses_voluntarios" in h:
                vol_table = b
                break
    
    assert vol_table is not None
    print("    ✅ Voluntary Focus Table Present")
    
    # 4. Talent Leakage (TableBlock)
    leak_table = None
    for b in content:
        if b['type'] == 'TABLE' and b != vol_table:
            h = b['payload'].get('headers', [])
            if "talento" in h and "motivo" in h:
                leak_table = b
                break
    
    if leak_table:
         print("    ✅ Talent Leakage Table Present")
    else:
         print("    ⚠️ Talent Leakage Table Missing (Check Mock Data)")

    # 5. Comparative Table (TableBlock) & Chart (ChartBlock)
    comp_chart = next((b for b in content if b['type'] == 'CHART' and "Comparativa" in b.get('metadata', {}).get('title', "")), None)
    assert comp_chart is not None
    # Check for 2 datasets (Real vs Promedio)
    assert len(comp_chart['payload']['datasets']) == 2
    print("    ✅ Comparative Chart Present")

    comp_table = None
    for b in content:
        if b['type'] == 'TABLE' and b != vol_table and b != leak_table:
            h = b['payload'].get('headers', [])
            if "Variación" in h and "Mes Actual" in h:
                comp_table = b
                break

    assert comp_table is not None
    print("    ✅ Comparative Table Present")
    cols = comp_table['payload']['headers']
    assert "Variación" in cols
    assert "Mes Actual" in cols

if __name__ == "__main__":
    try:
        test_executive_report_generation()
    except AssertionError as e:
        print(f"❌ ASSERTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
