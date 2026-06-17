$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
py -3.10 -m venv .venv

Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r backend\requirements-win.txt

Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
npm install

Write-Host "Done. Copy backend\.env.example to backend\.env and fill API keys if needed." -ForegroundColor Green
