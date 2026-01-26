/* ESQUEMA TÉCNICO DE LA TABLA BIGQUERY
   Fuente: esquema_bigquery.csv
   Propósito: Definición de tipos de datos y nulabilidad para validación de queries.
*/

TABLE_SCHEMA (
    column_name                     data_type       is_nullable
    -----------------------------------------------------------
    anio                            INT64           YES
    periodo                         DATE            YES
    supervisor                      STRING          YES
    gerente                         STRING          YES
    razon_social                    STRING          YES
    tipo_documento                  STRING          YES
    dni                             STRING          YES
    fecha_nacimiento                DATE            YES
    codigo_persona                  STRING          YES
    nombre_completo_antiguo         STRING          YES
    posicion                        STRING          YES
    segmento                        STRING          YES  -- Campo crítico para filtros ADMI/FFVV/Jerarquía
    mapeo_talento_ultimo_anio       INT64           YES  -- Filtro para Hipers (7) e Hipos (8,9)
    per_anual                       STRING          YES
    ggs                             STRING          YES
    percentil                       STRING          YES
    fecha_ingreso                   DATE            YES
    ts_anios                        FLOAT64         YES
    fecha_corte                     DATE            YES
    ts_dias                         FLOAT64         YES
    rango_permanencia               STRING          YES
    sexo                            STRING          YES
    estado_civil                    STRING          YES
    nacionalidad                    STRING          YES
    estado                          STRING          YES  -- "Activo" vs "Cesado"
    fecha_cese                      DATE            YES
    motivo_cese                     STRING          YES  -- Clave para identificar "Voluntaria"
    tipo_contrato                   STRING          YES
    uo2                             STRING          YES  -- División
    uo3                             STRING          YES  -- Área
    uo4                             STRING          YES  -- Gerencia
    uo5                             STRING          YES  -- Equipos / Canales
    uo6                             STRING          YES  -- Equipos Nivel 2
    departamento                    STRING          YES
    provincia                       STRING          YES
    distrito                        STRING          YES
    rango_anio                      INT64           YES
    anio_ingreso                    INT64           YES
    nombre_completo                 STRING          YES
    nombres                         STRING          YES
    apellido_paterno                STRING          YES
    apellido_materno                STRING          YES
    dni_mes_anio                    STRING          YES
    cod_persona_mes_anio            STRING          YES
    sede_rimac                      STRING          YES
    jerarquia_ffvv                  STRING          YES
    dni_anio_mes_cesado             STRING          YES
    mes_anio_ingreso                INT64           YES
    respuestas                      STRING          YES
    load_timestamp                  TIMESTAMP       NO
);
[cite_start]``` [cite: 1261]