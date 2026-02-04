from enum import Enum

class ProfileEnum(str, Enum):
    EJECUTIVO = "EJECUTIVO"
    ANALISTA = "ANALISTA"
    GERENTE = "GERENTE"
    ADMIN = "ADMIN"
