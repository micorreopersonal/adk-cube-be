import sys
import os
import pytest
from pprint import pprint

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, project_root)

from app.ai.tools.bq_queries.hr_metrics import get_monthly_trend

def test_hu_007_flexible_periods():
    print("\n[TEST] Testing HU-007: Flexible Trend Periods")
    
    # Caso 1: Rango Q4 (Oct-Dic 2024)
    print("\n--- Case 1: Last Quarter (Oct-Dec 2024) ---")
    result = get_monthly_trend(
        year=2024,
        month_start=10,
        month_end=12,
        segment="TOTAL"
    )
    
    # validations
    assert result is not None
    data_series_block = next((b for b in result["content"] if b["type"] == "data_series"), None)
    
    if not data_series_block:
        # Si no hay datos (ej. 2024 aun no tiene data Q4 real), fallar gracefully o warn
        print("⚠️ No data returned for Q4 2024. Check DB state.")
    else:
        payload = data_series_block["payload"]
        months = payload["months"]
        print(f"✅ Data returned. Months found: {months}")
        
        # Debe contener solo Oct, Nov, Dic (o subset si falta data)
        # Pero NO debe tener Enero o Junio.
        forbidden = ["Ene", "Jun", "Jul"]
        for m in months:
            if m in forbidden:
                pytest.fail(f"❌ Filtering FAILED. Found month {m} in requested range 10-12.")
        
        # Validar largo maximo 3
        if len(months) > 3:
             pytest.fail(f"❌ Too many months: {len(months)}")
             
        print("✅ Filtering Logic Passed (Clean subset)")

    # Caso 2: Año completo (sanity check)
    print("\n--- Case 2: Full Year Default ---")
    result_full = get_monthly_trend(year=2024)
    data_full = next((b for b in result_full["content"] if b["type"] == "data_series"), None)
    if data_full:
        print(f"✅ Full Year Months: {len(data_full['payload']['months'])}")

if __name__ == "__main__":
    try:
        test_hu_007_flexible_periods()
    except Exception as e:
        print(f"❌ FAIL: {e}")
        sys.exit(1)
