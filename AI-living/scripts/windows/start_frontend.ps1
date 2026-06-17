$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
npm run dev -- --host 127.0.0.1 --port 3000
