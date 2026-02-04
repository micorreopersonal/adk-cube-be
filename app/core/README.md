# Capa Core (`app/core`)

El núcleo de la aplicación. Contiene la lógica transversal, configuración y seguridad.
Ha sido refactorizada para modularidad (Feb 2026).

## Estructura Modular

### 1. Auth (`app/core/auth/`)
Todo lo relacionado con Identidad y Seguridad.
*   `security.py`: Implementa JWT, hashing de contraseñas y **Máscaras de Privacidad** (DNI/Salarios).
*   `mock_users.py`: "Base de datos" volátil para usuarios de prueba (Admin, Ejecutivo).
*   `tools_rbac.py`: Utilidades para control de acceso a herramientas (Role Based Access Control).

### 2. Config (`app/core/config/`)
Configuración del entorno.
*   `config.py`: Carga variables de entorno (`.env`) usando Pydantic `BaseSettings`. Define conexiones a GCP.
*   `constants.py`: Enums y constantes globales (ej. Perfiles de Usuario).

### 3. Utils (`app/core/utils/`)
Herramientas de bajo nivel.
*   `perf_logger.py`: Decoradores y utilidades para medir rendimiento de funciones críticas.

### 4. Analytics (`app/core/analytics/`)
El "Cerebro Semántico" estático.
*   `registry.py`: **Single Source of Truth**. Define qué métricas y dimensiones existen, sus fórmulas y descripciones.
