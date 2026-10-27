$ErrorActionPreference = 'Stop'
$target = Join-Path $HOME 'Documents\SPMG-Sandbox\AI-Agent-Work\SPMG-Command-Center'
$base = 'https://raw.githubusercontent.com/mmgblabel-png/SPMG-Quant-Nexus-Access-Verifier/main/command-center'
New-Item -ItemType Directory -Path $target -Force | Out-Null
Write-Host "Installatielocatie: $target" -ForegroundColor Cyan
$updater = Join-Path $target 'update.ps1'
Invoke-WebRequest -Uri "$base/update.ps1" -UseBasicParsing -OutFile $updater -TimeoutSec 30
& $updater -Apply
if (-not (Test-Path (Join-Path $target 'app.py'))) { throw 'Installatie onvolledig: app.py ontbreekt' }
Write-Host 'SPMG AI Command Center is geinstalleerd.' -ForegroundColor Green
Write-Host 'Gebruik voortaan START-SPMG.cmd of de chatopdracht: update jezelf.'
Start-Process (Join-Path $target 'START-SPMG.cmd')