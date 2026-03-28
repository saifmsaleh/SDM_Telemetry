# Monitor Launchers

These PowerShell scripts are provided so the telemetry folder is usable without remembering the full commands.

## Scripts

- `scripts/open_dashboard.ps1`
  - Launches the dashboard GUI on a serial port
- `scripts/open_sta_monitor.ps1`
  - Opens the ESP-IDF monitor for the STA board when available, otherwise falls back to raw serial
- `scripts/open_ap_monitor.ps1`
  - Opens the ESP-IDF monitor for the AP board when available, otherwise falls back to raw serial
- `scripts/open_rp2350_monitor.ps1`
  - Opens a simple serial line monitor for the RP2350 bridge

## Default Ports

- `COM12` = STA board
- `COM13` = AP board
- `COM15` = RP2350

Change them with the `-Port` argument if Windows assigns a different port.

## Usage

Dashboard:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_dashboard.ps1 -Port COM12
```

You can force a specific Python executable if needed:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_dashboard.ps1 -Port COM12 -Python python
```

STA monitor:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_sta_monitor.ps1 -Port COM12
```

AP monitor:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_ap_monitor.ps1 -Port COM13
```

RP2350 monitor:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_rp2350_monitor.ps1 -Port COM15
```

## Typical Workflow

1. Open the STA monitor.
2. Open the AP monitor if you need bridge-side diagnostics.
3. Open the RP2350 monitor if you need raw bridge output verification.
4. Open the dashboard on the STA port.

## Notes

- `idf_monitor.py` is resolved from:
  - `IDF_MONITOR_PY`
  - `IDF_PATH`
  - or a script argument like `-IdfPath C:\path\to\esp-idf`
- If `idf_monitor.py` or the firmware ELF is not available, the AP/STA scripts automatically fall back to a plain serial monitor.
- `idf_monitor.py` is used directly because it is more reliable for this setup than `idf.py monitor`.
- Exit the ESP-IDF monitor with `Ctrl+]`.
- Stop the raw serial monitors with `Ctrl+C`.
