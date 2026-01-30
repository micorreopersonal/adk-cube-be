# TUS-002: Verificación de Consistencia (Ground Truth)

## Descripción Conceptual
**Como:** QA Engineer / Stakeholder de Datos.
**Quiero:** Validar que los números reportados por el Agente sean **100% idénticos** a los calculados por la base de datos oficial.
**Para:** Confiar ciegamente en las métricas entregadas y descartar "alucinaciones numéricas" o errores de redondeo del LLM.

## El Problema
Los LLMs son probabilísticos. Aunque usen Tools, a veces pueden:
1.  Leer mal el output JSON de la tool.
2.  Inventar un número si la tool falla.
3.  Redondear incorrectamente (ej. 45.4% -> 45%).

## La Solución ("Ground Truth Test")
Un script que:
1.  Calcula el valor REAL usando directamente la función Python (Bypaseando el LLM).
2.  Pregunta al Agente lo mismo.
3.  Compara `Valor_Chat == Valor_SQL`.
