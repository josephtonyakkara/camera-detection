# One-time machine setup for Windows: venv + pinned deps.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

& $python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python >= 3.11 required. Set `$env:PYTHON to a newer interpreter and re-run."
}

if (-not (Test-Path .venv)) {
    & $python -m venv .venv
}

.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.lock

New-Item -ItemType Directory -Force -Path config\local, logs | Out-Null

.venv\Scripts\python.exe -c "import cv2, numpy, fastapi, asyncua, yaml"

Write-Host ""
Write-Host "Setup complete."
Write-Host "  Run:          .venv\Scripts\python.exe main.py"
Write-Host "  Tests:        .venv\Scripts\python.exe -m pytest -m `"not hardware`""
Write-Host "  Camera probe: .venv\Scripts\python.exe scripts\camera_check.py --list"
Write-Host ""
Write-Host "Per-machine settings go in config\local\<name>.yaml (gitignored);"
Write-Host "see docs_camera\DEPLOYMENT.md."
