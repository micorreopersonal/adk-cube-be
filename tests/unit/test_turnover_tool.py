import json
from app.ai.tools.bq_queries.turnover import get_turnover_deep_dive

def test_turnover_deep_dive():
    print("Testing get_turnover_deep_dive...")
    
    # Test 1: Default args
    result = get_turnover_deep_dive()
    data = json.loads(result)
    
    assert data["response_type"] == "visual_package"
    assert len(data["content"]) >= 3
    print("✅ Default params passed.")
    
    # Test 2: Custom params
    result_custom = get_turnover_deep_dive(dimension="Ventas")
    data_custom = json.loads(result_custom)
    
    insight_block = next(b for b in data_custom["content"] if b.get("variant") == "insight")
    assert "Ventas" in insight_block["payload"]
    print("✅ Custom params passed.")

if __name__ == "__main__":
    test_turnover_deep_dive()
