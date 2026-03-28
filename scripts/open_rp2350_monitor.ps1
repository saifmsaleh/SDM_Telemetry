param(
    [string]$Port = "COM15",
    [int]$Baud = 115200
)

$serial = New-Object System.IO.Ports.SerialPort $Port, $Baud, "None", 8, "one"
$serial.NewLine = "`n"
$serial.ReadTimeout = 1000

try {
    $serial.Open()
    Write-Host "Monitoring $Port @ $Baud. Press Ctrl+C to stop." -ForegroundColor Cyan
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
