
import asyncio
import time
import os
import vertexai
from vertexai.generative_models import GenerativeModel
from google.api_core.exceptions import ResourceExhausted

# Configuración
PROJECT_ID = os.getenv("PROJECT_ID", "adk-sandbox-486117")
REGION = os.getenv("REGION", "us-central1")
MODEL_NAME = "gemini-2.0-flash"

# Parámetros del Stress Test
TOTAL_REQUESTS = 60      # Intentar 60 requests (1 por segundo promedio)
CONCURRENCY = 10         # 10 requests simultáneos
PROMPT = "Say 'OK'"

async def send_request(model, request_id):
    try:
        start = time.time()
        # Vertex AI GenerativeModel no es nativamente async aún en todas las versiones,
        # pero podemos ejecutarlo en un threadpool si bloquea, o usar la versión async si está disponible.
        # Para simplificar y estresar, usaremos el executor por defecto de asyncio.
        response = await asyncio.to_thread(model.generate_content, PROMPT)
        duration = time.time() - start
        return {"status": "OK", "duration": duration, "id": request_id}
    except ResourceExhausted:
        return {"status": "429", "duration": 0, "id": request_id}
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "id": request_id}

async def run_stress_test():
    print(f"🔥 Iniciando Stress Test de RPM para {MODEL_NAME} en {PROJECT_ID}")
    print(f"🎯 Meta: {TOTAL_REQUESTS} requests con concurrencia de {CONCURRENCY}")
    
    vertexai.init(project=PROJECT_ID, location=REGION)
    model = GenerativeModel(MODEL_NAME)
    
    start_time = time.time()
    
    tasks = []
    results = []
    
    # Semáforo para controlar concurrencia
    sem = asyncio.Semaphore(CONCURRENCY)
    
    async def bound_request(req_id):
        async with sem:
            return await send_request(model, req_id)

    # Crear tareas
    print("🚀 Lanzando requests...", end="", flush=True)
    for i in range(TOTAL_REQUESTS):
        tasks.append(bound_request(i))
    
    # Esperar resultados
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    print("\n\n📊 Resultados del Stress Test:")
    print("-" * 40)
    
    success_count = sum(1 for r in results if r["status"] == "OK")
    rate_limit_count = sum(1 for r in results if r["status"] == "429")
    error_count = sum(1 for r in results if r["status"] == "ERROR")
    
    avg_latency = 0
    if success_count > 0:
        avg_latency = sum(r["duration"] for r in results if r["status"] == "OK") / success_count

    real_rpm = (success_count / total_time) * 60
    
    print(f"⏱️ Tiempo Total:       {total_time:.2f} s")
    print(f"✅ Exitosos:           {success_count}")
    print(f"🛑 Rate Limited (429): {rate_limit_count}")
    print(f"❌ Otros Errores:      {error_count}")
    print(f"🐢 Latencia Promedio:  {avg_latency:.4f} s")
    print("-" * 40)
    print(f"📈 RPM LOGRADO:        {real_rpm:.2f} RPM")
    
    if rate_limit_count == 0:
        print("\n✨ El modelo soportó la carga SIN errores de cuota.")
    else:
        print("\n⚠️ Se alcanzó el límite de cuota.")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
