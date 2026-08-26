@echo off
setlocal enabledelayedexpansion
title OptionsLab Trading Desktop Gateway

cd /d "%~dp0"

echo =======================================================
echo    OptionsLab Autonomous Trading Desktop Gateway
echo =======================================================

set ELECTRON_EXE="%~dp0node_modules\electron\dist\electron.exe"

if not exist %ELECTRON_EXE% (
    echo [OptionsLab] Initializing Desktop App runtime...
    call npm.cmd install
)

echo [OptionsLab] Ensuring port 8000 is clean...
powershell -NoProfile -Command "$c = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; if ($c) { $pids = $c | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }; foreach ($p in $pids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue } }"

echo [OptionsLab] Launching native Desktop window...
if exist %ELECTRON_EXE% (
    start "" %ELECTRON_EXE% "%~dp0." %*
) else (
    call npx.cmd electron . %*
)

exit /b 0
