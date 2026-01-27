from typing import List, Callable
from app.core.constants import ProfileEnum
from app.ai.tools.bq_queries.hr_metrics import (
    get_monthly_attrition, 
    get_talent_alerts,
    get_yearly_attrition,
    get_monthly_trend
)
from app.ai.tools.bq_queries.turnover import get_turnover_deep_dive
from app.ai.tools.bq_queries.leavers import get_leavers_list
from app.ai.tools.report_generator import generate_executive_report

# Configuración centralizada de Roles y Herramientas (RBAC)
TOOL_ACCESS_CONFIG = {
    ProfileEnum.ADMIN.value: [get_monthly_attrition, get_yearly_attrition, get_monthly_trend, get_talent_alerts, get_turnover_deep_dive, get_leavers_list, generate_executive_report],
    ProfileEnum.ANALISTA.value: [get_monthly_attrition, get_yearly_attrition, get_monthly_trend, get_talent_alerts, get_turnover_deep_dive, get_leavers_list, generate_executive_report],
    ProfileEnum.GERENTE.value: [get_monthly_attrition, get_yearly_attrition, get_monthly_trend, get_talent_alerts, get_turnover_deep_dive, get_leavers_list, generate_executive_report], 
    ProfileEnum.EJECUTIVO.value: [get_monthly_attrition, get_yearly_attrition, get_monthly_trend, get_turnover_deep_dive, generate_executive_report], 
}

def get_allowed_tools(profile: str) -> List[Callable]:
    """
    Retorna la lista de herramientas permitidas para un perfil dado.
    Si el perfil no existe, retorna un set mínimo seguro.
    """
    # Default seguro: solo métricas básicas
    default_tools = [get_monthly_attrition]
    return TOOL_ACCESS_CONFIG.get(profile, default_tools)
