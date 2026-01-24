from typing import List
# Importar ADK cuando esté configurado
# from adk import Agent, Router

class AgentRouter:
    """
    Orquestador principal que redirige las consultas a los agentes especialistas:
    - hr_agent: Consultas sobre rotación, headcount y BigQuery.
    - docs_agent: Consultas sobre políticas y reglamentos en PDF/GCS.
    """
    def __init__(self):
        self.name = "Router"
        # Aquí se inicializarán los agentes reales de ADK

    async def route(self, message: str) -> str:
        # Por ahora, solo funciona como un eco inteligente hasta integrar ADK real
        return f"Recibí tu mensaje: '{message}'. El sistema multi-agente está siendo configurado."

def get_router():
    return AgentRouter()
