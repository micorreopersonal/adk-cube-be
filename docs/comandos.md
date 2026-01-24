# 🚀 Comandos Operativos - ADK People Analytics

Guía rápida de comandos para desarrollo local y operación del backend.

## 1. Configuración de Entorno

### Activar Virtual Environment
**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### Variables de Entorno (Opcional)
El proyecto usa `.env` por defecto, pero puedes forzar variables en la terminal:

```powershell
# Modo Test (Habilita Bypass Seguridad)
$env:APP_ENV="test"; $env:LOG_LEVEL="DEBUG"
```

---

## 2. Ejecutar Servidor (Local)

El servidor utiliza **Uvicorn** con hot-reload para desarrollo.

```powershell
uvicorn app.main:app --reload --port 8080
```
*   **Acceso API:** [http://localhost:8080](http://localhost:8080)
*   **Documentación Interactiva (Swagger):** [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 3. Pruebas de Seguridad (Auth Bypass)

Dado que se ha implementado la validación JWT, usa el token maestro en modo local:

**Token de Desarrollo:** `dev-token-mock`

### Ejemplo con cURL
```bash
curl -X POST "http://localhost:8080/chat" \
     -H "Authorization: Bearer dev-token-mock" \
     -H "Content-Type: application/json" \
     -d '{
           "message": "Hola, ¿cuál fue la rotación de FFVV en Enero?"
         }'
```

---

---

## 4. Testing y QA 🧪

### A. Pruebas Unitarias (Regresión)
Validan la lógica interna sin necesidad de conexión externa (mocks). Deben pasar siempre antes de subir cambios.
```bash
python -m pytest tests/unit
```

### B. Pruebas Funcionales (End-to-End)
Validan el flujo completo contra el servidor local. Requieren que `uvicorn` esté corriendo en el puerto 8000.

**Validar Chat y Herramientas (Casos A, B, C):**
```bash
python tests/functional/test_chat_flow.py
```

**Validar Boletín Mensual (Caso D):**
```bash
python tests/functional/test_full_report.py
```

---

## 5. Gestión de Dependencias

Si agregas nuevas librerías:

```powershell
# Instalar desde requirements
pip install -r requirements.txt

# Guardar nuevas dependencias
pip freeze > requirements.txt
```

## 5. Docker (Build & Run)

Para simular el entorno de Cloud Run:

```bash
docker build -t adk-backend .
docker run -p 8080:8080 --env-file .env adk-backend
```
