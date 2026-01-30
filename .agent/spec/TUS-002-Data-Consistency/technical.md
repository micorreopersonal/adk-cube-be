# Especificación Técnica (TUS-002)

## Implementación
*   **Script:** `app/ai/evals/test_data_consistency.py`
*   **Dependencies:**
    *   `app.ai.tools.bq_queries.attrition_queries` (Para Ground Truth).
    *   `requests` (Para interrogar al agente).
    *   `re` (Expresiones regulares para extraer números del chat).

## Flujo de Ejecución
1.  **Ground Truth Step:**
    ```python
    truth_data = get_monthly_attrition_query(2025, 1) # Ejecutar en BQ real
    expected_rate = truth_data['ratio_rotacion_general']
    ```
2.  **Agent Step:**
    ```python
    response = chat_with_agent("¿Rotación general Enero 2025?")
    predicted_text = response['response']
    ```
3.  **Extraction & Assertion:**
    *   Extraer floated del texto: `re.search(r"(\d+\.?\d*)%", predicted_text)`
    *   Comparar: `abs(expected_rate * 100 - extracted_rate) < 0.01`

## Trazabilidad
*   Etiquetar código con `# TUS-002`.
