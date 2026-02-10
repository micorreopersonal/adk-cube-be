import asyncio
import logging
import json
from app.ai.tools.executive_report_orchestrator import generate_executive_report

logging.basicConfig(level=logging.INFO)

async def test_orchestrator():
    print("🚀 Testing Simplified Orchestrator 2025...")
    period = "202501"
    
    try:
        result = await generate_executive_report(period)
        print(f"✅ Success! Response Type: {result.get('response_type')}")
        print(f"📊 Summary: {result.get('summary')}")
        print(f"🧱 Block Count: {len(result.get('content', []))}")
        
        # Check for insights within blocks
        insights = [b for b in result.get('content', []) if b.get('variant') == 'insight']
        print(f"🤖 AI Insights Found: {len(insights)}")
        for i, b in enumerate(insights):
            print(f"   - Insight {i+1}: {b.get('payload')[:50]}...")

    except Exception as e:
        print(f"❌ Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())
