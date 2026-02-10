import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.tools.executive_report_orchestrator import build_query_sequence
from app.ai.tools.universal_analyst import execute_semantic_query

# Copied verbatim from executive_report_stream.py to test EXACT logic
def get_kpi_value_repro(content, label_key: str) -> float:
    """Extract KPI value from query results (Replica of internal function)."""
    if content and len(content) > 0:
        first_block = content[0]
        
        payload = None
        if isinstance(first_block, dict):
            payload = first_block.get('payload', {})
        elif hasattr(first_block, 'payload'):
            payload = first_block.payload
        
        print(f"DEBUG: Payload Type: {type(payload)}")
        print(f"DEBUG: Payload Raw: {str(payload)[:200]}...")

        # Check for items
        items = None
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict) and 'items' in payload:
            items = payload['items']
        elif hasattr(payload, 'items') and callable(payload.items):
             # This might be the bug? data.items() returns (key, val) tuples for a dict!
             # If payload is a Pydantic model it might be different.
            items = payload.items() 
        elif hasattr(payload, 'items'):
            items = payload.items 
        
        if items:
            print(f"DEBUG: Items found. Count: {len(list(items))}")
            for item in items:
                # Handle both object and dict items
                if isinstance(item, dict):
                    i_label = item.get('label', '')
                    i_val = item.get('value', 0)
                else:
                    i_label = getattr(item, 'label', '')
                    i_val = getattr(item, 'value', 0)
                    
                print(f"   -> Item: '{i_label}' = {i_val}")
                
                if label_key.lower() in str(i_label).lower():
                    print(f"   ✅ MATCH! Returning {i_val}")
                    return i_val
    return 0

async def main():
    print("🚀 Starting KPI Extraction Repro...")
    
    # 1. Build Query
    all_queries = build_query_sequence("2025")
    # Find headline_current
    query_config = next(q for q in all_queries if q["section"] == "headline_current")
    
    print(f"📋 Executing Intent: {query_config['intent']}")
    
    # 2. Execute Query
    result = execute_semantic_query(
        intent=query_config["intent"],
        cube_query=query_config["cube_query"],
        metadata=query_config.get("metadata", {})
    )
    
    content = result.get("content", [])
    
    # 3. Test Extraction
    print("\n--- Testing Extraction ---")
    val_tasa = get_kpi_value_repro(content, "Tasa")
    val_ceses = get_kpi_value_repro(content, "Ceses")
    
    print(f"\n📢 RESULTS:")
    print(f"Extracted Tasa: {val_tasa}")
    print(f"Extracted Ceses: {val_ceses}")
    
    if val_tasa == 0:
        print("\n❌ FAILURE: Extracted 0 but expected ~25.9")
    else:
        print("\n✅ SUCCESS: Value extracted correctly")

if __name__ == "__main__":
    asyncio.run(main())
