param(
    [string]$Port = "COM12"
)

$telemetryRoot = Split-Path $PSScriptRoot -Parent
$dashboardPath = Join-Path $telemetryRoot "dashboard\can_dashboard_gui.py"
$pythonExe = "C:\Users\Saif\anaconda3\python.exe"

if (-not (Test-Path -LiteralPath $dashboardPath)) {
    Write-Error "Dashboard not found: $dashboardPath"
    exit 1
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "Python not found: $pythonExe"
    exit 1
}

& $pythonExe $dashboardPath --port $Port
