# Setup

## Requirements

- Python 3.10+ available on `PATH` as `py` or `python`
- `pyserial`
- `Pillow`
- ESP-IDF installed if you want to use the AP/STA monitor scripts

Install Python dependencies from the telemetry root:

```powershell
py -3 -m pip install -r .\requirements.txt
```

If `py` is not available:

```powershell
python -m pip install -r .\requirements.txt
```

## ESP-IDF

The STA/AP monitor scripts look for `idf_monitor.py` in one of these places:

1. `IDF_MONITOR_PY`
2. `IDF_PATH\tools\idf_monitor.py`
3. an explicit `-IdfPath` argument passed to the script

Recommended:

```powershell
$env:IDF_PATH = 'C:\Espressif\frameworks\esp-idf-v5.1.1'
```

## Launch

Dashboard:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_dashboard.ps1 -Port COM12
```

Demo mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\open_dashboard.ps1 -Demo
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

## Notes

- The AP/STA monitor scripts still expect the firmware ELF files to exist in:
  - `examples/chat_ap/build/chat_ap.elf`
  - `examples/chat_sta/build/chat_sta.elf`
- The telemetry repo is portable, but those monitor scripts depend on the parent repo still containing the ESP example firmware builds.
