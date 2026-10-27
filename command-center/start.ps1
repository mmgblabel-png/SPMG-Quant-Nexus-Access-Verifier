$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
Write-Host 'SPMG AI Command Center - lokale chat + Game Maker-agent' -ForegroundColor Cyan

# Update only at startup. Changes are checked against SHA-256 manifest.
if (-not $env:SPMG_SKIP_UPDATE -and (Test-Path (Join-Path $here 'update.ps1'))) {
    try { & (Join-Path $here 'update.ps1') -Quiet }
    catch { Write-Warning "Updatecontrole niet beschikbaar: $_" }
}

# The PowerShell launcher remains alive and restarts Python on a deliberate
# exit code 23, without losing the local chat service permanently.
$env:SPMG_SUPERVISOR = '1'
while ($true) {
    py -3 (Join-Path $here 'app.py')
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 23) {
        Write-Host 'SPMG update uitgevoerd. Lokale chat opnieuw starten...' -ForegroundColor Cyan
        Start-Sleep -Seconds 2
        continue
    }
    if ($exitCode -ne 0) {
        Write-Warning "Command Center stopte met code $exitCode. Controleer PowerShell op fouten."
    }
    break
}
