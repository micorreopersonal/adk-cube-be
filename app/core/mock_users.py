from app.core.constants import ProfileEnum
from app.core.config import get_settings

settings = get_settings()

# Diccionario de usuarios simulados para desarrollo/pruebas.
# En un entorno productivo real, esto se reemplazaría por una tabla 'users' en base de datos.
# Estructura: username -> {password, profile}

MOCK_USERS = {
    "admin": {
        "password": settings.SECRET_KEY, # Mantenemos compatibilidad actual
        "profile": ProfileEnum.ADMIN.value
    },
    "ejecutivo": {
        "password": "123", # Password simple para demo
        "profile": ProfileEnum.EJECUTIVO.value
    },
    "analista": {
        "password": "123",
        "profile": ProfileEnum.ANALISTA.value
    },
    "gerente": {
       "password": "123",
       "profile": ProfileEnum.GERENTE.value
    }
}

def get_user(username: str):
    return MOCK_USERS.get(username)
