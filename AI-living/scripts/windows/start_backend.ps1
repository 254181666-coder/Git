$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

if (!(Test-Path ".\.venv\Scripts\python.exe")) {
  Write-Host "Missing .venv. Run scripts\windows\setup_windows.ps1 first." -ForegroundColor Red
  exit 1
}

Set-Location ".\backend"
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
