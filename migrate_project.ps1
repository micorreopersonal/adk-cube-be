
# Script de Migración Fuera de OneDrive
# Mueve el proyecto actual a C:\adk-projects preservando Git pero limpiando temporales.

$Source = Get-Location
$Dest = "C:\adk-projects\adk-people-analytics-backend"

Write-Host "🏗️ Iniciando migración..." -ForegroundColor Cyan
Write-Host "Origen: $Source"
Write-Host "Destino: $Dest"

# 1. Copia Robusta (Excluyendo venv y caché)
# /E :: Copia subdirectorios, incluidos los vacíos.
# /XD :: Excluye los directorios especificados.
# /XF :: Excluye archivos especificados.
robocopy $Source $Dest /E /XD ".venv" "__pycache__" ".idea" ".vscode" "node_modules" /XF "*.pyc" "*.log"

Write-Host "`n✅ Archivos migrados exitosamente." -ForegroundColor Green

# 2. Instrucciones Post-Migración
$Instruction = @"

=======================================================
🚀 MIGRACIÓN COMPLETADA
=======================================================
Tu proyecto ha sido movido a: $Dest

PASOS SIGUIENTES:
1. Cierra tu editor actual (VS Code / Cursor).
2. Abre la nueva carpeta: C:\adk-projects\adk-people-analytics-backend
3. Abre una terminal en esa nueva ubicación y ejecuta:
   python -m venv .venv
   .\.venv\Scripts\Activate
   pip install -r requirements.txt

NOTA: La carpeta original en OneDrive NO ha sido eliminada por seguridad.
Puedes borrarla manualmente una vez verifiques que todo funciona en la nueva ruta.
=======================================================
"@

Write-Host $Instruction -ForegroundColor Yellow
Start-Process "explorer.exe" $Dest
