# AI-living Windows Setup

This package is prepared for continuing development and live-stream testing on Windows.

## 1. Install prerequisites

- Windows 11 64-bit
- Python 3.10 or 3.11
- Node.js 18 LTS or newer
- Git for Windows
- FFmpeg, added to `PATH`
- OBS Studio and Douyin Live Companion, when testing live output

## 2. Prepare the project

Open PowerShell in the unzipped project directory:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\windows\setup_windows.ps1
copy backend\.env.example backend\.env
```

Edit `backend\.env` and fill in real API keys or streaming configuration on the Windows machine.

## 3. Test camera capture

```powershell
.\.venv\Scripts\python.exe backend\scripts\diagnose_camera_windows.py
```

If camera access fails, check Windows Settings:

`Settings > Privacy & security > Camera`

Enable camera access for desktop apps.

## 4. Start local services

Open three PowerShell windows:

```powershell
.\scripts\windows\start_backend.ps1
```

```powershell
.\scripts\windows\start_frontend.ps1
```

```powershell
.\scripts\windows\start_rtmp.ps1
```

Then open:

```text
http://127.0.0.1:3000
```

## 5. Live validation path

1. Confirm camera preview works in the web UI.
2. Apply the snack room background and snack overlay pack.
3. Start the local RTMP server.
4. Push the composed stream to local RTMP first.
5. Use OBS or Douyin Live Companion to verify video and audio.
6. After local validation, switch the RTMP target to Douyin test stream settings.

## Notes

- Real `.env` files are intentionally excluded from the migration package.
- `node_modules` and `dist` are intentionally excluded and should be recreated on Windows.
- Use `backend\requirements-win.txt` on Windows to avoid macOS-only dependency issues.
