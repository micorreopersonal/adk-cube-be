import asyncio
import time
import json
import os
import sys

# Asegurar que el path del proyecto esté disponible
sys.path.append(os.getcwd())

from app.ai.agents.router_logic import AgentRouter
from app.core.config.config import get_settings

async def run_rpm_test():
    router = AgentRouter()
    settings = get_settings()
    
    print("="*60)
    print("🚀 INICIANDO TEST DE EVALUACIÓN DE RPM / CUOTA API")
    print(f"Proyecto: {settings.PROJECT_ID}")
    print(f"Backend: Vertex AI (v1) en {settings.REGION}")
    print("="*60)

    # Escenarios de prueba: Consultas que disparan múltiples herramientas o reportes complejos
    queries = [
        "Dame el reporte ejecutivo de Marzo 2024 para la DIVISION FINANZAS.",
        "Compara la rotación de FFVV vs ADMI en el año 2024.",
        "Dime la tendencia de rotación de Riesgos y compárala con Operaciones en 2024.",
        "¿Hay alertas de talento crítico en la DIVISION COMERCIAL para Julio 2024?",
        "Haz un resumen ejecutivo anual del 2024 para toda la compañía."
    ]

    session_id = f"test-rpm-{int(time.time())}"
    results = []

    for i, query in enumerate(queries):
        print(f"\n[{i+1}/{len(queries)}] Enviando consulta: '{query}'")
        start_time = time.time()
        
        try:
            # Ejecutar consulta
            response = await router.route(query, session_id=session_id, profile="EJECUTIVO")
            duration = time.time() - start_time
            
            # Extraer telemetría (inyectada por el router_logic actualizado)
            telemetry = {}
            if isinstance(response, dict):
                telemetry = response.get("telemetry", {})
            
            turns = telemetry.get("model_turns", "N/A")
            api_calls = telemetry.get("api_invocations_est", "N/A")
            tools = telemetry.get("tools_executed", [])
            
            print(f"✅ Respuesta recibida en {duration:.2f}s")
            print(f"   📊 Telemetría: Turns={turns} | Est. API Calls={api_calls}")
            print(f"   🔧 Tools: {', '.join(tools) if tools else 'Ninguna'}")
            
            results.append({
                "query": query,
                "duration": duration,
                "turns": turns,
                "api_calls": api_calls,
                "tools": tools,
                "status": "success"
            })

            # Pequeña pausa para no saturar instantáneamente si el límite es muy bajo
            # Pero lo suficientemente corta para probar el RPM
            await asyncio.sleep(1)

        except Exception as e:
            print(f"❌ Error en consulta: {e}")
            results.append({
                "query": query,
                "error": str(e),
                "status": "error"
            })
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("🚨 BLOQUEO POR CUOTA (429) DETECTADO")

    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL DEL TEST")
    total_calls = sum(r.get("api_calls", 0) for r in results if isinstance(r.get("api_calls"), int))
    total_duration = sum(r.get("duration", 0) for r in results if r.get("status") == "success")
    
    print(f"Consultas Exitosas: {len([r for r in results if r['status'] == 'success'])}/{len(queries)}")
    print(f"Total API Calls estimadas: {total_calls}")
    print(f"Tiempo Total de ejecución: {total_duration:.2f}s")
    if total_duration > 0:
        print(f"Promedio RPM (est): {(total_calls / total_duration) * 60:.2f}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_rpm_test())
