param(
    [int]$TotalSec = 245
)

$ErrorActionPreference = 'SilentlyContinue'

Write-Host '=== Flamki Vector Search Auto Demo Sequence ==='
Write-Host 'Starting browser walkthrough...'

Start-Sleep -Seconds 2
Start-Process 'http://localhost:5173'
Write-Host '[Scene] Opened PWA home'

Start-Sleep -Seconds 18
Start-Process 'http://localhost:8000/api/index/status'
Write-Host '[Scene] Opened index status with vector counts'

Start-Sleep -Seconds 18
Write-Host '[Scene] Health check'
curl.exe -s http://localhost:8000/health

Start-Sleep -Seconds 12
Write-Host '[Scene] Text search demo: hackathon battle plan'
curl.exe -s "http://localhost:8000/api/search?q=hackathon%20battle%20plan&top_k=5"

Start-Sleep -Seconds 18
Write-Host '[Scene] Filtered photo-oriented query'
curl.exe -s "http://localhost:8000/api/search?q=photo%20of%20person&top_k=5"

Start-Sleep -Seconds 16
Write-Host '[Scene] Image-to-image endpoint demo'
$img=(Get-ChildItem -Path demo_data/photos -File | Select-Object -First 1).FullName
curl.exe -s -X POST "http://localhost:8000/api/search/image?top_k=5" -F "file=@$img"

Start-Sleep -Seconds 18
Write-Host '[Scene] Audio transcript search demo'
curl.exe -s "http://localhost:8000/api/search?q=be%20decent%20in%20my%20eyes&file_type=mp3&top_k=5"

Start-Sleep -Seconds 15
Write-Host '[Scene] Open API docs page'
Start-Process 'http://localhost:8000/docs'

Start-Sleep -Seconds 15
Write-Host '[Scene] Open repository (public proof)'
Start-Process 'https://github.com/Flamki/flamki-vector-search'

$remaining = [Math]::Max(0, $TotalSec - 132)
if ($remaining -gt 0) {
    Write-Host "[Scene] Holding final screen for ${remaining}s"
    Start-Sleep -Seconds $remaining
}

Write-Host '=== Auto demo sequence complete ==='
