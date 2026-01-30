import sys
import os

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, project_root)

from app.ai.tools.bq_queries.leavers import get_leavers_distribution

def test_hu_008():
    print("[TEST] Testing HU-008: Talent Filter in Distributions")
    
    # December 2025 - HIPOS (Filter 8, 9)
    print("\n--- Case 1: Filter HIPOS ---")
    res_hipo = get_leavers_distribution(periodo="2025-12", breakdown_by="division", tipo_talento="HIPOS")
    print("Title:", res_hipo['content'][0]['title'])
    
    # Verify title reflects the filter
    if "Hipos" in res_hipo['content'][0]['title']:
         print("✅ Title correctly reflects 'Hipos'")
    else:
         print("❌ Title missing filter label")

    # December 2025 - HIPERS (Filter 7)
    print("\n--- Case 2: Filter HIPERS ---")
    res_hiper = get_leavers_distribution(periodo="2025-12", breakdown_by="division", tipo_talento="HIPERS")
    print("Title:", res_hiper['content'][0]['title'])
    if "Hipers" in res_hiper['content'][0]['title']:
         print("✅ Title correctly reflects 'Hipers'")
    else:
         print("❌ Title missing filter label")

    # Verify Robustness (kwargs)
    print("\n--- Case 3: Robustness (Unknown Param) ---")
    try:
        res_robust = get_leavers_distribution(periodo="2024", breakdown_by="area", unknown_param="ignored")
        print("✅ Robustness test: SUCCESS (No crash)")
    except TypeError as e:
        print(f"❌ Robustness test: FAILED (Caught TypeError: {e})")

if __name__ == "__main__":
    test_hu_008()
