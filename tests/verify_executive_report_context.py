
from unittest.mock import MagicMock, patch
from app.ai.tools.executive_report_orchestrator import generate_executive_report
from app.schemas.payloads import VisualDataPackage, ChartBlock, ChartPayload, Dataset, ChartMetadata

def test_context_extraction():
    # Mock execute_semantic_query to return a known structure
    with patch("app.ai.tools.executive_report_orchestrator.execute_semantic_query") as mock_exec, \
         patch("app.ai.tools.executive_report_orchestrator.ReportInsightGenerator") as mock_gen_cls:
        
        # Setup Mock Generator
        mock_gen = mock_gen_cls.return_value
        mock_gen.generate_section_insight.return_value = "Insight Dummy"
        mock_gen.generate_strategic_conclusion.return_value = "Conclusion Dummy"

        # Mock Return for Segmentation (Chart)
        mock_seg_result = {
            "content": [
                ChartBlock(
                    payload=ChartPayload(
                        labels=["Admin", "Sales"],
                        datasets=[Dataset(label="Tasa", data=[5.5, 12.3])]
                    ),
                    metadata=ChartMetadata(title="Mock Chat")
                )
            ]
        }
        
        # Mock Return for Headlines (to avoid errors)
        mock_head_result = {"content": []}
        
        def side_effect(intent, cube_query, **kwargs):
            if query_config := kwargs.get('metadata'):
                pass
            # Return specific mock based on inputs/calls order if needed
            # For simplicity, we just check call args later
            if intent == "COMPARISON" and "grupo_segmento" in cube_query.get("dimensions", []):
                return mock_seg_result
            return mock_head_result

        mock_exec.side_effect = side_effect

        # Run Orchestrator
        generate_executive_report("2025")

        # Verify generate_section_insight was called with extracted data
        # We look for the call responsible for 'segmentation'
        # Args: (section_name, context_dict, period)
        
        found = False
        for call in mock_gen.generate_section_insight.call_args_list:
            args, kwargs = call
            if args[0] == "segmentation":
                context = args[1]
                raw_result = context.get("raw_result", "")
                print(f"Captured Segmentation Context: {raw_result}")
                if "Admin: 5.5" in raw_result and "Sales: 12.3" in raw_result:
                    found = True
        
        if found:
            print("SUCCESS: Data extracted correctly for AI Context.")
        else:
            print("FAILURE: AI Context did not contain expected chart data.")

if __name__ == "__main__":
    test_context_extraction()
