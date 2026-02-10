"""
Test Directo: Generación de Insights AI
----------------------------------------
Este test llama directamente al generador de insights para diagnosticar 
por qué está retornando "[AI Narrative Unavailable]" en lugar de narrativas.
"""

import sys
import os
import logging

# Add root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.ai.tools.executive_insights import ReportInsightGenerator

def test_direct_insight_generation():
    """Test directo para generar un insight y capturar errores."""
    print("\n" + "="*80)
    print("🔍 TEST DIRECTO: Generación de Insights AI")
    print("="*80)
    
    # Initialize generator
    print("\n⏳ Inicializando generador de insights...")
    generator = ReportInsightGenerator()
    
    # Check if client initialized
    if not generator.client:
        print("❌ PROBLEMA: El cliente LLM no se inicializó correctamente")
        print("   Revisa las variables de entorno (PROJECT_ID, GOOGLE_GENAI_USE_VERTEXAI)")
        return
    
    print("✅ Cliente LLM inicializado correctamente\n")
    
    # Test 1: Insight Crítico
    print("─"*80)
    print("TEST 1: Generación de Insight Crítico")
    print("─"*80)
    
    test_context = {
        "headline_actual": {"tasa": 5.2, "ceses": 15, "hc": 288},
        "headline_prev": {"tasa": 4.8, "ceses": 14, "hc": 292},
        "annual_stats": {"tasa_avg": 4.9, "ceses_total_range": 165, "hc_avg": 290}
    }
    
    print(f"Contexto de prueba: {test_context}\n")
    
    try:
        print("⏳ Generando insight crítico...")
        insight = generator.generate_section_insight(
            "critical_insight",
            test_context,
            "Año 2025"
        )
        
        print(f"\n📝 Resultado:\n{insight}\n")
        
        if "[AI Narrative Unavailable]" in insight:
            print("❌ FALLO: El insight retornó placeholder en lugar de narrativa generada")
            print("   Esto indica que hubo una excepción en _generate() o _generate_with_retry()")
        elif "Quota Exceeded" in insight:
            print("❌ FALLO: Error de cuota (429 - RESOURCE_EXHAUSTED)")
            print("   Solución: Esperar o aumentar cuota de Vertex AI")
        elif "Client Error" in insight:
            print("❌ FALLO: El cliente LLM no está disponible")
        else:
            print("✅ ÉXITO: Insight generado correctamente")
            
    except Exception as e:
        print(f"\n❌ EXCEPCIÓN CAPTURADA: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Segmentation Insight
    print("\n" + "─"*80)
    print("TEST 2: Generación de Insight de Segmentación")
    print("─"*80)
    
    seg_context = {"raw_result": "ADMIN: 152 (Segmento), FFVV: 89 (Segmento)"}
    
    print(f"Contexto de prueba: {seg_context}\n")
    
    try:
        print("⏳ Generando insight de segmentación...")
        insight = generator.generate_section_insight(
            "segmentation",
            seg_context,
            "Año 2025"
        )
        
        print(f"\n📝 Resultado:\n{insight}\n")
        
        if "[AI Narrative Unavailable]" in insight:
            print("❌ FALLO: El insight retornó placeholder")
        elif "Quota Exceeded" in insight:
            print("❌ FALLO: Error de cuota (429)")
        else:
            print("✅ ÉXITO: Insight generado correctamente")
            
    except Exception as e:
        print(f"\n❌ EXCEPCIÓN CAPTURADA: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "="*80)
    print("📊 DIAGNÓSTICO FINAL")
    print("="*80)
    print("\nRevisa los logs DEBUG arriba para ver:")
    print("  - Si hay errores de autenticación con Vertex AI")
    print("  - Si hay errores 429 (Quota Exceeded)")
    print("  - Si hay timeout de red")
    print("  - Si el prompt llega correctamente al LLM")

if __name__ == "__main__":
    test_direct_insight_generation()
