import sys
import os

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, project_root)

from app.ai.tools.bq_queries.leavers import get_leavers_distribution

def debug_invalid_params():
    print("Simulating LLM calling get_leavers_distribution with unexpected 'talento' argument...")
    try:
        # This simulates what happens if the LLM hallucinates a parameter
        res = get_leavers_distribution(
            periodo="2025-12", 
            breakdown_by="division",
            talento_only=True # HALLUCINATED PARAMETER
        )
        print("RESULT:", res)
    except TypeError as e:
        print(f"\n[CRITICAL] CAUGHT EXPECTED ERROR: {e}")
        print("This TypeError in a tool call CRASHES the current Agent implementation if not caught in the Runner loop.")
    except Exception as e:
        print(f"FAILED with unexpected error: {e}")

if __name__ == "__main__":
    debug_invalid_params()
