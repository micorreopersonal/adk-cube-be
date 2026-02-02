# ==========================================
# BOOTSTRAP SCRIPT FOR ADK-SANDBOX (GCP)
# ==========================================
# Este script inicializa un proyecto GCP vacío para el backend de People Analytics.
# Requisitos: Tener Google Cloud SDK instalado y autenticado (gcloud auth login).

$PROJECT_ID = "adk-sandbox-486117"
$REGION = "us-central1"
$SA_NAME = "adk-agent-runner"
$SA_EMAIL = "$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
$BQ_DATASET = "data_set_historico_ceses"
$BUCKET_DOCS = "adk-sandbox-hr-docs"
$BUCKET_LANDING = "adk-sandbox-landing"

Write-Host "🚀 Iniciando Bootstrap para $PROJECT_ID..." -ForegroundColor Cyan

# 1. Configurar Proyecto
Write-Host "`n[1/6] Configurando proyecto activo..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID
if ($LASTEXITCODE -ne 0) { Write-Error "No se pudo acceder al proyecto $PROJECT_ID."; exit 1 }

# 2. Habilitar APIs
Write-Host "`n[2/6] Habilitando APIs (esto puede tardar unos minutos)..." -ForegroundColor Yellow
$APIS = @(
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "bigquery.googleapis.com",
    "aiplatform.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "iamcredentials.googleapis.com"
)
# gcloud services enable $APIS
if ($LASTEXITCODE -ne 0) { Write-Error "Fallo al habilitar APIs."; exit 1 }

# 3. Firestore (Intentar crear solo si no existe)
Write-Host "`n[3/6] Inicializando Firestore (Native)..." -ForegroundColor Yellow
# Nota: La creación de App Engine/Firestore a veces falla si ya existe. Lo intentamos y continuamos.
gcloud firestore databases create --location=$REGION --type=firestore-native 2>$null
if ($LASTEXITCODE -eq 0) { 
    Write-Host "✅ Firestore creado exitosamente." -ForegroundColor Green 
}
else {
    Write-Host "⚠️ Firestore ya existe o requiere intervención manual (verificar en consola)." -ForegroundColor Yellow
}

# 4. IAM - Service Account
Write-Host "`n[4/6] Configurando Service Account ($SA_NAME)..." -ForegroundColor Yellow
# Crear SA si no existe
gcloud iam service-accounts create $SA_NAME --display-name="ADK Agent Runner" 2>$null

# Asignar Roles
$ROLES = @(
    "roles/aiplatform.user",
    "roles/bigquery.jobUser",
    "roles/bigquery.dataViewer",
    "roles/storage.objectAdmin",
    "roles/datastore.user",
    "roles/iam.serviceAccountUser", # Para que Cloud Run pueda actuar como esta SA
    "roles/run.invoker" # Para invocar el servicio
)

foreach ($role in $ROLES) {
    Write-Host "   -> Asignando $role..."
    gcloud projects add-iam-policy-binding $PROJECT_ID `
        --member="serviceAccount:$SA_EMAIL" `
        --role=$role > $null
}

# 5. BigQuery Dataset
Write-Host "`n[5/6] Creando Dataset BigQuery..." -ForegroundColor Yellow
bq --location=US mk --dataset "${PROJECT_ID}:${BQ_DATASET}" 2>$null
if ($LASTEXITCODE -eq 0) { Write-Host "✅ Dataset creado." -ForegroundColor Green }
else { Write-Host "⚠️ Dataset ya existe." -ForegroundColor Yellow }

# 6. Cloud Storage Buckets
Write-Host "`n[6/6] Creando Buckets de Storage..." -ForegroundColor Yellow
gsutil mb -l $REGION -p $PROJECT_ID "gs://$BUCKET_DOCS" 2>$null
gsutil mb -l $REGION -p $PROJECT_ID "gs://$BUCKET_LANDING" 2>$null

# Resumen
Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "✅ BOOTSTRAP COMPLETADO EXITOSAMENTE" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Recursos creados:"
Write-Host "- Proyecto: $PROJECT_ID"
Write-Host "- Service Account: $SA_EMAIL"
Write-Host "- Dataset: $BQ_DATASET"
Write-Host "- Buckets: gs://$BUCKET_DOCS, gs://$BUCKET_LANDING"
Write-Host "`n⚠️ Siguiente Paso: Ejecuta la migración de datos."
