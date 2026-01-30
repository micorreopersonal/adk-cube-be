import sys
import os
import requests
import pytest
import re
from datetime import datetime

# Asegurar que podemos importar modulos de la app
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
sys.path.insert(0, project_root)

from app.ai.tools.bq_queries.hr_metrics import get_monthly_attrition
from app.core.config import get_settings

# TUS-002: Verificación de Consistencia (Ground Truth Eval)
BASE_URL = "http://localhost:8080"
DEV_TOKEN = "dev-token-mock"

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

def test_consistency_turnover_rate():
    """
    COMPARA:
    1. Ground Truth: Ejecución directa de la tool `get_monthly_attrition`.
    2. Agent Response: Chat con el LLM.
    VALIDA: Identidad Numérica.
    """
    print("\n[EVAL] Iniciando Test de Consistencia de Datos (Ground Truth)...")
    
    # Init Report
    report = [
        "# TUS-002: Data Consistency Evidence",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "**Test:** Ground Truth Verification (Turnover Rate)",
        "---",
        "## Execution Log"
    ]
    
    # PARAMETROS DEL TEST
    YEAR = 2025
    MONTH = 1 # Enero
    QUESTION = f"¿Cuál fue la tasa de rotación general en Enero de {YEAR}?"
    
    report.append(f"**Parameters:** Month={MONTH}, Year={YEAR}")
    report.append(f"**Probe Question:** '{QUESTION}'\n")

    test_passed = False
    error_msg = ""
    
    try:
        # 1. OBTRNER GROUND TRUTH (Directo de BQ)
        print(f" 1. Calculando Ground Truth (SQL Directo)...")
        
        try:
            truth_data = get_monthly_attrition(month=MONTH, year=YEAR)
            
            # Extraction logic (Copied from verified previous version)
            truth_percentage = 0.0
            found_truth = False
            content_list = truth_data.get("content", [])
            
            for item in content_list:
                if item.get("type") == "kpi_row":
                    kpi_data = item.get("payload") or item.get("data") or []
                    for kpi in kpi_data:
                        lbl = kpi.get("label", "")
                        val = kpi.get("value", "")
                        if "Rotaci" in lbl and "Voluntaria" not in lbl:
                            val_str = val.replace("%", "").strip()
                            truth_percentage = float(val_str)
                            found_truth = True
                            break
                if found_truth:
                    break
            
            if not found_truth:
                raise ValueError("Ground Truth KPI not found in Tool Response.")
            
            print(f"    > Ground Truth (Extracted): {truth_percentage:.2f}%")
            report.append(f"### 1. Ground Truth (SQL)\n*   **Extracted Value:** `{truth_percentage:.2f}%`")
            
        except Exception as e:
            msg = f"Fallo al calcular Ground Truth: {e}"
            report.append(f"❌ **ERROR Ground Truth:** {msg}")
            raise RuntimeError(msg)

        # 2. OBTENER RESPUESTA AGENTE
        print(f" 2. Consultando al Agente...")
        headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
        payload = {
            "message": QUESTION, 
            "session_id": "eval-session-consistency-report",
            "context_profile": "ADMIN"
        }
        
        try:
            resp = requests.post(f"{BASE_URL}/chat", headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
                
            agent_text = resp.json()["response"]
            print(f"    > Agente dice: {agent_text[:60]}...")
            
            report.append(f"\n### 2. Agent Response (Chat)\n*   **Raw Text:** \"{agent_text}\"")
            
        except Exception as e:
            msg = f"Fallo al consultar Agente: {e}"
            report.append(f"❌ **ERROR Agent:** {msg}")
            raise RuntimeError(msg)

        # 3. EXTRACCIÓN Y COMPARACIÓN
        regex_pattern = r"(\d+[.,]?\d*)\s*%"
        match = re.search(regex_pattern, agent_text)
        
        if not match:
            msg = "El agente no proporcionó un porcentaje legible."
            report.append(f"\n### 3. Comparison\n❌ **FAIL:** {msg}")
            raise RuntimeError(msg)
            
        extracted_value = float(match.group(1).replace(",", "."))
        diff = abs(truth_percentage - extracted_value)
        
        print(f" 3. Comparando: {truth_percentage:.2f}% vs {extracted_value:.2f}%")
        report.append(f"\n### 3. Comparison\n*   **SQL:** `{truth_percentage:.2f}%`\n*   **Agent:** `{extracted_value:.2f}%`\n*   **Delta:** `{diff:.4f}%`")
        
        if diff > 0.1:
            msg = f"Diferencia {diff:.4f}% excede tolerancia 0.1%."
            report.append(f"❌ **FAIL:** {msg}")
            raise AssertionError(msg)
        else:
            report.append("✅ **RESULT: PASS** (Identity Confirmed)")
            test_passed = True
            print("✅ [PASS]")

    except Exception as e:
        error_msg = str(e)
        test_passed = False
    
    # Save Report
    save_report(report, "TUS-002", test_passed)
    
    if not test_passed:
        pytest.fail(error_msg)

if __name__ == "__main__":
    test_consistency_turnover_rate()
