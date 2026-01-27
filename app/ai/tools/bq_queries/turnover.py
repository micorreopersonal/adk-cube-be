import json
from typing import Dict, Any
from app.ai.utils.response_builder import ResponseBuilder

def get_turnover_deep_dive(dimension: str = "uo2", periodo_inicio: str = "2025-01-01", periodo_fin: str = "2025-12-31", tipo_rotacion: str = "GENERAL") -> Dict[str, Any]:
    """
    Realiza un análisis profundo de rotación (Deep Dive) cruzando dimensiones organizacionales.
    Retorna un VisualDataPackage con KPIs, Gráficos e Insight Ejecutivo.
    """
    # Inicializar builder al principio para capturar debugs o errores tempranos
    builder = ResponseBuilder()

    # Simulación de Lógica de Negocio (Mock Data based on Ground Truth Docs)
    # En producción, esto sería una query compleja a BigQuery
    from app.ai.tools.bq_queries.financial_parameters import (
        AVG_ANNUAL_SALARY_USD, RECRUITMENT_COST_PCT, TRAINING_COST_USD,
        RAMP_UP_MONTHS, RAMP_UP_PRODUCTIVITY_FACTOR, SEVERANCE_AVG_USD
    )
    
    # 1. Datos Simulados (Mock)
    current_rate = "45.06%" # Del caso de uso Transformación
    avg_company = "37.21%"
    total_leavers = 676
    
    # --- CÁLCULO DE IMPACTO FINANCIERO DINÁMICO (Hybrid BQ + Config) ---
    
    # Intentar cargar parámetros desde BigQuery (Producción)
    params = {}
    try:
        from app.services.bigquery import get_bq_service
        bq = get_bq_service()
        # TODO: Mover el ID del proyecto/dataset a variables de entorno si cambia
        query = "SELECT param_key, param_value FROM `adk-team-fitness.data_set_historico_ceses.config_financial_params`"
        df_params = bq.execute_query(query)
        
        # Convertir a diccionario
        if not df_params.empty:
            params = dict(zip(df_params['param_key'], df_params['param_value']))
            # Debug SQL en el response builder si es necesario
            builder.add_debug_sql(query)
            
    except Exception as e:
        print(f"[WARN] Falló carga de parámetros financieros BQ: {e}. Usando fallback local.")
    
    # Obtener valores con fallback a constantes locales (File Config)
    salary_usd = params.get('AVG_ANNUAL_SALARY_USD', AVG_ANNUAL_SALARY_USD)
    rec_cost_pct = params.get('RECRUITMENT_COST_PCT', RECRUITMENT_COST_PCT)
    training_cost = params.get('TRAINING_COST_USD', TRAINING_COST_USD)
    ramp_months = params.get('RAMP_UP_MONTHS', RAMP_UP_MONTHS)
    ramp_factor = params.get('RAMP_UP_PRODUCTIVITY_FACTOR', RAMP_UP_PRODUCTIVITY_FACTOR)
    severance = params.get('SEVERANCE_AVG_USD', SEVERANCE_AVG_USD)

    # Costo Reemplazo
    cost_replacement = salary_usd * rec_cost_pct
    
    # Costo Productividad
    monthly_salary = salary_usd / 12
    cost_productivity = monthly_salary * ramp_months * (1 - ramp_factor)
    
    # Costo Unitario por Salida
    cost_per_leaver = cost_replacement + training_cost + cost_productivity + severance
    
    # Impacto Total (Ejemplo con 676 leavers)
    total_impact_usd = cost_per_leaver * total_leavers
    
    # Formatear a millones (ej: $1.2M)
    impact_formatted = f"${total_impact_usd / 1_000_000:.1f}M"
    
    # 2. Generación de Insight Ejecutivo
    insight_text = (
        f"Se observa un incremento crítico en la rotación de la división {dimension} ({current_rate}), "
        f"superando el promedio general ({avg_company}). "
        f"Con {total_leavers} salidas, estimamos un **impacto financiero anual de {impact_formatted}**, "
        f"basado en parámetros actualizados de negocio (Salario Base: ${salary_usd:,.0f})."
    )
    
    severity = "critical" if float(current_rate.replace("%", "")) > 30 else "warning"

    # Bloque 1: Insight Ejecutivo
    builder.add_insight_alert(insight_text, severity=severity)
    
    # Bloque 2: KPIs
    builder.add_kpi_row([
        {"label": "Rotación 2025", "value": current_rate, "delta": "+15% vs 2024", "color": "inverse"},
        {"label": "Ceses Voluntarios", "value": str(total_leavers), "delta": "Renuncias", "color": "normal"},
        {"label": "Costo de Rotación", "value": impact_formatted, "delta": "B.Q. Live", "color": "inverse"}
    ])
    
    # Bloque 3: Gráfico de Tendencia
    # Bloque 3: Visualización Interactiva
    months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    gen_rate = [2.1, 2.5, 3.0, 5.2, 4.8, 3.5, 4.0, 4.2, 3.8, 3.9, 3.5, 4.5]
    vol_rate = [1.8, 2.0, 2.5, 4.5, 4.0, 3.0, 3.5, 3.8, 3.2, 3.5, 3.0, 4.0] # Mock data voluntaria
    
    data_series = {
        "months": months,
        "rotacion_general": gen_rate,
        "rotacion_voluntaria": vol_rate,
        # Mocking extra data for the table view
        "headcount": [1500] * 12,
        "ceses": [int(x*15) for x in gen_rate],
        "renuncias": [int(x*15) for x in vol_rate]
    }
    
    builder.add_data_series(data_series, metadata={"year": "2025", "segment": dimension})
    
    return builder.to_dict()
