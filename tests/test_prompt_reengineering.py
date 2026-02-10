import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

sys.path.append(os.getcwd())

from app.ai.tools.executive_report_orchestrator import parse_period, generate_executive_report, _get_report_prompts

def test_parse_period():
    print("Testing parse_period...")
    
    # Test Year
    p1 = parse_period("2025")
    print(f"Input '2025': {p1}")
    assert p1["granularity"] == "YEAR", "2025 should be YEAR"
    assert p1["year"] == 2025, "Year should be 2025"
    
    # Test Month
    p2 = parse_period("202512")
    print(f"Input '202512': {p2}")
    assert p2["granularity"] == "MONTH", "202512 should be MONTH"
    
    print("✅ parse_period passed.")

def test_prompt_builder():
    print("\nTesting _get_report_prompts...")
    
    # CASE 1: ANNUAL
    parsed_year = {"granularity": "YEAR", "year": 2025, "display": "AÑO 2025"}
    prompts_year = _get_report_prompts(parsed_year, "2024", "Global")
    
    print("YEAR Prompts (Headline):", prompts_year["headline_current"])
    assert "ACUMULADO para TODO EL AÑO 2025" in prompts_year["headline_current"]
    assert "MES" not in prompts_year["headline_current"]
    
    # CASE 2: MONTHLY
    parsed_month = {"granularity": "MONTH", "year": 2025, "display": "Diciembre 2025"}
    prompts_month = _get_report_prompts(parsed_month, "202511", "Global")
    
    print("MONTH Prompts (Headline):", prompts_month["headline_current"])
    assert "MES de Diciembre 2025" in prompts_month["headline_current"]
    assert "ACUMULADO para TODO EL AÑO" not in prompts_month["headline_current"]

    print("✅ _get_report_prompts passed.")

if __name__ == "__main__":
    test_parse_period()
    test_prompt_builder()
