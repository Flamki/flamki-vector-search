param(
    [string]$Output = "recordings/final_demo_$(Get-Date -Format 'yyyyMMdd_HHmmss').mp4",
    [string]$AudioDevice = "Microphone Array (AMD Audio Device)"
)

$ErrorActionPreference = 'Stop'

Write-Host 'Ensuring stack is up...'
docker compose up -d | Out-Null

Write-Host 'Running preflight checks...'
python scripts/check_endpoints.py

Write-Host 'Opening demo pages...'
Start-Process 'http://localhost:5173'
Start-Process 'http://localhost:8000/api/index/status'

Write-Host 'Starting recording in 5 seconds. Prepare your narration.'
Start-Sleep -Seconds 5

powershell -ExecutionPolicy Bypass -File scripts/record_demo_main_screen.ps1 -Output $Output -DurationSec 240 -AudioDevice $AudioDevice

Write-Host "Final demo recording saved at: $Output"
