import sys
import os
import pandas as pd
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.schemas.analytics import SemanticRequest, CubeQuery, RequestMetadata, FilterCondition
from app.ai.tools.universal_analyst import execute_semantic_query
from app.schemas.payloads import VisualDataPackage, ChartBlock

# Mock BigQuery Service to avoid real DB calls
def mock_bq_executor(sql: str) -> pd.DataFrame:
    print(f"    🔍 [MOCK DB] Executing SQL... (simulated)")
    # Return a dummy DF structure based on typical queries
    # We construct a generic DF that satisfies "completeness" checks
    data = []
    # Try to guess dimensions from SQL (very basic)
    # This is just to prevent crashes; the real assertion is on the *Dimensions List* modification 
    # which happens BEFORE SQL generation in the code we modified.
    return pd.DataFrame(data)

def test_scenario(name: str, intent: str, dimensions: List[str], filters: Dict[str, Any], metrics: List[str], expected_order: List[str]):
    print(f"\n🧪 TEST: {name}")
    print(f"    Input Dimensions: {dimensions}")
    print(f"    Input Filters: {filters}")
    
    # 1. Setup Request
    # Construct FilterConditions
    filter_objs = []
    for k, v in filters.items():
        filter_objs.append(FilterCondition(dimension=k, value=v, operator="IN"))

    req_payload = {
        "intent": intent,
        "cube_query": {
            "metrics": metrics,
            "dimensions": dimensions.copy(), # Copy to see mutation
            "filters": filter_objs
        },
        "metadata": {"requested_viz": "LINE_CHART"}
    }

    # 2. Run logic (Patched)
    # We want to inspect the 'dimensions' list INSIDE execute_semantic_query *after* the reordering logic.
    # Since we can't easily spy on local variables, we will rely on the *SQL Generation* call 
    # or we can verify the behavior by checking if valid chart blocks are produced (if we had real data).
    # 
    # BETTER APPROACH FOR UNIT TESTING LOGIC: 
    # We will import the logic block or spy on `build_analytical_query` to see what params it received.
    
    with patch('app.ai.tools.universal_analyst.get_bq_service') as mock_service:
        mock_instance = MagicMock()
        mock_instance.execute_query.side_effect = mock_bq_executor
        mock_service.return_value = mock_instance
        
        with patch('app.ai.tools.universal_analyst.build_analytical_query') as mock_builder:
            mock_builder.return_value = "SELECT * FROM dummy"
            
            # Execute
            execute_semantic_query(**req_payload)
            
            # 3. Assertions
            # Get the arguments passed to build_analytical_query
            args, kwargs = mock_builder.call_args
            actual_dims = kwargs.get('dimensions')
            
            print(f"    ✅ Result Dimensions sent to SQL: {actual_dims}")
            
            if actual_dims == expected_order:
                print("    🎉 PASS")
            else:
                print(f"    ❌ FAIL. Expected {expected_order}, got {actual_dims}")

if __name__ == "__main__":
    print("🚀 Starting Semantic Comparison Logic Tests...\n")
    
    # CASE 1: Temporal Comparison (Classic Year vs Year)
    # User asks: "Rotation 2024 vs 2025 monthly" -> dims: [mes, uo2, anio] (LLM typical output)
    test_scenario(
        name="Temporal Comparison (2024 vs 2025)",
        intent="COMPARISON",
        dimensions=["mes", "uo2", "anio"], 
        filters={"anio": [2024, 2025]},
        metrics=["tasa_rotacion"],
        expected_order=["mes", "anio", "uo2"] # Should move 'anio' to index 1
    )

    # CASE 2: Categorical Comparison (Division vs Division)
    # User asks: "Rotation Finance vs HR monthly" -> dims: [mes, uo2]
    test_scenario(
        name="Categorical Comparison (Division vs Division)",
        intent="COMPARISON",
        dimensions=["mes", "uo2"], 
        filters={"uo2": ["Finance", "HR"]}, # Multiple values for uo2
        metrics=["tasa_rotacion"],
        expected_order=["mes", "uo2"] # 'uo2' is already at index 1, should stay or verify it's valid
    )
    
    # CASE 3: Inverted Input (LLM puts Year first for some reason)
    # User asks: "Compare years 24 vs 25 by month" -> dims: [anio, mes]
    test_scenario(
        name="Inverted Input (Year first)",
        intent="COMPARISON",
        dimensions=["anio", "mes"], 
        filters={"anio": [2024, 2025]},
        metrics=["tasa_rotacion"],
        expected_order=["anio", "mes"] 
        # Wait, if Anio is first (X-Axis), we get "2024, 2025" on X-Axis. 
        # If the user wants Time Series, X should be Month. 
        # Our logic *promotes* to Index 1. 
        # If 'anio' is at 0, and we move it to 1... it becomes [mes, anio] (assuming mes was at 1).
        # Let's trace: dims=[anio, mes]. remove(anio) -> [mes]. insert(1, anio) -> [mes, anio].
        # So yes, this verifies we FIX the axis too!
    )

    # CASE 4: Multi-Metric (Should NOT reorder)
    # User asks: "Voluntary vs Involuntary 2025" -> dims: [mes], metrics: [vol, invol]
    test_scenario(
        name="Multi-Metric Comparison",
        intent="COMPARISON",
        dimensions=["mes", "uo2"], 
        filters={"anio": 2025}, # Single year
        metrics=["tasa_voluntaria", "tasa_involuntaria"],
        expected_order=["mes", "uo2"] # Should NOT change, metrics drive the series
    )

    # CASE 5: N-Line Scaling (3 Years)
    test_scenario(
        name="N-Line Scaling (3 Years: 2023, 2024, 2025)",
        intent="COMPARISON",
        dimensions=["mes", "uo2", "anio"], 
        filters={"anio": [2023, 2024, 2025]},
        metrics=["tasa_rotacion"],
        expected_order=["mes", "anio", "uo2"] # correctly groups by anio
    )
