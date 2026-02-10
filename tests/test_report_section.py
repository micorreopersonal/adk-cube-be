
import sys
import os

# Add root to python path to allow module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
from app.ai.tools.executive_report_orchestrator import generate_executive_report
from app.schemas.payloads import VisualDataPackage, TextBlock, KPIBlock, ChartBlock, TableBlock

def main():
    parser = argparse.ArgumentParser(description="Test Executive Report Generation by Section")
    parser.add_argument("--period", type=str, default="2025", help="Period to analyze (YYYY, YYYYQN, YYYYMM)")
    parser.add_argument("--section", type=str, required=True, help="Section to generate (headline, segmentation, voluntary, talent, trend, conclusion)")
    
    args = parser.parse_args()
    
    print(f"Testing Section: {args.section} for Period: {args.period}")
    
    try:
        result = generate_executive_report(args.period, sections=[args.section])
        
        # Check if result is valid
        if result.get("response_type") == "error":
            print(f"ERROR: {result.get('summary')}")
            return

        print(f"SUCCESS: Report generated with {len(result['content'])} blocks.\n")
        
        # Print block types and first few chars of content
        for block in result['content']:
             if isinstance(block, dict):
                 block_type = block.get('type', 'UNKNOWN')
                 payload = block.get('payload', '')
             else:
                 block_type = block.type
                 payload = block.payload
                 
             payload_preview = str(payload)[:100] + "..." if isinstance(payload, str) else type(payload).__name__
             print(f" - [{block_type}] {payload_preview}")
             
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
