from typing import Callable, List, Dict
from app.api.routes import get_current_user 
from app.ai.tools.universal_analyst import get_analytical_data

# Mapa de Roles -> Herramientas
TOOL_ACCESS_CONFIG: Dict[str, List[Callable]] = {
    # El Ejecutivo tiene acceso completo a la herramienta universal
    "EJECUTIVO": [get_analytical_data],
    
    # El Admin también, más herramientas de sistema si las hubiera
    "ADMIN": [get_analytical_data],
    
    # Perfil Restricted (ej. Solo métricas básicas) - Por ahora igual
    "RESTRICTED": [get_analytical_data]
}

def get_allowed_tools(profile: str) -> List[Callable]:
    """
    Retorna la lista de herramientas permitidas para un perfil dado.
    Si el perfil no existe, retorna un set mínimo seguro.
    """
    # Default seguro: solo métricas básicas
    default_tools = [get_analytical_data] 
    return TOOL_ACCESS_CONFIG.get(profile, default_tools)
