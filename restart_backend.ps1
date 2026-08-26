# OptionsLab Windows Native Backend Clean Restart & Port Guardian
# Terminate lingering background python processes on port 8000, purge stale pycache, and launch fresh hot-reloading uvicorn.

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   OptionsLab Windows Native Backend Clean Restart" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$Port = 8000
$AppDir = $PSScriptRoot

# 1. Kill any existing process on port 8000
Write-Host "[1/3] Checking for active processes on port $Port..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($connections) {
    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
    foreach ($procId in $pids) {
        try {
            Write-Host "  -> Terminating orphan process PID $procId on port $Port..." -ForegroundColor Red
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "  -> Could not kill PID $procId: $_" -ForegroundColor DarkGray
        }
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host "  -> Port $Port is clean." -ForegroundColor Green
}

# 2. Clean stale __pycache__ bytecode files
Write-Host "[2/3] Purging stale Python bytecode cache..." -ForegroundColor Yellow
Get-ChildItem -Path "$AppDir\options_lab" -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  -> Bytecode cache cleared." -ForegroundColor Green

# 3. Launch hot-reloading uvicorn
Write-Host "[3/3] Starting fresh hot-reloading FastAPI backend on http://127.0.0.1:$Port..." -ForegroundColor Yellow
$PythonExe = "$AppDir\venv_win\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Write-Host "  -> Executing: $PythonExe -m uvicorn options_lab.api.main:app --host 127.0.0.1 --port $Port --reload --reload-dir options_lab" -ForegroundColor Cyan
& $PythonExe -m uvicorn options_lab.api.main:app --host 127.0.0.1 --port $Port --reload --reload-dir "$AppDir\options_lab"
