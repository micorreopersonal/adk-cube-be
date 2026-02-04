import sys
import os
import pytest
from google.cloud import bigquery
from datetime import datetime

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
sys.path.insert(0, project_root)

from app.core.config.config import get_settings

# TUS-005: Cost Efficiency & Guardrails
# Objetivo: Verificar que nuestras queries típicas no excedan el presupuesto de bytes (1 GB).

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

def test_cost_efficiency_dry_run():
    """
    Ejecuta las queries más pesadas en modo DRY RUN.
    No cobra dinero.
    Verifica bytes procesados estimados.
    """
    print("\n[EVAL] Iniciando Test de Costos (Dry Run) TUS-005...")
    
    report = [
        "# TUS-005: Cost Efficiency Evidence",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "**Test:** BigQuery Dry Run Estimation",
        "**Limit:** 1 GB (1,000,000,000 bytes)",
        "---",
        "## Execution Log"
    ]
    
    settings = get_settings()
    client = bigquery.Client(project=settings.PROJECT_ID)
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    
    # 1. Definir Queries Representativas (Sample)
    # Usamos la tabla de turnover definida en settings
    table_id = f"{settings.PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_TABLE_TURNOVER}"
    
    queries = [
        {
            "name": "Metadata Check (1 Row)",
            "sql": f"SELECT fecha_corte, codigo_persona FROM `{table_id}` LIMIT 1"
        },
        {
            "name": "Monthly App Aggregation (Heavy)",
            "sql": f"""
                SELECT 
                    uo2, 
                    COUNT(*) as total_rows
                FROM `{table_id}`
                GROUP BY uo2
            """
        },
        {
            "name": "Granular Group By (Detailed)",
            "sql": f"""
                SELECT 
                    uo2, segmento, 
                    COUNT(codigo_persona) as hc 
                FROM `{table_id}` 
                WHERE fecha_corte >= '2024-01-01'
                GROUP BY uo2, segmento
            """
        }
    ]
    
    limit_bytes = 10**9 # 1 GB
    all_passed = True
    
    for q in queries:
        print(f"  ⚡ Estimando: {q['name']}...")
        report.append(f"\n### Query: {q['name']}")
        report.append(f"```sql\n{q['sql'].strip()[:200]}...\n```")
        
        try:
            query_job = client.query(q['sql'], job_config=job_config)
            bytes_processed = query_job.total_bytes_processed
            mb_processed = bytes_processed / (1024 * 1024)
            
            report.append(f"*   **Estimated Bytes:** `{bytes_processed:,} bytes` ({mb_processed:.2f} MB)")
            
            if bytes_processed > limit_bytes:
                msg = f"❌ **FAIL:** Excede límite de 1GB."
                print(f"     ❌ FAIL ({mb_processed:.2f} MB > 1000 MB)")
                report.append(msg)
                all_passed = False
            else:
                msg = f"✅ **PASS:** Dentro del presupuesto."
                print(f"     ✅ PASS ({mb_processed:.2f} MB)")
                report.append(msg)
                
        except Exception as e:
            msg = f"❌ **ERROR:** {e}"
            print(f"     ❌ ERROR: {e}")
            report.append(msg)
            all_passed = False

    # Save Report
    save_report(report, "TUS-005", all_passed)

    if not all_passed:
        pytest.fail("Cost Test Failed. Check report.")
        
    print("✅ [PASS] Todas las estimaciones de costo están dentro del límite.")

if __name__ == "__main__":
    test_cost_efficiency_dry_run()
