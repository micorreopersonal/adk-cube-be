"""
Test de Diagnóstico: Generación de Narrativas AI en Reporte Ejecutivo
-----------------------------------------------------------------------
Este test diagnostica por qué las narrativas aparecen como "[AI Narrative Unavailable]"
en lugar de mostrarse los insights generados por el LLM.
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

from app.ai.tools.executive_report_orchestrator import generate_executive_report
import json

def test_executive_report_narratives():
    """
    Test para generar reporte ejecutivo de año 2025 y diagnosticar 
    problemas de generación de narrativas AI.
    """
    print("\n" + "="*80)
    print("🔍 TEST DE DIAGNÓSTICO: Narrativas AI en Reporte Ejecutivo")
    print("="*80)
    print("Período: Año 2025")
    print("Objetivo: Identificar por qué las narrativas no se generan\n")
    
    try:
        # Generar reporte ejecutivo para todo el año 2025
        print("⏳ Generando reporte ejecutivo...")
        report = generate_executive_report("2025")
        
        if "error" in report:
            print(f"\n❌ Error al generar reporte: {report['error']}")
            return
        
        # Analizar contenido del reporte
        print(f"\n✅ Reporte generado exitosamente")
        print(f"Total de bloques: {len(report.get('content', []))}\n")
        
        # Buscar bloques de narrativa
        narrative_blocks = []
        unavailable_narratives = []
        
        for i, block in enumerate(report.get('content', []), 1):
            block_type = block.get('type', 'UNKNOWN') if isinstance(block, dict) else getattr(block, 'type', 'UNKNOWN')
            
            # Detectar bloques de texto que podrían ser narrativas
            if block_type == 'text':
                payload = block.get('payload', '') if isinstance(block, dict) else getattr(block, 'payload', '')
                variant = block.get('variant', '') if isinstance(block, dict) else getattr(block, 'variant', '')
                
                # Verificar si es una narrativa
                if variant in ['insight', 'standard', 'critical']:
                    if '[AI Narrative Unavailable]' in str(payload) or 'Narrative Unavailable' in str(payload):
                        unavailable_narratives.append({
                            'block_number': i,
                            'variant': variant,
                            'payload': payload[:100]
                        })
                        print(f"❌ Bloque {i} - Narrativa NO disponible (variant={variant})")
                    else:
                        narrative_blocks.append({
                            'block_number': i,
                            'variant': variant,
                            'payload': payload[:150]
                        })
                        print(f"✅ Bloque {i} - Narrativa generada (variant={variant})")
                        print(f"   Preview: {payload[:100]}...")
        
        # Resumen del diagnóstico
        print("\n" + "="*80)
        print("📊 RESUMEN DEL DIAGNÓSTICO")
        print("="*80)
        print(f"Total de bloques en reporte: {len(report.get('content', []))}")
        print(f"Narrativas generadas correctamente: {len(narrative_blocks)}")
        print(f"Narrativas NO disponibles: {len(unavailable_narratives)}")
        
        if unavailable_narratives:
            print("\n⚠️  PROBLEMA DETECTADO:")
            print(f"   {len(unavailable_narratives)} narrativa(s) no se generaron")
            print("\n   Posibles causas:")
            print("   1. Error en llamada al LLM (timeout, excepción)")
            print("   2. Cuota de API excedida (Error 429)")
            print("   3. Contexto vacío o inválido enviado al LLM")
            print("   4. Problema de manejo de errores en executive_insights.py")
            
            print("\n   Bloques afectados:")
            for item in unavailable_narratives:
                print(f"   - Bloque #{item['block_number']} (variant={item['variant']})")
        else:
            print("\n🎉 Todas las narrativas se generaron correctamente!")
        
        # Guardar reporte completo para análisis
        output_file = "tests/diagnostic_report_2025.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Reporte completo guardado en: {output_file}")
        print("   Puedes revisar el JSON para ver el contenido detallado de cada bloque")
        
    except Exception as e:
        print(f"\n❌ Error crítico durante el test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_executive_report_narratives()
