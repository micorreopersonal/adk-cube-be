# Manifiesto de Arquitectura y Gobernanza: ADK People Analytics

**Versión:** 1.0 (MVP)  
**Fecha:** Enero 2026  
**Contexto:** Ecosistema de IA Empresarial (Google ADK)

---

## 1. Narrativa Conceptual: Sostenibilidad y Escala

El proyecto **ADK People Analytics** no es solo un backend; es un sistema vivo diseñado para democratizar el acceso a métricas complejas de RRHH mediante lenguaje natural. Nuestra arquitectura se fundamenta en tres pilares que garantizan un ciclo de vida sostenible:

1.  **Directory as Context:** La estructura del proyecto es la documentación misma. Cada carpeta tiene un propósito único y explícito, permitiendo que tanto humanos como agentes de IA naveguen y entiendan el sistema sin ambigüedades.
2.  **Stateless by Design:** Todo el sistema es desacoplado y sin estado (a excepción de la persistencia en Firestore), lo que permite una escalabilidad horizontal infinita en **Cloud Run** con costos cercanos a cero en reposo.
3.  **Seguridad en Capas (Defense in Depth):** La seguridad no es un "feature", es la base. Desde la sanitización de inputs hasta el enmascaramiento de datos sensibles en logs, cada capa asume un entorno hostil.

---

## 2. Capas Metodológicas y Equilibrio del Flujo

Para mantener el equilibrio entre velocidad de desarrollo y robustez, implementamos una arquitectura hexagonal simplificada:

### A. Capa de Cerebro (Probabilística) - `app/ai/`
Aquí reside la inteligencia.
*   **Agentes:** Orquestadores que deciden *qué* hacer (e.g., `HR Agent`).
*   **Tools:** Habilidades determinísticas y probadas (SQL, Cálculos). **Regla de oro:** El agente piensa, la tool ejecuta.
*   **Evals:** Pruebas automatizadas para medir la calidad de las respuestas (alucinaciones, precisión).

### B. Capa de Seguridad (Core) - `app/core/`
El guardián del sistema.
*   **RBAC (Role Based Access Control):** No todos ven todo. Un `ANALISTA` no ejecuta las mismas tools que un `GERENTE`.
*   **Anonymization:** Rutinas estrictas (masking) para nunca exponer PII (RUTs, Salarios) en logs o respuestas no autorizadas.
*   **Config:** Gestión centralizada y validada de variables de entorno (Pydantic Settings).

### C. Capa de Músculo (Servicios) - `app/services/`
La lógica dura confiable.
*   **Conectores Singleton:** Gestión eficiente de conexiones a BigQuery y Firestore para evitar fugas de memoria.
*   **Lógica de Negocio Pura:** Cálculos de rotación agnósticos a la IA.

---

## 3. Ciclo de Vida y Mejores Prácticas

Nuestro flujo de trabajo asegura calidad continua:

1.  **Planning First:** Ninguna línea de código se escribe sin un "Implementation Plan" aprobado (`plans/`).
2.  **Testing Multinivel:**
    *   *Unitarias:* Validan la lógica (e.g., cálculo correcto de KPI).
    *   *Funcionales:* Validan el flujo completo (Request -> Auth -> Agent -> Tool -> Response).
3.  **Governance as Code:** Las reglas no están en wikis olvidadas, están en `GLOBAL_RULES.md` y se hacen cumplir en cada PR.

---

## 4. CAPÍTULO ESPECIAL: Gobernanza GCP y Riesgos IA

Desarrollar con IA Asistida conlleva riesgos únicos: código inflado, consultas ineficientes y costos ocultos. Implementamos mecanismos de contención ("Circuit Breakers") para mitigar estos riesgos a CERO.

### A. Control de Costos (FinOps)
*   **Consultas Optimimzadas:** Las tools usan `SELECT columns` explícitos, nunca `SELECT *` descontrolados sobre tablas masivas.
*   **Partitioning & Clustering:** Las tablas de BigQuery (`fecha_corte`) están particionadas para que las consultas del agente solo escaneen los datos necesarios (mes actual vs historia completa).
*   **Presupuestos Cloud:** Alertas de facturación configuradas en GCP al 50%, 80% y 100% del presupuesto mensual.
*   **Scale to Zero:** Cloud Run se apaga si no hay tráfico, garantizando costo cero fuera de horario laboral.

### B. Eficiencia de Código y Memoria
*   **Generadores vs Listas:** Para procesar grandes volúmenes de datos (ETL), exigimos el uso de generadores (`yield`) para mantener el consumo de RAM constante y bajo (<512MB), apto para contenedores micro.
*   **No Pandas en Producción (ETL):** En pipelines de carga masiva, prohibimos Pandas en favor de streaming nativo para evitar *OOM (Out of Memory)* errors.
*   **Revisión de Dependencias:** El agente tiene prohibido instalar librerías pesadas si existe una alternativa estándar ligera.

### C. Seguridad en el Desarrollo Asistido (AI Safety)
*   **Human in the Loop:** El agente propone cambios (Diffs), pero el humano aprueba. El despliegue a producción (`deploy.ps1`) requiere interacción humana explícita.
*   **Sandboxing de Pruebas:** Las pruebas destructivas o de carga se ejecutan en un entorno aislado, nunca contra datos productivos de escritura.
*   **Secret Management:** El código generado por IA nunca contiene credenciales. Se fuerza el uso de `os.environ` y Secret Manager.

---

**Conclusión:**
Este sistema está construido para ser auditado, escalado y operado con confianza empresarial, equilibrando la innovación de la IA con la disciplina de la ingeniería de software tradicional.
