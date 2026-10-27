@echo off
cd /d "%~dp0"
start "SPMG AI Command Center" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
timeout /t 2 >nul
start "" "http://127.0.0.1:8792"