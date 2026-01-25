# 🤖 Project Blueprint: adk-people-analytics-backend

## 🎯 Business Context
Este sistema es el motor de una solución de **HR Analytics (División de Talento)**. El objetivo principal es el análisis de **churn/atrición de empleados** mediante agentes de IA que consumen datos de BigQuery y Excel.

## 🛠 Tech Stack (2026 Standard)
- **Language:** Python 3.12+
- **Agent Framework:** Google Agent Development Kit (ADK)
- **API:** FastAPI
- **Database:** BigQuery (Analítica) & Firestore (Estado/Sesiones)
- **Security:** JWT + RBAC (Role-Based Access Control)
- **Infra:** Docker + Google Cloud Run
- **Quality:** Pytest (Unit/Functional) + AI Evals (Regresión de Agentes)

## 📁 Architecture (State of the Art)
- `app/ai/`: Cerebro del sistema (Agents, Tools, Prompts).
- `app/core/`: Corazón técnico (Seguridad, Config, DB Connections).
- `app/services/`: Lógica determinística (Cálculos de KPIs de rotación).
- `app/schemas/`: Modelos Pydantic para validación de datos.
- `.agent/spec/`: Documentación funcional para consumo de IA.

## 🛡 Mandatory Rules
1. **Zero-Hardcoding:** Todo secreto va en `Secret Manager` o `.env`.
2. **Modular Tools:** Cada herramienta del agente debe ser una función independiente en `app/ai/tools/`.
3. **Traceability:** Cada acción del agente debe generar un log estructurado en `logs/`.
4. **Git Flow:** No se toca `main` sin pasar pruebas de `check_import.py` y `pytest`.