param(
    [string]$Port = "COM13",
    [int]$Baud = 115200
)

$telemetryRoot = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path $telemetryRoot -Parent
$elfPath = Join-Path $repoRoot "examples\chat_ap\build\chat_ap.elf"
$pythonExe = "C:\Espressif\python_env\idf5.1_py3.11_env\Scripts\python.exe"
$monitorPy = "C:\Espressif\frameworks\esp-idf-v5.1.1\tools\idf_monitor.py"

if (-not (Test-Path -LiteralPath $elfPath)) {
    Write-Error "AP ELF not found: $elfPath"
    exit 1
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    Write-Error "ESP-IDF Python not found: $pythonExe"
    exit 1
}

if (-not (Test-Path -LiteralPath $monitorPy)) {
    Write-Error "idf_monitor.py not found: $monitorPy"
    exit 1
}

& $pythonExe $monitorPy -p "\\.\$Port" -b $Baud $elfPath
