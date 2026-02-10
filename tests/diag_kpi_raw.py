"""
Diagnóstico: Inspeccionar estructura RAW de headline_current
"""
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.tools.executive_report_orchestrator import build_query_sequence
from app.ai.tools.universal_analyst import execute_semantic_query

def run_diagnostic():
    print("🚀 Iniciando diagnóstico de headline_current...")
    
    # 2025 Global
    all_queries = build_query_sequence("2025", None)
    
    # Buscar el query de headline_current
    headline_query = next((q for q in all_queries if q["section"] == "headline_current"), None)
    
    if not headline_query:
        print("❌ No se encontró el query de headline_current")
        return

    print(f"📋 Ejecutando query: {headline_query['intent']}")
    
    try:
        result = execute_semantic_query(
            intent=headline_query["intent"],
            cube_query=headline_query["cube_query"],
            metadata=headline_query.get("metadata", {}),
            limit=headline_query["cube_query"].get("limit")
        )
        
        print("\n📦 ESTRUCTURA COMPLETA DEL RESULTADO:")
        # Serializar con cuidado por si hay objetos no serializables
        def default_serializer(obj):
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            return str(obj)
            
        print(json.dumps(result, indent=2, default=default_serializer))
        
        # Probar extracción manualmente
        content = result.get("content", [])
        if content:
            first = content[0]
            payload = first.get("payload") if isinstance(first, dict) else getattr(first, "payload", None)
            print(f"\n💡 Payload type: {type(payload)}")
            print(f"💡 Payload content: {payload}")
            
            items = []
            if isinstance(payload, list): items = payload
            elif isinstance(payload, dict): items = payload.get("items", [])
            
            print(f"💡 Items: {items}")
            
            for i in items:
                label = i.get("label") if isinstance(i, dict) else getattr(i, "label", "")
                val = i.get("value") if isinstance(i, dict) else getattr(i, "value", 0)
                print(f"   -> Found: '{label}' = {val} ({type(val)})")

    except Exception as e:
        print(f"❌ Error en diagnóstico: {e}")

if __name__ == "__main__":
    run_diagnostic()
