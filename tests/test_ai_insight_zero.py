"""
Test de Aislamiento: Verificar si la IA genera insight con 0% 
cuando recibe datos válidos (25.97%)
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ai.tools.executive_insights import ReportInsightGenerator
from datetime import datetime

def test_critical_insight_with_real_data():
    """
    Simula el contexto exacto que se envía desde executive_report_stream.py
    para verificar si la IA devuelve 0% o el valor correcto.
    """
    
    ai_gen = ReportInsightGenerator()
    
    # Datos reales extraídos del sistema (confirmados en repro_kpi_extraction.py)
    context_payload = {
        "headline_actual": {
            "tasa": 25.965073529411764,
            "ceses": 1130.0,
            "hc": 2176.0
        },
        "headline_prev": {
            "tasa": 24.263387978142077,  # Valor anterior
            "ceses": 1071.0,
            "hc": 2213.0
        },
        "annual_stats": {
            "tasa_avg": 24.9,  # Promedio anual estimado
            "ceses_total_range": 1100.0,
            "hc_avg": 2200.0
        },
        "_cache_buster": str(datetime.now())
    }
    
    report_context = "2025 | Global"
    
    print("📋 Contexto enviado a la IA:")
    print(f"   - Tasa Actual: {context_payload['headline_actual']['tasa']:.2f}%")
    print(f"   - Tasa Anterior: {context_payload['headline_prev']['tasa']:.2f}%")
    print(f"   - Tasa Promedio Anual: {context_payload['annual_stats']['tasa_avg']:.2f}%")
    print(f"   - Contexto: {report_context}")
    print()
    
    # Generar insight
    print("🤖 Generando insight de IA...")
    insight = ai_gen.generate_section_insight(
        "critical_insight",
        context_payload,
        report_context
    )
    
    print(f"\n📄 Insight generado:\n{insight}")
    print()
    
    # Verificar si el insight menciona "0%"
    if "0%" in insight or "0 %" in insight or "cero" in insight.lower():
        print("❌ FALLO: La IA mencionó 0% a pesar de datos correctos")
        print("   Esto confirma el bug reportado.")
        return False
    elif "25" in insight or "26" in insight:
        print("✅ ÉXITO: La IA reconoce el valor correcto (~25-26%)")
        return True
    else:
        print("⚠️  AMBIGUO: La IA no menciona valores específicos")
        print("   Revisar insight manualmente")
        return None

if __name__ == "__main__":
    print("="*60)
    print("TEST DE AISLAMIENTO: ¿La IA genera 0% con datos válidos?")
    print("="*60)
    print()
    
    result = test_critical_insight_with_real_data()
    
    print()
    print("="*60)
    if result is True:
        print("CONCLUSIÓN: No se pudo replicar el bug. La IA responde correctamente.")
        print("El bug puede ser intermitente o ya estar resuelto.")
    elif result is False:
        print("CONCLUSIÓN: Bug confirmado. La IA alucina 0% con datos válidos.")
        print("Acción sugerida: Revisar prompt o cambiar temperatura del modelo.")
    else:
        print("CONCLUSIÓN: Resultado no concluyente. Revisar output manualmente.")
    print("="*60)
