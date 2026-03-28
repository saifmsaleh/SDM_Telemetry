# SDM Telemetry

This folder contains the custom telemetry dashboard, RP2350 bridge script, supporting docs, and reference assets used during bring-up.

## Structure

- `dashboard/`
  - `can_dashboard_gui.py`
- `firmware/`
  - `rp2350_can_bridge_main.py`
- `docs/`
  - `CAN_BRIDGE_INSTRUCTIONS.md`
  - `MONITORS.md`
- `scripts/`
  - monitor and dashboard launchers
- `assets/logos/`
  - runtime logos used by the GUI
- `references/gui/`
  - GUI reference images
- `references/photos/`
  - hardware/setup photos
- `references/pclink/`
  - PCLink screenshot references

## Run The Dashboard

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_dashboard.ps1 -Port COM12
```

Demo mode:

```powershell
C:\Users\Saif\anaconda3\python.exe C:\Users\Saif\mm-iot-esp32\telemetry\dashboard\can_dashboard_gui.py --demo
```

## Monitors

See [MONITORS.md](C:\Users\Saif\mm-iot-esp32\telemetry\docs\MONITORS.md) for monitor usage.

Quick launch examples:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_sta_monitor.ps1 -Port COM12
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_ap_monitor.ps1 -Port COM13
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_rp2350_monitor.ps1 -Port COM15
```

## Notes

- The dashboard loads its team logo from `assets/logos/`.
- The settings UI is GUI-side only unless explicitly wired into the decoder later.
- Reference images are kept out of the runtime folders so the repo is easier to navigate.
