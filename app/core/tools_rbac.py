from typing import List, Callable
from app.core.constants import ProfileEnum
from app.tools.bq_queries.hr_metrics import (
    get_monthly_attrition, 
    get_talent_alerts
)

# Configuración centralizada de Roles y Herramientas (RBAC)
TOOL_ACCESS_CONFIG = {
    ProfileEnum.ADMIN.value: [get_monthly_attrition, get_talent_alerts],
    ProfileEnum.ANALISTA.value: [get_monthly_attrition, get_talent_alerts],
    ProfileEnum.GERENTE.value: [get_monthly_attrition, get_talent_alerts], # Gerente ve todo por ahora
    ProfileEnum.EJECUTIVO.value: [get_monthly_attrition], # Ejecutivo solo ve métricas agregadas
}

def get_allowed_tools(profile: str) -> List[Callable]:
    """
    Retorna la lista de herramientas permitidas para un perfil dado.
    Si el perfil no existe, retorna un set mínimo seguro.
    """
    # Default seguro: solo métricas básicas
    default_tools = [get_monthly_attrition]
    return TOOL_ACCESS_CONFIG.get(profile, default_tools)
