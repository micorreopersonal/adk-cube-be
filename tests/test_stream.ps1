$ErrorActionPreference = "Stop"

Write-Host "🔐 Obteniendo token..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8080/token" -Method Post -Body @{username = "ejecutivo"; password = "123" }
    $token = $response.access_token
    Write-Host "✅ Token obtenido"
}
catch {
    Write-Host "❌ Error obteniendo token: $_"
    exit
}

Write-Host "📡 Enviando POST request (sections=headline)..."
$url = $STREAM_URL

try {
    Write-Host "📡 Conectando al stream..."
    $request = [System.Net.HttpWebRequest]::Create($url)
    $request.Method = "POST"
    $request.Headers.Add("Authorization", "Bearer $token")
    $request.ContentType = "application/json"
    $request.Timeout = 100000 # 100 segundos
    
    # Send empty body (POST requires content-length 0 or body)
    $request.ContentLength = 0
    
    $response = $request.GetResponse()
    $stream = $response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    
    Write-Host "✅ Conectado! Recibiendo eventos en tiempo real..."
    Write-Host "--------------------------------------------------"
    
    while (-not $reader.EndOfStream) {
        $line = $reader.ReadLine()
        
        if ($line.StartsWith("data: ")) {
            $jsonStr = $line.Substring(6)
            try {
                $data = $jsonStr | ConvertFrom-Json
                
                # Format output nicely
                $timestamp = Get-Date -Format "HH:mm:ss"
                
                if ($data.section_id -eq "complete") {
                     Write-Host "[$timestamp] 🎉 GENERACIÓN COMPLETA (100%)" -ForegroundColor Green
                }
                elseif ($data.section_id -eq "error") {
                     Write-Host "[$timestamp] ❌ ERROR: $($data.error)" -ForegroundColor Red
                }
                else {
                    $blockCount = if ($data.blocks) { $data.blocks.Count } else { 0 }
                    Write-Host "[$timestamp] 📦 Sección Recibida: '$($data.section_id)' ($($data.progress)%) - $blockCount bloques" -ForegroundColor Cyan
                    
                    # Optional: Print first block content preview
                    if ($data.blocks -and $data.blocks.Count -gt 0) {
                        $firstBlock = $data.blocks[0]
                        if ($firstBlock.payload) {
                             $preview = $firstBlock.payload.ToString().Substring(0, [math]::Min(50, $firstBlock.payload.ToString().Length))
                             Write-Host "           Example Content: $preview..." -ForegroundColor Gray
                        }
                    }
                }
            }
            catch {
                Write-Host "[$timestamp] raw: $line" -ForegroundColor Gray
            }
        }
    }
    
    $reader.Close()
    $response.Close()
}
catch {
    Write-Host "❌ Error en stream: $_"
    if ($_.Exception.InnerException) {
        Write-Host "   Detalle: $($_.Exception.InnerException.Message)"
    }
}
