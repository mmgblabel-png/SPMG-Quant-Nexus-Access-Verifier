@echo off
setlocal
cd /d "%~dp0"
start "SPMG AI Command Center" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
rem Wait for the local server instead of opening Edge after an arbitrary 2 seconds.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "for ($i=0; $i -lt 90; $i++) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8792/' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch { }; Start-Sleep -Seconds 1 }; exit 1"
if errorlevel 1 (
  echo SPMG start niet. Controleer het PowerShell-venster met de foutmelding.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8792"
exit /b 0
