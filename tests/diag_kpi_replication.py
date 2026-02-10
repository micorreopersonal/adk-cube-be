"""
Diagnóstico 2: Replicar extracción EXACTA de executive_report_stream.py
"""
import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.tools.executive_report_orchestrator import build_query_sequence
from app.ai.tools.universal_analyst import execute_semantic_query

def run_diagnostic():
    print("🚀 Replicando extracción de executive_report_stream.py...")
    
    results = {}
    all_queries = build_query_sequence("2025", None)
    
    # 1. Simular ejecución de queries
    for q in all_queries:
        if q["section"] in ["headline_current", "headline_previous", "annual_stats"]:
            print(f"⏳ Querying: {q['section']}")
            res = execute_semantic_query(
                intent=q["intent"],
                cube_query=q["cube_query"],
                metadata=q.get("metadata", {}),
                limit=q["cube_query"].get("limit")
            )
            results[q["section"]] = res

    # 2. Definir función EXACTA del stream
    def get_kpi_value(section_key: str, label_key: str) -> float:
        """Extract KPI value from query results."""
        if section_key in results and "content" in results[section_key]:
            content = results[section_key]["content"]
            
            if content and len(content) > 0:
                first_block = content[0]
                
                payload = None
                if isinstance(first_block, dict):
                    payload = first_block.get('payload', {})
                elif hasattr(first_block, 'payload'):
                    payload = first_block.payload
                
                # Check for items
                items = None
                if isinstance(payload, list):
                    items = payload
                elif isinstance(payload, dict) and 'items' in payload:
                    items = payload['items']
                elif hasattr(payload, 'items') and callable(payload.items):
                    items = payload.items() 
                elif hasattr(payload, 'items'):
                    items = payload.items 
                
                if items:
                    for item in items:
                        # Handle both object and dict items
                        if isinstance(item, dict):
                            i_label = item.get('label', '')
                            i_val = item.get('value', 0)
                        else:
                            i_label = getattr(item, 'label', '')
                            i_val = getattr(item, 'value', 0)
                            
                        if label_key.lower() in str(i_label).lower():
                            return i_val
        return 0

    # 3. Test de extracción
    headline_actual = {
        "tasa": get_kpi_value("headline_current", "Tasa"),
        "ceses": get_kpi_value("headline_current", "Ceses"),
        "hc": get_kpi_value("headline_current", "Headcount")
    }
    
    print("\n📊 RESULTADOS DE EXTRACCIÓN (Simulando Stream):")
    print(json.dumps(headline_actual, indent=2))
    
    if headline_actual["tasa"] == 0:
        print("❌ ERROR: La extracción devolvió 0")
    else:
        print(f"✅ ÉXITO: Se extrajo {headline_actual['tasa']}")

if __name__ == "__main__":
    run_diagnostic()
