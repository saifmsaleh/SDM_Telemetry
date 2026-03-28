# RP2350 CAN to HaLow Bridge

## Overview

The `chat_ap` example now acts as a UART-to-HaLow bridge.

Data flow:

`CAN bus -> Waveshare RP2350-CAN -> UART -> ESP32-S3 AP board -> HaLow TCP -> ESP32-S3 STA board`

The `chat_sta` example remains the receiver and prints the forwarded lines.

## Default Wiring

Between the Waveshare RP2350-CAN board and the ESP32-S3 AP board:

- `RP2350 TX` -> `ESP32 RX` on `GPIO44`
- `RP2350 RX` -> `ESP32 TX` on `GPIO43`
- `GND` -> `GND`

Default AP UART settings:

- UART port: `UART1`
- RX pin: `GPIO44`
- TX pin: `GPIO43`
- Baud rate: `115200`
- Framing: `8N1`

## Message Format

Start with line-oriented ASCII messages from the RP2350.

Example:

```text
CAN,id=123,ext=0,dlc=8,data=1122334455667788
```

Each line must end with `\n`.

The AP board forwards each complete UART line to the STA board over the existing HaLow TCP link.

Messages sent from the STA board are written back out on the AP board UART as CRLF-terminated lines.

## Current Firmware Roles

- `chat_ap`
  - starts the HaLow AP
  - listens for the STA TCP client
  - reads UART lines from the RP2350 and forwards them to the STA
  - writes lines received from the STA back to the RP2350 over UART

- `chat_sta`
  - joins the HaLow AP
  - connects to the AP TCP server
  - prints the forwarded UART/CAN lines
  - can still send manual lines back to the AP

## RP2350 Firmware Guidance

On the RP2350:

1. Read a CAN frame from the onboard CAN controller.
2. Convert it to one ASCII line.
3. Write that line to the UART connected to the AP board.

Recommended first step:

- send fixed test lines over UART before integrating real CAN parsing
- once the STA receives those lines, replace the test data with actual CAN frame formatting

## Desktop Dashboard

The translated CAN output can also be viewed in the desktop dashboard:

- script: `C:\Users\Saif\mm-iot-esp32\examples\can_dashboard_gui.py`
- reference style: `C:\Users\Saif\mm-iot-esp32\examples\GUI Example.png`

Use the local Anaconda Python, not the ESP-IDF Python environment, because the ESP-IDF environment does not include `tkinter`.

Run the live dashboard from the STA serial output on `COM12`:

```powershell
C:\Users\Saif\anaconda3\python.exe C:\Users\Saif\mm-iot-esp32\examples\can_dashboard_gui.py --port COM12
```

If you just want to preview the layout without hardware:

```powershell
C:\Users\Saif\anaconda3\python.exe C:\Users\Saif\mm-iot-esp32\examples\can_dashboard_gui.py --demo
```

If the dashboard says the serial port is busy, close PuTTY or any other monitor attached to `COM12` and run the command again.

## Optional AP Build Overrides

The AP example supports compile-time overrides:

- `BRIDGE_UART_BAUD_RATE`
- `BRIDGE_UART_RX_PIN`
- `BRIDGE_UART_TX_PIN`

Example:

```powershell
python C:\Espressif\frameworks\esp-idf-v5.1.1\tools\idf.py -DBRIDGE_UART_RX_PIN=44 -DBRIDGE_UART_TX_PIN=43 -DBRIDGE_UART_BAUD_RATE=115200 build
```
