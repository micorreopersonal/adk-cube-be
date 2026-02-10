
from app.services.query_generator import build_analytical_query

params = {
    "metrics": ["tasa_rotacion"],
    "dimensions": ["uo2"],
    "filters": {"anio": 2025}
}
query = build_analytical_query(**params)
print("Generated SQL:")
print(query)

expected_snippet = "NOT (LOWER(segmento) LIKE '%practicante%')"
if expected_snippet in query:
    print("\nSUCCESS: Snippet found.")
else:
    print(f"\nFAILURE: Snippet '{expected_snippet}' NOT found.")
