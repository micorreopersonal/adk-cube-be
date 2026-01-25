import pytest
import sys
from unittest.mock import MagicMock

# Como Agent importa de google.adk, y google.adk no está en el entorno local de test puro 
# (o podría requerir credenciales), vamos a mockear la clase Agent ANTES de importar hr_agent.
sys.modules["google.adk"] = MagicMock()
sys.modules["google.adk"].Agent = MagicMock()

# Ahora podemos importar de forma segura
from app.agents.hr_agent import get_hr_agent
from app.tools.bq_queries.hr_metrics import get_monthly_attrition, get_talent_alerts
from app.core.constants import ProfileEnum

def test_agent_tools_admin():
    """
    Validar que el perfil ADMIN recibe todas las herramientas.
    """
    profile = ProfileEnum.ADMIN.value
    agent_mock = get_hr_agent(profile)
    
    # Inspeccionar con qué argumentos se llamó al constructor de Agent
    # get_hr_agent llama a Agent(...)
    # sys.modules["google.adk"].Agent es el mock
    
    call_args = sys.modules["google.adk"].Agent.call_args
    assert call_args is not None
    
    # args, kwargs
    _, kwargs = call_args
    tools = kwargs.get("tools")
    
    # Validar que están ambas herramientas
    assert len(tools) == 2
    assert get_monthly_attrition in tools
    assert get_talent_alerts in tools

def test_agent_tools_executive():
    """
    Validar que el perfil EJECUTIVO solo recibe monthly_attrition.
    """
    profile = ProfileEnum.EJECUTIVO.value
    get_hr_agent(profile)
    
    _, kwargs = sys.modules["google.adk"].Agent.call_args
    tools = kwargs.get("tools")
    
    assert len(tools) == 1
    assert get_monthly_attrition in tools
    assert get_talent_alerts not in tools
