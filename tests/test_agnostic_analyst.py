import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.schemas.analytics import SemanticRequest
from app.ai.tools.universal_analyst import execute_semantic_query, _ensure_dataframe_completeness
from app.core.analytics.registry import DEFAULT_FILTERS, DIMENSIONS_REGISTRY

# --- SCENARIO 1: AGNOSTIC MAPPING & SORTING ---
def test_agnostic_mapping_sorting():
    print("\n🧪 TEST: Agnostic Mapping & Sorting (Month)")
    
    # Mock DF with raw data (unordered months: 2, 1)
    df_raw = pd.DataFrame([
        {"mes": 2, "count": 10},
        {"mes": 1, "count": 5}
    ])
    
    # Mock Dependencies
    with patch('app.ai.tools.universal_analyst.get_bq_service') as mock_service:
        mock_instance = MagicMock()
        mock_instance.execute_query.return_value = df_raw
        mock_service.return_value = mock_instance
        
        with patch('app.ai.tools.universal_analyst.build_analytical_query') as mock_builder:
            mock_builder.return_value = "SELECT * FROM dummy"
            
            # Execute
            req = {
                "intent": "TREND",
                "cube_query": {
                    "metrics": ["count"],
                    "dimensions": ["mes"],
                    "filters": []
                },
                "metadata": {"requested_viz": "BAR_CHART"}
            }
            result_json = execute_semantic_query(**req)
            
            # Assertions
            # 1. Check Sorting: Should be sorted by Month 1 ("ene") then 2 ("feb")
            content = result_json["content"][0]["payload"]
            labels = content["labels"]
            data = content["datasets"][0]["data"]
            
            print(f"    Labels: {labels}")
            print(f"    Data: {data}")
            
            if labels == ["ene", "feb"] and data == [5, 10]:
                 print("    ✅ Data Correctly Sorted and Mapped (Registry logic working)")
            else:
                 print("    ❌ FAIL: Mapping or Sorting failed.")

# --- SCENARIO 2: DEFAULT FILTERS INJECTION ---
def test_default_filter_injection():
    print("\n🧪 TEST: Default Filter Injection (Config-Driven)")
    
    # Mock Dependencies
    with patch('app.ai.tools.universal_analyst.get_bq_service') as mock_service:
        mock_instance = MagicMock()
        # Empty DF just to pass execution
        mock_instance.execute_query.return_value = pd.DataFrame()
        mock_service.return_value = mock_instance
        
        with patch('app.ai.tools.universal_analyst.build_analytical_query') as mock_builder:
            mock_builder.return_value = "SELECT * FROM dummy"
            
            # Execute "LISTING" without status filter
            req = {
                "intent": "LISTING",
                "cube_query": {
                    "metrics": [],
                    "dimensions": ["nombre", "dni"],
                    "filters": [] # Intentionally empty
                },
                "metadata": {"requested_viz": "TABLE"}
            }
            execute_semantic_query(**req)
            
            # Validate what was passed to SQL Builder
            args, kwargs = mock_builder.call_args
            filters_sent = kwargs.get('filters', {})
            
            print(f"    Filters Sent to SQL: {filters_sent}")
            
            # Should contain 'estado': 'Cesado' from DEFAULT_FILTERS
            default_rule = DEFAULT_FILTERS["LISTING"][0]
            expected_key = default_rule["dimension"]
            expected_val = default_rule["value"]
            
            if filters_sent.get(expected_key) == expected_val:
                print("    ✅ Default Filter Successfully Injected from Config")
            else:
                print("    ❌ FAIL: Default filter not injected.")

if __name__ == "__main__":
    print("🚀 Starting Agnostic Analyst Tests...\n")
    test_agnostic_mapping_sorting()
    test_default_filter_injection()
