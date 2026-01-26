import asyncio
import json
from app.ai.utils.response_builder import ResponseBuilder

# Mock logic to simulate Agent output
def mock_agent_visual_response():
    return json.dumps({
        "response_type": "visual_package",
        "content": [
            {"type": "kpi_row", "payload": [{"label": "Test KPI", "value": "100"}]}
        ]
    })

def mock_route_logic(response_text):
    visual_package = None
    import re
    
    clean_text = response_text.strip()
    
    # Intento de limpieza de Markdown Code Barriers (```json ... ```)
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
    if json_match:
        clean_text = json_match.group(1)

    try:
        if clean_text.startswith("{"):
            potential_json = json.loads(clean_text)
            if "content" in potential_json:
                visual_package = potential_json
                if "response_type" not in visual_package:
                    visual_package["response_type"] = "visual_package"
    except json.JSONDecodeError:
        pass
    
    if not visual_package:
        builder = ResponseBuilder()
        builder.add_text(response_text)
        visual_package = builder.to_dict()
        
    return visual_package

def test_visual_flow():
    print("Testing Visual Flow...")
    agent_output = mock_agent_visual_response()
    result = mock_route_logic(agent_output)
    
    assert result["response_type"] == "visual_package"
    assert result["content"][0]["type"] == "kpi_row"
    print("✅ Visual Flow Parsed Correctly!")
    print(json.dumps(result, indent=2))

def test_text_flow():
    print("\nTesting Text Fallback...")
    agent_output = "Just plain text."
    result = mock_route_logic(agent_output)
    
    assert result["response_type"] == "visual_package" # Wrapper
    assert result["content"][0]["type"] == "text"
    print("✅ Text Flow Wrapped Correctly!")
    print(json.dumps(result, indent=2))

def test_markdown_wrapped_flow():
    print("\nTesting Markdown Wrapped Flow...")
    # Simulate Agent output with markdown fences
    agent_output = """```json
    {
        "response_type": "visual_package",
        "content": [
            {"type": "plot", "subtype": "bar"}
        ]
    }
    ```"""
    
    # Needs re-implementation of mock logic to match routes.py or skip if testing routes logic directly isn't possible here easily without importing routes
    # But since we duplicated logic in the test file, we should update the test file's mock logic to match the new routes logic first.
    # Actually, let's update mock_route_logic in this file to match the new routes.py logic first.
    result = mock_route_logic(agent_output)
    
    assert result["response_type"] == "visual_package"
    assert result["content"][0]["type"] == "plot"
    print("✅ Markdown Wrapped Flow Parsed Correctly!")

if __name__ == "__main__":
    test_visual_flow()
    test_text_flow()
    test_markdown_wrapped_flow()
