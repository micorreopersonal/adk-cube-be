
from unittest.mock import MagicMock, patch
from app.ai.tools.executive_report_orchestrator import generate_executive_report
from app.schemas.payloads import VisualDataPackage, ChartBlock, ChartPayload, Dataset, ChartMetadata, KPIBlock, KPIItem, TableBlock, TablePayload

def test_full_report_prompts():
    # Mock execute_semantic_query to return structure for all sections
    with patch("app.ai.tools.executive_report_orchestrator.execute_semantic_query") as mock_exec, \
         patch("app.ai.tools.executive_insights.ReportInsightGenerator._generate") as mock_generate:
        
        # Setup Mock Generator Response
        mock_generate.return_value = "Insight Generated Successfully."

        # Mock Data for Sections
        mock_kpi = {
            "content": [
                KPIBlock(payload=[KPIItem(label="Tasa Rotación", value=5.5), 
                                  KPIItem(label="Ceses Totales", value=10),
                                  KPIItem(label="Headcount Promedio", value=200)])
            ]
        }
        
        mock_chart = {
            "content": [
                ChartBlock(
                    payload=ChartPayload(labels=["A", "B"], datasets=[Dataset(label="Tasa", data=[10, 20])]),
                    metadata=ChartMetadata(title="Mock Chat")
                )
            ]
        }

        mock_table = {
            "content": [
                TableBlock(
                    payload=TablePayload(headers=["Col1", "Col2"], rows=[{"Col1": "Val1", "Col2": "Val2"}]),
                    metadata=ChartMetadata(title="Mock Table")
                )
            ]
        }
        
        mock_pie = {
             "content": [
                ChartBlock(
                    payload=ChartPayload(labels=["Vol", "Invol"], datasets=[Dataset(label="Ceses", data=[8, 2])]),
                    metadata=ChartMetadata(title="Mock Pie")
                )
            ]
        }

        def side_effect(intent, cube_query, **kwargs):
            # Return appropriate mock based on intent/section hint
            if intent == "SNAPSHOT" and "tasa_rotacion_voluntaria" in cube_query.get("metrics", []):
                return mock_pie # Global Breakdown - PRIORITIZE THIS
            if intent == "SNAPSHOT" and "grupo_segmento" not in cube_query.get("dimensions", []):
                return mock_kpi # Generic Headline
            if intent == "COMPARISON":
                 if "grupo_segmento" in cube_query.get("dimensions", []): return mock_chart # Segmentation
                 if "uo2" in cube_query.get("dimensions", []): return mock_table # Voluntary Focus
            if intent == "LISTING":
                return mock_table # Talent Leakage
            if intent == "TREND":
                return mock_chart # Monthly Trend
            return {"content": []}

        mock_exec.side_effect = side_effect

        # Run Orchestrator
        generate_executive_report("2025")

        # Verify calls to _generate
        # We expect calls for: critical_insight, segmentation, voluntary_trend, talent_leakage, annual_trend, strategic_conclusion
        
        expected_snippets = {
            "Analiza los KPI de Rotación": "Critical Insight",
            "Analiza la rotación por segmento": "Segmentation",
            "Analiza la rotación voluntaria": "Voluntary",
            "Analiza la fuga de talento": "Talent",
            "Analiza la tendencia": "Trend",
            "CONCLUSIÓN ESTRATÉGICA FINAL": "Strategy"
        }
        
        found_snippets = set()
        
        for call in mock_generate.call_args_list:
            args, kwargs = call
            prompt = args[0]
            # print(f"DEBUG PROMPT: {prompt[:50]}...")
            
            for snippet, name in expected_snippets.items():
                if snippet in prompt:
                    found_snippets.add(name)
                    # Check for data presence
                    if name == "Segmentation":
                        if "A: 10" in prompt and "B: 20" in prompt: 
                            print(f"✅ {name} Prompt contains Chart Data")
                        else:
                            print(f"❌ {name} Prompt MISSING Data")
                    elif name == "Voluntary":
                        if "Vol: 8" in prompt:
                            print(f"✅ {name} Prompt contains Pie Data")
                        else:
                             print(f"❌ {name} Prompt MISSING Data. content: {prompt}")
                    elif name == "Talent":
                        if "Val1=Val1" in prompt: # Row content
                            print(f"✅ {name} Prompt contains Table Data")
                        else:
                            print(f"❌ {name} Prompt MISSING Data. content: {prompt}")

        missing = set(expected_snippets.values()) - found_snippets
        if not missing:
            print("\nSUCCESS: All expected prompts generated with context.")
        else:
            print(f"\nFAILURE: Missing prompts for: {missing}")

if __name__ == "__main__":
    test_full_report_prompts()
