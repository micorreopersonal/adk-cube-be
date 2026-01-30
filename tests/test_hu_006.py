import sys
import os
import pytest
from pprint import pprint

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, project_root)

from app.ai.tools.bq_queries.leavers import get_leavers_distribution

def test_hu_006_distribution():
    print("\n[TEST] Testing HU-006: Distributive Analysis Tool")
    
    # Caso 1: Distribución por Área (UO3) - 2024
    print("\n--- Case 1: Breakdown by AREA (UO3) ---")
    result = get_leavers_distribution(
        periodo="2024",
        breakdown_by="AREA",
        segmento="TOTAL"
    )
    
    # Basic Validations
    assert result is not None
    assert "content" in result
    
    has_chart = False
    for block in result["content"]:
        if block.get("type") == "distribution_chart":
            has_chart = True
            print(f"✅ Chart Found: {block['subtype']} - {block['title']}")
            print(f"   Data Points: {len(block['data'])}")
            if len(block['data']) > 0:
                print(f"   Top 1: {block['data'][0]}")
        
        if block.get("type") == "debug_sql":
            print(f"   SQL:\n{block['payload']}")

    if not has_chart and "No se encontraron datos" not in str(result):
        pytest.fail("Chart block missing in response")
        
    print("✅ Case 1 Passed")

    # Caso 2: Distribución por Motivo (Pie Chart probable)
    print("\n--- Case 2: Breakdown by MOTIVO (Pie Candidate) ---")
    result_motivo = get_leavers_distribution(
        periodo="2024",
        breakdown_by="MOTIVO"
    )
    # Check execution only
    assert result_motivo is not None
    print("✅ Case 2 Passed")

if __name__ == "__main__":
    try:
        test_hu_006_distribution()
    except Exception as e:
        print(f"❌ FAIL: {e}")
        sys.exit(1)
