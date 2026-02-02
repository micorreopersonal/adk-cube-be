# Script de Despliegue Automatizado para Windows (PowerShell)

# 1. Configuración de Variables
$PROJECT_ID = "adk-sandbox-486117"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/adk-people-analytics-backend:latest"
$REGION = "us-central1"
$SERVICE_NAME = "adk-people-analytics-backend"

Write-Host "🚀 Iniciando proceso de despliegue para $SERVICE_NAME..." -ForegroundColor Cyan

# 2. Construir Imagen (Cloud Build)
# Necesario porque cambiaste requirements.txt
Write-Host "`n📦 Construyendo imagen de contenedor (esto puede tardar unos minutos)..." -ForegroundColor Yellow
gcloud builds submit --tag $IMAGE_NAME --project $PROJECT_ID .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error en Cloud Build. Abortando." -ForegroundColor Red
    exit 1
}

# 3. Desplegar en Cloud Run
# Usamos el archivo cloud_run_env.yaml y configuración de memoria de 2Gi
Write-Host "`n🚀 Desplegando en Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_NAME `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --memory 2Gi `
    --timeout 300 `
    --env-vars-file cloud_run_env.yaml `
    --service-account "adk-agent-runner@$PROJECT_ID.iam.gserviceaccount.com" `
    --project $PROJECT_ID

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ ¡Despliegue Exitoso!" -ForegroundColor Green
}
else {
    Write-Host "`n❌ Error en el despliegue." -ForegroundColor Red
}
