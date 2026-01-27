# Parámetros de Costo de Rotación
# Estas constantes se utilizan para estimar el impacto financiero de la rotación de empleados.

# 1. Compensación Base
AVG_ANNUAL_SALARY_USD = 30000.0  # Promedio de salario bruto anual

# 2. Costos de Reclutamiento (Directos e Indirectos)
# incluye honorarios de agencias, publicidad, tiempo de reclutadores, tiempo de entrevistas
RECRUITMENT_COST_PCT = 0.20  # 20% del salario anual

# 3. Costos de Capacitación y Onboarding
# incluye materiales, tiempo del entrenador, cursos
TRAINING_COST_USD = 1500.0  # Costo fijo por nueva contratación

# 4. Pérdida de Productividad
# Tiempo (en meses) hasta que una nueva contratación es totalmente productiva
RAMP_UP_MONTHS = 3
# Productividad promedio durante el período de adaptación (ej. 50% productivo)
RAMP_UP_PRODUCTIVITY_FACTOR = 0.5 

# 5. Costos de Desvinculación
# incluye indemnizaciones, honorarios legales, tiempo administrativo
SEVERANCE_AVG_USD = 2000.0
