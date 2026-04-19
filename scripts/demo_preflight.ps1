$ErrorActionPreference = 'Stop'

Write-Host '=== Demo Preflight ==='
Write-Host ''

Write-Host '[1/3] Docker services status'
docker compose ps
Write-Host ''

Write-Host '[2/3] Endpoint smoke checks'
python scripts/check_endpoints.py
Write-Host ''

Write-Host '[3/3] Ready message'
Write-Host 'Preflight complete. If all checks passed, start recording now.'
