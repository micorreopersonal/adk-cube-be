import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.tools.executive_report_orchestrator import generate_executive_report

def test_orchestrator():
    print("\n🧪 Testing Executive Report Orchestrator with Real Data")
    print("=" * 60)
    
    try:
        result = generate_executive_report("202512")
        
        print(f"\n✅ Report generated successfully!")
        print(f"Response Type: {result.get('response_type')}")
        print(f"Summary: {result.get('summary')}")
        print(f"Total Blocks: {len(result.get('content', []))}")
        
        # Count section headers
        content = result.get('content', [])
        headers = [block for block in content if isinstance(block, dict) and block.get('variant') == 'h3']
        print(f"Section Headers: {len(headers)}")
        
        # Show first few blocks
        print("\n📋 First 5 blocks:")
        for i, block in enumerate(content[:5]):
            if isinstance(block, dict):
                print(f"  {i+1}. Type: {block.get('type', 'unknown')}, Variant: {block.get('variant', 'N/A')}")
                if block.get('type') == 'TEXT':
                    payload = block.get('payload', '')
                    preview = payload[:100] + '...' if len(payload) > 100 else payload
                    print(f"     Preview: {preview}")
        
        print("\n" + "=" * 60)
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_orchestrator()
