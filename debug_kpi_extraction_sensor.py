
import sys
import os
import asyncio
from pprint import pprint

# Add root to path
sys.path.append(os.getcwd())

from app.ai.tools.executive_report_orchestrator import build_query_sequence
from app.ai.tools.universal_analyst import execute_semantic_query

# MOCK of the function in executive_report_stream.py
def get_kpi_value_debug(results, section_key, label_key):
    print(f"\n🔎 [SENSOR] Scanning for '{label_key}' in section '{section_key}'...")
    
    if section_key not in results:
        print(f"   ❌ Section '{section_key}' NOT FOUND in results.")
        return 0

    content = results[section_key].get("content", [])
    print(f"   📦 Content blocks: {len(content)}")
    
    if not content:
        print("   ❌ No content blocks.")
        return 0

    first_block = content[0]
    print(f"   📄 Block 0 type: {type(first_block)}")
    
    payload = None
    if isinstance(first_block, dict):
        payload = first_block.get('payload', {})
    elif hasattr(first_block, 'payload'):
        payload = first_block.payload
        
    print(f"   📦 Payload type: {type(payload)}")
    pprint(payload)

    # REPLICATING LOGIC FROM executive_report_stream.py
    items = None
    if isinstance(payload, list):
        print("   ✅ Payload is LIST")
        items = payload
    elif isinstance(payload, dict) and 'items' in payload:
        print("   ✅ Payload is DICT with 'items'")
        items = payload['items']
    elif hasattr(payload, 'items') and callable(payload.items):
        print("   ⚠️ Payload has .items() callable (Dict-like?)") 
        # CAREFUL: Dicts have .items(), but we want the key "items" if it's a wrapper
        # If it is a list wrapped in an object? 
        pass 
    elif hasattr(payload, 'items'):
        print("   ✅ Payload has .items attribute")
        items = payload.items
    
    if items:
        print(f"   🔢 Items count: {len(items)}")
        for idx, item in enumerate(items):
            # Handle both object and dict items
            if isinstance(item, dict):
                i_label = item.get('label', '')
                i_val = item.get('value', 0)
            else:
                i_label = getattr(item, 'label', '')
                i_val = getattr(item, 'value', 0)
                
            match = label_key.lower() in str(i_label).lower()
            status = "✅ MATCH" if match else "❌ NO MATCH"
            print(f"     [{idx}] Label='{i_label}' | Val={i_val} | Search='{label_key}' -> {status}")
            
            if match:
                return i_val
    else:
        print("   ❌ No 'items' found in payload.")

    return 0

async def run_test():
    print("🚀 STARTING BLOCK 1 ISOLATION TEST")
    
    # 1. Build Query for Headline (2025)
    queries = build_query_sequence("2025")
    headline_query = next(q for q in queries if q["section"] == "headline_current")
    
    print(f"📋 Executing query for section: {headline_query['section']}")
    
    # 2. Execute Query
    result = execute_semantic_query(
        intent=headline_query["intent"],
        cube_query=headline_query["cube_query"],
        metadata=headline_query.get("metadata", {}),
        limit=100
    )
    
    results = {"headline_current": result}
    
    # 3. Test Extraction
    val_tasa = get_kpi_value_debug(results, "headline_current", "Tasa")
    val_ceses = get_kpi_value_debug(results, "headline_current", "Ceses")
    val_hc = get_kpi_value_debug(results, "headline_current", "Headcount")
    
    print("\n📊 FINAL EXTRACTION RESULTS:")
    print(f"   Tasa: {val_tasa}")
    print(f"   Ceses: {val_ceses}")
    print(f"   Headcount: {val_hc}")

if __name__ == "__main__":
    asyncio.run(run_test())
