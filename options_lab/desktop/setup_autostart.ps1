# OptionsLab Windows Auto-Start Registration Script
# Registers OptionsLab to start automatically when Windows boots / user logs in

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherBat = Join-Path $scriptDir "start_desktop.bat"
$startupFolder = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$shortcutPath = Join-Path $startupFolder "OptionsLab.lnk"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Configuring OptionsLab Windows Auto-Startup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Create Desktop Launcher Shortcut in Windows Startup Folder
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = $launcherBat
$Shortcut.WorkingDirectory = $scriptDir
$Shortcut.Description = "OptionsLab Automated Quant Ecosystem & Broker Gateway"
$Shortcut.WindowStyle = 7 # Minimized
$Shortcut.Save()

Write-Host "[SUCCESS] Windows Startup Shortcut created at:" -ForegroundColor Green
Write-Host "  -> $shortcutPath" -ForegroundColor Yellow

# 2. Registry verification
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$regName = "OptionsLab"
Set-ItemProperty -Path $regPath -Name $regName -Value "`"$launcherBat`" --hidden"

Write-Host "[SUCCESS] Windows Registry Auto-Run Key configured under:" -ForegroundColor Green
Write-Host "  -> $regPath ($regName)" -ForegroundColor Yellow
Write-Host "`nOptionsLab will now automatically launch in background tray on computer startup!" -ForegroundColor Cyan
