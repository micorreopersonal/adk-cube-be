import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.getcwd())

try:
    from app.ai.tools.executive_report_orchestrator import build_query_sequence
    # universal_analyst is in ai/tools
    from app.ai.tools.universal_analyst import execute_semantic_query
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

def inspect_data():
    print("🔍 Inspecting 'headline_current' data structure...")
    
    # 1. Get query config
    # 2025 is a valid period
    queries = build_query_sequence("2025", None)
    headline_q = next(q for q in queries if q["section"] == "headline_current")
    
    print(f"\n📋 Query Config:\n{json.dumps(headline_q, indent=2, ensure_ascii=False)}")
    
    try:
        print("\n🚀 Executing query...")
        result = execute_semantic_query(
            intent=headline_q["intent"],
            cube_query=headline_q["cube_query"],
            metadata=headline_q.get("metadata", {})
        )
        
        print("\n✅ Query Result:")
        # Print first block structure
        if result and "content" in result:
            content = result["content"]
            print(f"Content length: {len(content)}")
            for i, block in enumerate(content):
                print(f"\nBlock {i} type: {type(block)}")
                if isinstance(block, dict):
                    print(json.dumps(block, indent=2, ensure_ascii=False, default=str))
                else:
                    print(f"Object: {block}")
                    if hasattr(block, 'payload'):
                        print(f"Payload: {block.payload}")
        else:
            print(f"⚠️ Result has no 'content': {result.keys()}")
            
    except Exception as e:
        print(f"\n❌ Error executing query: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_data()
