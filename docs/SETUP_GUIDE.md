# Guía de Levantamiento (Setup Guide)

## Requisitos
- Python 3.11+
- Google Cloud SDK
- Docker

## Instalación Local
1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Configurar `.env` usando `.env.example`.
3. Ejecutar servidor:
   ```bash
   uvicorn app.main:app --reload
   ```

## Despliegue (SOTA Flow)
Utilizar el script automatizado:
```powershell
.\deploy.ps1
```
Este script se encarga de:
1. Construir la imagen en Cloud Build.
2. Desplegar en Cloud Run con la configuración de memoria y variables correcta.
