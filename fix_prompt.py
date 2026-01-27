"""
Script para añadir la regla crítica al prompt del agente
"""
import re

file_path = r"C:\Users\Lenovo\OneDrive\Documents\adk-people-analytics-backend\app\ai\agents\hr_agent.py"

# Leer el archivo
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar la línea donde termina la lista de herramientas
search_pattern = r"(- `get_leavers_list`: Listado NOMINAL de personas que cesaron.*?\n)\n"

replacement = r"""\1

**⚠️ REGLA CRÍTICA - PROHIBIDO GENERAR TEXTO SIN USAR TOOLS:**
Si el usuario pide datos (rotación, tendencia, leavers, etc.), NUNCA respondas con texto generado.
SIEMPRE debes llamar primero a la herramienta correspondiente y devolver su resultado.
Ejemplo: Si piden "tendencia mensual 2025", llama a get_monthly_trend(year=2025) y devuelve su JSON completo.
NO escribas "Aquí tienes la tendencia..." - ESO ESTÁ PROHIBIDO.

"""

# Reemplazar
new_content = re.sub(search_pattern, replacement, content, count=1)

# Verificar que se hizo el cambio
if new_content != content:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ Archivo modificado exitosamente")
    print("\nSe añadió la regla crítica después de la lista de herramientas")
else:
    print("❌ No se pudo encontrar el patrón para reemplazar")
    print("Buscando:", search_pattern)
