import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.query_generator import build_analytical_query

def test_temporal_sql_generation():
    print("\n🧪 TEST: SQL Generation for Temporal Types")
    
    try:
        # Case 1: Simple Equality
        sql = build_analytical_query(
            metrics=["tasa_rotacion"],
            dimensions=["periodo"],
            filters={"periodo": "202404"}
        )
        
        print("\n--- SQL Output (Equality) ---")
        print(sql)
        
        if "LOWER(periodo)" in sql:
            print("❌ FAIL: LOWER() detected in SQL.")
        elif "periodo = '202404'" in sql:
            print("✅ PASS: Correct equality check generated.")
        else:
             print("⚠️ WARN: Check output manually.")

        # Case 2: IN Clause
        sql_in = build_analytical_query(
            metrics=["tasa_rotacion"],
            dimensions=["periodo"],
            filters={"periodo": ["202404", "202403"]}
        )
        print("\n--- SQL Output (IN Clause) ---")
        print(sql_in)
        
        if "LOWER(periodo)" in sql_in:
             print("❌ FAIL: LOWER() detected in IN Clause.")
        elif "periodo IN ('202404', '202403')" in sql_in or "periodo IN ('202403', '202404')" in sql_in:
             print("✅ PASS: Correct IN clause generated.")
             
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_temporal_sql_generation()
