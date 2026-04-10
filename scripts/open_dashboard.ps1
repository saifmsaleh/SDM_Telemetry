param(
    [string]$Port = "COM12",
    [switch]$Demo,
    [string]$Python
)

function Resolve-PythonCommand {
    param([string]$PreferredPython)

    if ($PreferredPython) {
        $cmd = Get-Command $PreferredPython -ErrorAction SilentlyContinue
        if ($cmd) {
            return @($cmd.Source)
        }
        throw "Requested Python executable was not found on PATH: $PreferredPython"
    }

    foreach ($candidate in @("python", "py")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            try {
                if ($candidate -eq "py") {
                    & $cmd.Source -3 -c "import sys" *> $null
                    if ($LASTEXITCODE -eq 0) {
                        return @($cmd.Source, "-3")
                    }
                }
                else {
                    & $cmd.Source -c "import sys" *> $null
                    if ($LASTEXITCODE -eq 0) {
                        return @($cmd.Source)
                    }
                }
            }
            catch {
                continue
            }
        }
    }

    throw "Python was not found. Install Python 3 and make sure 'py' or 'python' is on PATH."
}

$telemetryRoot = Split-Path $PSScriptRoot -Parent
$dashboardPath = Join-Path $telemetryRoot "dashboard\can_dashboard_gui.py"

if (-not (Test-Path -LiteralPath $dashboardPath)) {
    Write-Error "Dashboard not found: $dashboardPath"
    exit 1
}

try {
    $pythonCmd = @(Resolve-PythonCommand -PreferredPython $Python)
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}

$argsList = @($dashboardPath)
if ($Demo) {
    $argsList += "--demo"
}
else {
    $argsList += @("--port", $Port)
}

$pythonArgs = @()
if ($pythonCmd.Length -gt 1) {
    $pythonArgs += $pythonCmd[1..($pythonCmd.Length - 1)]
}
$pythonArgs += $argsList
& $pythonCmd[0] @pythonArgs
