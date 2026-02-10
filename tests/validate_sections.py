"""
Script para validar contexto de IA sección por sección
Muestra el contexto extraído para cada sección del reporte ejecutivo
"""

import sys
import os
import logging
from io import StringIO

# Add root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging to capture orchestrator output
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

from app.ai.tools.executive_report_orchestrator import generate_executive_report

# Secciones a validar
SECTIONS = ["headline", "segmentation", "voluntary", "talent", "trend"]

def test_section(section_name, period="202501"):
    """Test a single section and show context logs."""
    print(f"\n{'='*80}")
    print(f"🔍 VALIDANDO SECCIÓN: {section_name.upper()}")
    print(f"{'='*80}\n")
    
    try:
        # Generate report for this section
        report = generate_executive_report(period, sections=[section_name])
        
        # Check for errors
        if "error" in report:
            print(f"❌ Error: {report['error']}")
            return False
        
        # Show blocks generated
        blocks = report.get("content", [])
        print(f"\n📦 Bloques generados: {len(blocks)}")
        for i, block in enumerate(blocks, 1):
            block_type = block.get('type', 'UNKNOWN') if isinstance(block, dict) else getattr(block, 'type', 'UNKNOWN')
            print(f"   {i}. Tipo: {block_type}")
        
        print(f"\n✅ Sección '{section_name}' completada correctamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error crítico en '{section_name}': {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*80)
    print("🎯 VALIDACIÓN DE CONTEXTO - REPORTE EJECUTIVO")
    print("="*80)
    print(f"Período de prueba: 202501 (Enero 2025)")
    print(f"Secciones a validar: {len(SECTIONS)}")
    print("\nNOTA: Busca las líneas '🤖 [CTX]' en el output para ver el contexto")
    print("="*80)
    
    results = {}
    for section in SECTIONS:
        passed = test_section(section)
        results[section] = passed
        
        # Pause between sections
        print(f"\n{'─'*80}\n")
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 RESUMEN DE VALIDACIÓN")
    print(f"{'='*80}\n")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for section, passed_test in results.items():
        status = "✅ APROBADO" if passed_test else "❌ RECHAZADO"
        print(f"{status}: {section}")
    
    print(f"\n📈 Total: {passed}/{total} secciones aprobadas ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ¡Todas las secciones generaron bloques correctamente!")
    else:
        print(f"\n⚠️  {total - passed} sección(es) tuvieron errores")

if __name__ == "__main__":
    main()
