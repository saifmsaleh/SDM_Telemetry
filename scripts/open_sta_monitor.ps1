param(
    [string]$Port = "COM12",
    [int]$Baud = 115200,
    [string]$Python,
    [string]$IdfPath
)

function Start-RawSerialMonitor {
    param(
        [string]$TargetPort,
        [int]$TargetBaud
    )

    $serial = New-Object System.IO.Ports.SerialPort $TargetPort, $TargetBaud, "None", 8, "one"
    $serial.NewLine = "`n"
    $serial.ReadTimeout = 1000

    try {
        $serial.Open()
        Write-Host "STA raw serial monitor on $TargetPort @ $TargetBaud. Press Ctrl+C to stop." -ForegroundColor Yellow
        while ($true) {
            try {
                $line = $serial.ReadLine()
                if ($line -ne $null) {
                    Write-Host $line.TrimEnd("`r", "`n")
                }
            }
            catch [System.TimeoutException] {
            }
        }
    }
    finally {
        if ($serial.IsOpen) {
            $serial.Close()
        }
    }
}

function Resolve-PythonCommand {
    param([string]$PreferredPython)

    if ($PreferredPython) {
        $cmd = Get-Command $PreferredPython -ErrorAction SilentlyContinue
        if ($cmd) {
            return @($cmd.Source)
        }
        throw "Requested Python executable was not found on PATH: $PreferredPython"
    }

    foreach ($candidate in @("py", "python")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            if ($candidate -eq "py") {
                return @($cmd.Source, "-3")
            }
            return @($cmd.Source)
        }
    }

    throw "Python was not found. Install Python 3 and make sure 'py' or 'python' is on PATH."
}

function Resolve-IdfMonitorPath {
    param([string]$PreferredIdfPath)

    if ($env:IDF_MONITOR_PY -and (Test-Path -LiteralPath $env:IDF_MONITOR_PY)) {
        return $env:IDF_MONITOR_PY
    }

    $candidateRoots = @()
    if ($PreferredIdfPath) { $candidateRoots += $PreferredIdfPath }
    if ($env:IDF_PATH) { $candidateRoots += $env:IDF_PATH }

    foreach ($root in $candidateRoots) {
        $monitorPy = Join-Path $root "tools\idf_monitor.py"
        if (Test-Path -LiteralPath $monitorPy) {
            return $monitorPy
        }
    }

    throw "idf_monitor.py was not found. Set IDF_PATH or pass -IdfPath to your ESP-IDF installation."
}

$telemetryRoot = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path $telemetryRoot -Parent
$elfPath = Join-Path $repoRoot "examples\chat_sta\build\chat_sta.elf"

try {
    $pythonCmd = Resolve-PythonCommand -PreferredPython $Python
    $monitorPy = Resolve-IdfMonitorPath -PreferredIdfPath $IdfPath
}
catch {
    Write-Warning $_.Exception.Message
    Start-RawSerialMonitor -TargetPort $Port -TargetBaud $Baud
    exit 0
}

if (-not (Test-Path -LiteralPath $elfPath)) {
    Write-Warning "STA ELF not found, falling back to raw serial monitor: $elfPath"
    Start-RawSerialMonitor -TargetPort $Port -TargetBaud $Baud
    exit 0
}

& $pythonCmd[0] @($pythonCmd[1..($pythonCmd.Length - 1)]) $monitorPy -p "\\.\$Port" -b $Baud $elfPath
