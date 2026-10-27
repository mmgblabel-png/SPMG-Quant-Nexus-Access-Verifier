$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
Write-Host 'SPMG AI Command Center — lokale chat + Game Maker-agent' -ForegroundColor Cyan
# No auto-replacement of running files. Update occurs before the server starts.
if (-not $env:SPMG_SKIP_UPDATE -and (Test-Path (Join-Path $here 'update.ps1'))) {
    try { & (Join-Path $here 'update.ps1') -Quiet } catch { Write-Warning "Updatecontrole niet beschikbaar: $_" }
}
py -3 (Join-Path $here 'app.py')
if ($LASTEXITCODE -ne 0) { Write-Warning "Command Center stopte met code $LASTEXITCODE" }