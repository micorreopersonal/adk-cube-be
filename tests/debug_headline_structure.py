"""
Debug: Inspeccionar estructura de datos de headline_current
"""

import json
from app.ai.tools.executive_report_orchestrator import build_query_sequence
from app.ai.tools.universal_analyst import execute_semantic_query

# Build query for headline_current
queries = build_query_sequence("2025", None)
headline_query = [q for q in queries if q["section"] == "headline_current"][0]

print("="*80)
print("DEBUG: Estructura de headline_current")
print("="*80)
print(f"\nQuery config: {json.dumps(headline_query, indent=2, ensure_ascii=False)}")

# Execute query
limit = headline_query["cube_query"].pop("limit", None)
result = execute_semantic_query(
    intent=headline_query["intent"],
    cube_query=headline_query["cube_query"],
    metadata=headline_query.get("metadata", {}),
    limit=limit
)

print(f"\n\nResult keys: {result.keys()}")
print(f"Content type: {type(result.get('content', []))}")
print(f"Content length: {len(result.get('content', []))}")

if result.get('content'):
    first_block = result['content'][0]
    print(f"\nFirst block type: {type(first_block)}")
    
    if isinstance(first_block, dict):
        print(f"First block keys: {first_block.keys()}")
        print(f"\nFirst block dump:")
        print(json.dumps(first_block, indent=2, ensure_ascii=False, default=str))
    elif hasattr(first_block, '__dict__'):
        print(f"\nFirst block attributes: {dir(first_block)}")
        print(f"\nFirst block payload: {getattr(first_block, 'payload', 'NO PAYLOAD')}")

print("\n" + "="*80)
