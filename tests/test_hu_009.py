import sys
import os

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, project_root)

from app.ai.tools.bq_queries.turnover import get_turnover_deep_dive

def test_hu_009():
    print("[TEST] Testing HU-009: Organizational Drill-down & Hotspots")
    
    # Analyze Division SALUD (which we saw had ~944 records)
    print("\n--- Deep Dive: Division SALUD (UO2 -> UO3) ---")
    res = get_turnover_deep_dive(parent_level="UO2", parent_value="DIVISION SALUD", periodo="2025")
    
    # Check if we have a chart (comparative)
    has_chart = any(c['type'] == 'plot' for c in res['content'])
    has_kpis = any(c['type'] == 'kpi_row' for c in res['content'])
    has_insight = any(c['type'] == 'text' and c.get('variant') == 'insight' for c in res['content'])
    
    print(f"Chart Rendered: {'✅' if has_chart else '❌'}")
    print(f"KPIs Rendered: {'✅' if has_kpis else '❌'}")
    print(f"Hotspot Insight: {'✅' if has_insight else '❌'}")
    
    # Print the insight text
    insight_text = next(c['payload'] for c in res['content'] if c['type'] == 'text' and c.get('variant') == 'insight')
    print(f"\nInsight: {insight_text}")

    # Check for Monthly Period
    print("\n--- Deep Dive: Division SALUD (Monthly 2025-01) ---")
    res_monthly = get_turnover_deep_dive(parent_level="UO2", parent_value="DIVISION SALUD", periodo="2025-01")
    has_kpis_m = any(c['type'] == 'kpi_row' for c in res_monthly['content'])
    print(f"Monthly KPIs Rendered: {'✅' if has_kpis_m else '❌'}")

    # Check for UO4 (Gerencia)
    print("\n--- Deep Dive: Area to Gerencia (UO3 -> UO4) ---")
    res_gerencia = get_turnover_deep_dive(parent_level="UO3", parent_value="DESARROLLO TI", periodo="2025")
    
    has_chart_g = any(c['type'] == 'plot' for c in res_gerencia['content'])
    print(f"Drill-down to UO4 Rendered: {'✅' if has_chart_g else '❌'}")

if __name__ == "__main__":
    test_hu_009()
