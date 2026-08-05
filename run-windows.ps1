# Spusti aplikaci na Windows z venv (vyvojovy rezim).
#   .\run-windows.ps1
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\pythonw.exe"

if (-not (Test-Path $python)) {
    Write-Host "Zakladam venv a instaluji PySide6..."
    py -3 -m venv (Join-Path $root ".venv")
    & (Join-Path $root ".venv\Scripts\python.exe") -m pip install --upgrade pip
    & (Join-Path $root ".venv\Scripts\python.exe") -m pip install PySide6
}

$env:PYTHONPATH = Join-Path $root "src"
Start-Process -FilePath $python -ArgumentList "-m", "stickynotes.main" -WorkingDirectory $root
