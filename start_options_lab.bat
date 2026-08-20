@echo off
setlocal enabledelayedexpansion
title OptionsLab Autonomous Trading Gateway

echo ===================================================================
echo     OptionsLab Autonomous Socratic Trading Gateway & Simulator
echo ===================================================================
echo.

set DESKTOP_DIR=%~dp0options_lab\desktop

if exist "%DESKTOP_DIR%\start_desktop.bat" (
    echo [OptionsLab] Launching Desktop Trading Gateway...
    call "%DESKTOP_DIR%\start_desktop.bat" %*
) else (
    echo [Error] Desktop launcher not found at %DESKTOP_DIR%
    pause
)

exit /b 0
