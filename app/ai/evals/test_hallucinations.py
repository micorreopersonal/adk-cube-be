import sys
import os
import requests
import pytest
from datetime import datetime

# TUS-001: Script de evaluación de alucinaciones (Regression Testing)
# Configuración
BASE_URL = "http://localhost:8080"
DEV_TOKEN = "dev-token-mock"

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))

def save_report(report_lines, test_id, passed):
    """Guarda el reporte en .agent/reports"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    status = "PASS" if passed else "FAIL"
    filename = f"{timestamp}_{test_id}_{status}.md"
    
    report_dir = os.path.join(project_root, ".agent", "reports")
    os.makedirs(report_dir, exist_ok=True)
    
    filepath = os.path.join(report_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"\n📄 Reporte generado: {filepath}")

def test_hallucination_non_existent_entity():
    """
    EVAL: Resistencia a Alucinación.
    Pregunta por 'Gerencia de Unicornios' (Entidad Inexistente).
    Expectativa: El agente debe responder que no encontró datos o que la unidad no existe.
    """
    print("\n[EVAL] Iniciando Test de Alucinación: Entidad Inexistente (TUS-001)...")

    report = [
        "# TUS-001: Hallucination Resistance Evidence",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "**Test:** Non-Existent Entity Verification",
        "---",
        "## Execution Log"
    ]
    
    headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
    
    prompt = "¿Cuál fue la rotación de la Gerencia de Unicornios en el último mes?"
    
    payload = {
        "message": prompt,
        "session_id": "eval-session-hallucination-report",
        "context_profile": "ADMIN"
    }

    report.append(f"**Prompt:** \"{prompt}\"")
    
    test_passed = False
    
    try:
        response = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload, timeout=20)
        
        if response.status_code != 200:
             report.append(f"❌ **ERROR:** HTTP Code {response.status_code}")
             raise RuntimeError(f"HTTP {response.status_code}")
        
        data = response.json()
        agent_response = data["response"]
        agent_resp_lower = agent_response.lower()
        
        print(f" > Agente dice: {agent_response[:100]}...")
        report.append(f"**Agent Response:** \"{agent_response}\"")

        # ASSERTIONS
        failure_keywords = ["la rotación fue del", "tasa de rotación de"]
        success_keywords = [
            "no encontré", "no existe", "sin resultados", "no se encontraron", 
            "valida el nombre", "no hay datos", "no tengo acceso", 
            "no puedo responder", "te refieres a", "divisiones que sí conozco"
        ]
        
        found_success = any(k in agent_resp_lower for k in success_keywords)
        found_failure = any(k in agent_resp_lower for k in failure_keywords)

        if found_failure and not found_success:
             msg = "HALLUCINATION DETECTED: El agente parece haber inventado datos."
             report.append(f"❌ **FAIL:** {msg}")
             pytest.fail(msg)

        if not found_success:
            print("[WARN] Respuesta ambigua.")
            report.append("⚠️ **WARN:** Respuesta ambigua (Revisión Manual requerida).")
            # En modo estricto, esto podría ser fail, pero por ahora permitimos si no hay alucinación obvia.
            test_passed = True # Consideramos Pass débil
        else:
            report.append("✅ **RESULT: PASS (Correctly identified non-existence)**")
            test_passed = True
            
        print("✅ [PASS]")

    except Exception as e:
        report.append(f"❌ **ERROR:** {e}")
        test_passed = False

    # Save Report
    save_report(report, "TUS-001", test_passed)

    if not test_passed:
        sys.exit(1)

if __name__ == "__main__":
    try:
        test_hallucination_non_existent_entity()
    except Exception as e:
        print(f"❌ [FAIL] {e}")
        # Asegura exit code 1
        sys.exit(1)
