"""
Script para analizar qué tools está llamando el agente
"""
import sys
sys.path.insert(0, 'C:/Users/Lenovo/OneDrive/Documents/adk-people-analytics-backend')

from app.core.tools_rbac import get_allowed_tools

# Obtener todas las tools disponibles para ADMIN
tools = get_allowed_tools("ADMIN")

print("=" * 80)
print("TOOLS REGISTRADAS EN EL SISTEMA (Perfil ADMIN)")
print("=" * 80)

for i, tool in enumerate(tools, 1):
    print(f"\n{i}. {tool.__name__}")
    if hasattr(tool, '__doc__') and tool.__doc__:
        doc_lines = tool.__doc__.strip().split('\n')
        print(f"   Descripción: {doc_lines[0]}")

print("\n" + "=" * 80)
print("TOTAL DE TOOLS:", len(tools))
print("=" * 80)

# Verificar si get_monthly_trend está en la lista
tool_names = [t.__name__ for t in tools]
print("\n¿get_monthly_trend está registrada?", "get_monthly_trend" in tool_names)
print("¿get_monthly_attrition está registrada?", "get_monthly_attrition" in tool_names)
print("¿get_yearly_attrition está registrada?", "get_yearly_attrition" in tool_names)

print("\n" + "=" * 80)
print("ANÁLISIS DEL PROBLEMA")
print("=" * 80)

if "get_monthly_trend" in tool_names:
    print("✅ get_monthly_trend SÍ está registrada en tools_rbac.py")
    print("✅ El agente TIENE acceso a la tool")
    print("\n⚠️ PROBLEMA: El agente está ELIGIENDO NO USARLA")
    print("   Razón: El modelo de IA (Gemini) está generando texto en lugar de llamar a la tool")
    print("\n   Posibles soluciones:")
    print("   1. Hacer el prompt AÚN MÁS ESTRICTO")
    print("   2. Cambiar el modelo de IA")
    print("   3. Forzar la tool desde el router (pre-procesamiento)")
else:
    print("❌ get_monthly_trend NO está registrada")
    print("   Necesita ser añadida a tools_rbac.py")
