
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.ai.tools.bq_queries.hr_metrics import get_yearly_attrition, get_monthly_trend
from app.core.config import get_settings

print("🚀 Starting Debug of HR Metrics (Edge Cases)...")

try:
    print("\n--- Testing get_yearly_attrition (None UO) ---")
    result = get_yearly_attrition(year=2025, uo_value=None)
    print("✅ get_yearly_attrition (None) SUCCESS")
    
    print("\n--- Testing get_monthly_trend (None UO, None Segmento) ---")
    result_trend = get_monthly_trend(year=2025, uo_value=None, segmento=None)
    print("✅ get_monthly_trend (None) SUCCESS")

    print("\n--- Testing get_monthly_trend (FFVV, UO Present) ---")
    result_trend_2 = get_monthly_trend(year=2025, uo_value="Finanzas", segmento="FFVV")
    print("✅ get_monthly_trend (Full) SUCCESS")
    
except Exception as e:
    print(f"\n❌ CRITICAL ERROR DETECTED:")
    print(str(e))
    import traceback
    traceback.print_exc()
