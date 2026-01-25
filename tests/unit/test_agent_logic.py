import pytest
import sys
from unittest.mock import MagicMock, patch

# Definir imports dentro de los tests o después del mock para evitar ImportError prematuro
# O mejor, mockear google.adk.Agent específicamente

def test_agent_tools_admin():
    """
    Validar que el perfil ADMIN recibe todas las herramientas.
    """
    with patch.dict(sys.modules, {"google.adk": MagicMock()}):
         # Mockear la clase Agent dentro del módulo mockeado
         mock_adk = sys.modules["google.adk"]
         mock_adk.Agent = MagicMock()
         
         # Importar aquí para que use el mock
         # Nota: si app.ai.agents.hr_agent ya fue importado, hay que recargarlo
         import importlib
         import app.ai.agents.hr_agent
         importlib.reload(app.ai.agents.hr_agent)
         
         from app.ai.agents.hr_agent import get_hr_agent
         from app.ai.tools.bq_queries.hr_metrics import get_monthly_attrition, get_talent_alerts
         from app.core.constants import ProfileEnum

         profile = ProfileEnum.ADMIN.value
         agent_mock = get_hr_agent(profile)
         
         call_args = mock_adk.Agent.call_args
         assert call_args is not None
         
         _, kwargs = call_args
         tools = kwargs.get("tools")
         
         assert len(tools) == 2
         assert get_monthly_attrition in tools
         assert get_talent_alerts in tools

def test_agent_tools_executive():
    """
    Validar que el perfil EJECUTIVO solo recibe monthly_attrition.
    """
    with patch.dict(sys.modules, {"google.adk": MagicMock()}):
         mock_adk = sys.modules["google.adk"]
         mock_adk.Agent = MagicMock()
         
         import importlib
         import app.ai.agents.hr_agent
         importlib.reload(app.ai.agents.hr_agent)
         
         from app.ai.agents.hr_agent import get_hr_agent
         from app.ai.tools.bq_queries.hr_metrics import get_monthly_attrition, get_talent_alerts
         from app.core.constants import ProfileEnum

         profile = ProfileEnum.EJECUTIVO.value
         get_hr_agent(profile)
         
         _, kwargs = mock_adk.Agent.call_args
         tools = kwargs.get("tools")
         
         assert len(tools) == 1
         assert get_monthly_attrition in tools
         assert get_talent_alerts not in tools

