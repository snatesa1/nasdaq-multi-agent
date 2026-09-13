# OptionsLab Windows Native Frontend Launcher
# Launches the Next.js frontend bound to 0.0.0.0:3000 for local and Wi-Fi access.

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   OptionsLab Windows Native Frontend Launcher" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$Port = 3000
$FrontendDir = Join-Path $PSScriptRoot "options_lab\frontend"

# 1. Kill any stale process on port 3000
Write-Host "[1/2] Checking for active processes on port $Port..." -ForegroundColor Yellow
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

# 2. Detect local Wi-Fi / LAN IP and launch Next.js on 0.0.0.0
$localIP = "127.0.0.1"
try {
    $ipObj = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback|vEthernet|Virtual|WSL" -and $_.IPAddress -match "^192\.168\." } | Select-Object -First 1
    if ($ipObj) {
        $localIP = $ipObj.IPAddress
    }
} catch {}

Write-Host "[2/2] Starting Next.js frontend on 0.0.0.0:$Port..." -ForegroundColor Yellow
Write-Host "  -> Localhost URL: http://localhost:$Port" -ForegroundColor Green
Write-Host "  -> Local Wi-Fi URL: http://$($localIP):$Port" -ForegroundColor Cyan

Push-Location $FrontendDir
try {
    npx.cmd next dev -H 0.0.0.0 -p $Port
} finally {
    Pop-Location
}
