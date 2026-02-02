
import time
import os
import vertexai
from vertexai.generative_models import GenerativeModel
import statistics

# Configuración
PROJECT_ID = os.getenv("PROJECT_ID", "adk-sandbox-486117")
REGION = os.getenv("REGION", "us-central1")
NUM_ITERATIONS = 3 # Reduced for quick verification

CANDIDATE_MODELS = [
    "gemini-3-flash-preview", 
    "gemini-3-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash"
]

PROMPT = "Explain briefly (in one sentence) the importance of People Analytics for retention."

def benchmark_model_iterations(model_name):
    print(f"\n--- Testing {model_name} ({NUM_ITERATIONS} iterations) ---")
    latencies = []
    
    try:
        model = GenerativeModel(model_name)
        
        for i in range(NUM_ITERATIONS):
            start_time = time.time()
            response = model.generate_content(PROMPT)
            end_time = time.time()
            
            latency = end_time - start_time
            latencies.append(latency)
            print(f"   Iter {i+1}: {latency:.4f}s")
            
        avg_latency = statistics.mean(latencies)
        min_latency = min(latencies)
        
        return {
            "model": model_name,
            "avg": avg_latency,
            "min": min_latency,
            "first": latencies[0],
            "status": "OK"
        }
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return {
            "model": model_name,
            "status": "ERROR"
        }

def run_benchmark():
    print(f"🚀 Iniciando Múltiples Iteraciones en {PROJECT_ID}...")
    vertexai.init(project=PROJECT_ID, location=REGION)
    
    results = []
    for model in CANDIDATE_MODELS:
        res = benchmark_model_iterations(model)
        results.append(res)
    
    # Tabla de Resultados
    print("\n" + "="*80)
    print(f"{'MODELO':<20} | {'COLD START (1st)':<18} | {'WARM AVG':<12} | {'MEJOR':<12}")
    print("-" * 80)
    
    best_model = None
    min_warm_avg = float('inf')
    
    for r in results:
        if r["status"] == "OK":
            print(f"{r['model']:<20} | {r['first']:<18.4f} | {r['avg']:<12.4f} | {r['min']:<12.4f}")
            
            if r['avg'] < min_warm_avg:
                min_warm_avg = r['avg']
                best_model = r['model']
        else:
            print(f"{r['model']:<20} | {'ERROR':<18} | {'-':<12} | -")
            
    print("="*80)
    print(f"🏆 Ganador general (Promedio): {best_model}")

if __name__ == "__main__":
    run_benchmark()
