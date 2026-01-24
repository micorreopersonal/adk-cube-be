import re

def mask_rut(rut: str) -> str:
    """
    Anonimiza un RUT chileno (ej: 12.345.678-9 -> 12.XXX.XXX-X)
    """
    if not rut:
        return rut
    
    # Separar cuerpo y dígito verificador si es posible
    parts = re.split(r'[-]', rut)
    body = parts[0]
    
    if len(body) > 4:
        masked_body = body[:2] + "." + "X" * 3 + "." + "X" * 3
        if len(parts) > 1:
            return f"{masked_body}-X"
        return masked_body
    return "X.XXX.XXX-X"

def mask_salary(salary: float) -> str:
    """
    Anonimiza un salario convirtiéndolo en un rango o simplemente enmascarándolo.
    Según GLOBAL_RULES, los salarios deben ser anonimizados en los logs.
    """
    return "[SALARIO_CONFIDENCIAL]"

def clean_sensitive_data(text: str) -> str:
    """
    Busca patrones de RUT en un texto y los enmascara.
    """
    # Regex simple para RUT
    rut_pattern = r'\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]'
    return re.sub(rut_pattern, "XX.XXX.XXX-X", text)
