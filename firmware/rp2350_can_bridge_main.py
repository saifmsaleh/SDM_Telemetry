from machine import Pin, SPI, UART
import time

# Waveshare RP2350-CAN board schematic:
#   XL2515 INT  -> GPIO8
#   XL2515 CS   -> GPIO9
#   XL2515 SCLK -> GPIO10
#   XL2515 MOSI -> GPIO11
#   XL2515 MISO -> GPIO12
#
# UART bridge wiring to the ESP32 HaLow AP board:
#   RP2350 GP4/TX -> ESP32 GPIO7/RX
#   RP2350 GP5/RX -> optional ESP32 TX (unused for one-way bridge)


class MCP2515:
    CMD_RESET = 0xC0
    CMD_READ = 0x03
    CMD_WRITE = 0x02
    CMD_BIT_MODIFY = 0x05
    CMD_READ_STATUS = 0xA0

    CANSTAT = 0x0E
    CANCTRL = 0x0F
    CNF3 = 0x28
    CNF2 = 0x29
    CNF1 = 0x2A
    CANINTF = 0x2C
    EFLG = 0x2D

    RXB0CTRL = 0x60
    RXB0SIDH = 0x61
    RXB1CTRL = 0x70
    RXB1SIDH = 0x71

    RXM0SIDH = 0x20
    RXM1SIDH = 0x24
    RXF0SIDH = 0x00
    RXF1SIDH = 0x04
    RXF2SIDH = 0x08
    RXF3SIDH = 0x10
    RXF4SIDH = 0x14
    RXF5SIDH = 0x18

    MODE_NORMAL = 0
    MODE_SLEEP = 1
    MODE_LOOPBACK = 2
    MODE_LISTEN_ONLY = 3
    MODE_CONFIG = 4

    BITRATE_CONFIGS = {
        1000000: (0x00, 0xD0, 0x82),
        500000: (0x00, 0xF0, 0x86),
        250000: (0x01, 0xF0, 0x86),
        125000: (0x03, 0xF0, 0x86),
        100000: (0x04, 0xF0, 0x86),
        83333: (0x03, 0xBE, 0x07),
    }

    def __init__(self, spi, cs_pin, int_pin):
        self.spi = spi
        self.cs = cs_pin
        self.int_pin = int_pin
        self.cs.on()

    def _select(self):
        self.cs.off()

    def _deselect(self):
        self.cs.on()

    def reset(self):
        self._select()
        self.spi.write(bytearray([self.CMD_RESET]))
        self._deselect()
        time.sleep_ms(10)

    def read_register(self, address):
        self._select()
        self.spi.write(bytearray([self.CMD_READ, address]))
        value = self.spi.read(1, 0x00)[0]
        self._deselect()
        return value

    def read_registers(self, address, count):
        self._select()
        self.spi.write(bytearray([self.CMD_READ, address]))
        data = self.spi.read(count, 0x00)
        self._deselect()
        return data

    def write_register(self, address, value):
        self._select()
        self.spi.write(bytearray([self.CMD_WRITE, address, value]))
        self._deselect()

    def write_registers(self, address, values):
        self._select()
        self.spi.write(bytearray([self.CMD_WRITE, address]) + bytearray(values))
        self._deselect()

    def bit_modify(self, address, mask, value):
        self._select()
        self.spi.write(bytearray([self.CMD_BIT_MODIFY, address, mask, value]))
        self._deselect()

    def set_mode(self, mode):
        self.bit_modify(self.CANCTRL, 0xE0, mode << 5)
        for _ in range(50):
            canstat = self.read_register(self.CANSTAT)
            if (canstat & 0xE0) == (mode << 5):
                return True
            time.sleep_ms(2)
        return False

    def configure_accept_all(self):
        self.write_register(self.RXB0CTRL, 0x64)
        self.write_register(self.RXB1CTRL, 0x60)

        for address in (
            self.RXM0SIDH,
            self.RXM1SIDH,
            self.RXF0SIDH,
            self.RXF1SIDH,
            self.RXF2SIDH,
            self.RXF3SIDH,
            self.RXF4SIDH,
            self.RXF5SIDH,
        ):
            self.write_registers(address, (0x00, 0x00, 0x00, 0x00))

    def configure(self, bitrate, listen_only=True):
        if bitrate not in self.BITRATE_CONFIGS:
            raise ValueError("Unsupported CAN bitrate: {}".format(bitrate))

        cnf1, cnf2, cnf3 = self.BITRATE_CONFIGS[bitrate]

        self.reset()
        if not self.set_mode(self.MODE_CONFIG):
            raise RuntimeError("Failed to enter MCP2515 config mode")

        self.write_register(self.CNF1, cnf1)
        self.write_register(self.CNF2, cnf2)
        self.write_register(self.CNF3, cnf3)
        self.configure_accept_all()
        self.write_register(self.CANINTF, 0x00)

        target_mode = self.MODE_LISTEN_ONLY if listen_only else self.MODE_NORMAL
        if not self.set_mode(target_mode):
            raise RuntimeError("Failed to enter MCP2515 target mode")

    def has_pending_frame(self):
        if self.int_pin.value() == 0:
            return True
        return (self.read_register(self.CANINTF) & 0x03) != 0

    def _decode_frame(self, raw):
        sidh = raw[0]
        sidl = raw[1]
        eid8 = raw[2]
        eid0 = raw[3]
        dlc = raw[4] & 0x0F
        is_extended = (sidl & 0x08) != 0
        is_rtr = (raw[4] & 0x40) != 0

        if is_extended:
            sid = (sidh << 3) | (sidl >> 5)
            eid = ((sidl & 0x03) << 16) | (eid8 << 8) | eid0
            can_id = (sid << 18) | eid
        else:
            can_id = (sidh << 3) | (sidl >> 5)

        payload = bytes(raw[5:5 + dlc])
        return {
            "id": can_id,
            "extended": is_extended,
            "rtr": is_rtr,
            "dlc": dlc,
            "data": payload,
        }

    def read_frame(self):
        canintf = self.read_register(self.CANINTF)

        if canintf & 0x01:
            raw = self.read_registers(self.RXB0SIDH, 13)
            self.bit_modify(self.CANINTF, 0x01, 0x00)
            return self._decode_frame(raw)

        if canintf & 0x02:
            raw = self.read_registers(self.RXB1SIDH, 13)
            self.bit_modify(self.CANINTF, 0x02, 0x00)
            return self._decode_frame(raw)

        return None


UART_ID = 1
UART_BAUD_RATE = 115200
UART_TX_PIN = 4
UART_RX_PIN = 5

SPI_ID = 1
SPI_BAUD_RATE = 1_000_000
CAN_INT_PIN = 8
CAN_CS_PIN = 9
CAN_SCK_PIN = 10
CAN_MOSI_PIN = 11
CAN_MISO_PIN = 12

AUTO_DETECT_BITRATE = False
FIXED_CAN_BITRATE = 1000000
BITRATE_SCAN_ORDER = (500000, 250000, 125000, 100000, 83333)
BITRATE_SCAN_MS = 3000

TRANSLATED_IDS = {
    0x3E8: "ECU_STREAM2",
    0x3E9: "ECU_RPM_FAST",
    0x3EA: "ECU_PRESSURES",
    0x3EB: "ECU_TEMPS",
}

FORWARD_ONLY_TRANSLATED_IDS = True
FORWARD_ONLY_STREAMS_AND_PDM = True
MONITOR_ONLY_IDS = (0x3E9, 0x3EA, 0x3EB)


uart = UART(
    UART_ID,
    baudrate=UART_BAUD_RATE,
    bits=8,
    parity=None,
    stop=1,
    tx=Pin(UART_TX_PIN),
    rx=Pin(UART_RX_PIN),
)

spi = SPI(
    SPI_ID,
    baudrate=SPI_BAUD_RATE,
    polarity=0,
    phase=0,
    sck=Pin(CAN_SCK_PIN),
    mosi=Pin(CAN_MOSI_PIN),
    miso=Pin(CAN_MISO_PIN),
)

can = MCP2515(
    spi=spi,
    cs_pin=Pin(CAN_CS_PIN, Pin.OUT, value=1),
    int_pin=Pin(CAN_INT_PIN, Pin.IN, Pin.PULL_UP),
)


def send_bridge_line(line, echo=True):
    uart.write(line)
    uart.write("\n")
    if echo:
        print("UART OUT:", line)


def format_can_frame(frame):
    dlc = frame["dlc"]
    if dlc > 8:
        dlc = 8

    label = TRANSLATED_IDS.get(frame["id"])
    parts = [
        label if label is not None else "CAN",
        "id={:X}".format(frame["id"]),
        "ext={}".format(1 if frame["extended"] else 0),
        "dlc={}".format(dlc),
    ]

    if frame["rtr"]:
        parts.append("rtr=1")
        parts.append("data=")
        return ",".join(parts)

    parts.append("data={}".format(frame["data"][:dlc].hex().upper()))
    return ",".join(parts)


def read_be_unsigned(data, start_bit, width):
    start_byte = start_bit // 8
    byte_len = width // 8
    value = 0

    for index in range(byte_len):
        value = (value << 8) | data[start_byte + index]

    return value


def read_be_signed(data, start_bit, width):
    value = read_be_unsigned(data, start_bit, width)
    sign_bit = 1 << (width - 1)
    if value & sign_bit:
        value -= 1 << width
    return value


def format_stream2_frame(frame):
    data = frame["data"]

    if len(data) == 0:
        return "ECU Stream2 raw={}".format(data.hex().upper())

    frame_selector = data[0]

    if frame_selector == 0 and len(data) >= 8:
        engine_speed = read_be_unsigned(data, 8, 16)
        ect = read_be_signed(data, 24, 8)
        oil_temp = read_be_signed(data, 32, 8)
        oil_pressure = read_be_unsigned(data, 40, 16)
        neutral_park = read_be_unsigned(data, 56, 8)

        return (
            "ECU Stream2 Frame1 "
            "id=3E8 rpm={} ect={} oil_temp={} oil_pressure={} neutral_park={} raw={}"
        ).format(
            engine_speed,
            ect,
            oil_temp,
            oil_pressure,
            neutral_park,
            data.hex().upper(),
        )

    if frame_selector == 1 and len(data) >= 8:
        lambda1 = read_be_unsigned(data, 8, 8)
        tps_main = read_be_unsigned(data, 16, 8)
        gear_status = read_be_unsigned(data, 24, 8)
        driven_wheel_speed = read_be_unsigned(data, 32, 16)
        oil_pressure = read_be_unsigned(data, 40, 16)

        return (
            "ECU Stream2 Frame2 "
            "id=3E8 lambda1_raw={} tps_main_raw={} gear_status={} "
            "driven_wheel_speed={} oil_pressure={} raw={}"
        ).format(
            lambda1,
            tps_main,
            gear_status,
            driven_wheel_speed,
            oil_pressure,
            data.hex().upper(),
        )

    if frame_selector == 2 and len(data) >= 6:
        aps_main = read_be_unsigned(data, 8, 16)
        fuel_pressure = read_be_unsigned(data, 24, 16)

        return (
            "ECU Stream2 Frame3 "
            "id=3E8 aps_main_raw={} fuel_pressure={} raw={}"
        ).format(
            aps_main,
            fuel_pressure,
            data.hex().upper(),
        )

    if len(data) >= 1:
        return "ECU Stream2 Frame{} id=3E8 raw={}".format(frame_selector + 1, data.hex().upper())

    return "ECU Stream2 id=3E8 raw={}".format(data.hex().upper())


def format_rpm_fast_frame(frame):
    data = frame["data"]
    if len(data) >= 6:
        engine_speed = read_be_unsigned(data, 8, 16)
        tps_main = read_be_unsigned(data, 24, 8)
        aps_main = read_be_unsigned(data, 32, 8)
        lambda1 = read_be_unsigned(data, 40, 8)
        return "ECU Stream5 Frame1 id=3E9 rpm={} tps={} aps={} lambda1={} raw={}".format(
            engine_speed,
            tps_main,
            aps_main,
            lambda1,
            data.hex().upper(),
        )
    return "ECU Stream5 Frame1 id=3E9 raw={}".format(data.hex().upper())


def format_pressures_frame(frame):
    data = frame["data"]
    if len(data) >= 7:
        oil_pressure = read_be_unsigned(data, 8, 16)
        fuel_pressure = read_be_unsigned(data, 24, 16)
        map_value = read_be_unsigned(data, 40, 16)
        return (
            "ECU Stream6 Frame1 id=3EA oil_pressure={} fuel_pressure={} map={} raw={}"
        ).format(
            oil_pressure,
            fuel_pressure,
            map_value,
            data.hex().upper(),
        )
    return "ECU Stream6 Frame1 id=3EA raw={}".format(data.hex().upper())


def format_temps_frame(frame):
    data = frame["data"]
    if len(data) >= 6:
        ect = data[4]
        oil_temp = data[5]
        return "ECU Stream7 Frame1 id=3EB ect={} oil_temp={} raw={}".format(
            ect,
            oil_temp,
            data.hex().upper(),
        )
    return "ECU Stream7 Frame1 id=3EB raw={}".format(data.hex().upper())


def format_forward_line(frame):
    if frame["id"] == 0x3E8:
        return format_stream2_frame(frame)
    if frame["id"] == 0x3E9:
        return format_rpm_fast_frame(frame)
    if frame["id"] == 0x3EA:
        return format_pressures_frame(frame)
    if frame["id"] == 0x3EB:
        return format_temps_frame(frame)
    return format_can_frame(frame)


def poll_uart_inbound():
    if not uart.any():
        return

    raw = uart.readline()
    if not raw:
        return

    try:
        line = raw.decode("utf-8").strip()
    except Exception:
        line = str(raw)

    if line:
        print("UART IN:", line)


def should_forward_frame(frame):
    if not FORWARD_ONLY_TRANSLATED_IDS:
        return True
    if frame["id"] not in TRANSLATED_IDS:
        return False

    if not FORWARD_ONLY_STREAMS_AND_PDM:
        return True

    if frame["id"] == 0x3E8 and len(frame["data"]) > 0 and frame["data"][0] in (0, 1, 2):
        return True
    if frame["id"] in (0x3E9, 0x3EA, 0x3EB):
        return True

    return False


def should_echo_frame(frame):
    return frame["id"] in MONITOR_ONLY_IDS


def try_detect_bitrate():
    for bitrate in BITRATE_SCAN_ORDER:
        print("Trying CAN bitrate {} bps in listen-only mode".format(bitrate))
        try:
            can.configure(bitrate, listen_only=True)
        except Exception as exc:
            print("CAN configure failed:", exc)
            continue

        deadline = time.ticks_add(time.ticks_ms(), BITRATE_SCAN_MS)

        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            poll_uart_inbound()

            if can.has_pending_frame():
                frame = can.read_frame()
                if frame is not None:
                    print("Detected CAN bitrate {}".format(bitrate))
                    return bitrate, frame

            time.sleep_ms(10)

    return None, None


def main():
    print("RP2350 CAN to UART bridge starting")
    print("UART{} TX=GP{} RX=GP{} baud={}".format(
        UART_ID,
        UART_TX_PIN,
        UART_RX_PIN,
        UART_BAUD_RATE,
    ))
    print("CAN SPI{} CS=GP{} SCK=GP{} MOSI=GP{} MISO=GP{} INT=GP{}".format(
        SPI_ID,
        CAN_CS_PIN,
        CAN_SCK_PIN,
        CAN_MOSI_PIN,
        CAN_MISO_PIN,
        CAN_INT_PIN,
    ))
    print("Listen-only mode enabled")
    print("AUTO_DETECT_BITRATE={}".format(AUTO_DETECT_BITRATE))
    print("FORWARD_ONLY_TRANSLATED_IDS={}".format(FORWARD_ONLY_TRANSLATED_IDS))
    print("FORWARD_ONLY_STREAMS_AND_PDM={}".format(FORWARD_ONLY_STREAMS_AND_PDM))
    for can_id, label in TRANSLATED_IDS.items():
        print("Label {} -> 0x{:X}".format(label, can_id))

    bitrate = FIXED_CAN_BITRATE
    first_frame = None

    if AUTO_DETECT_BITRATE:
        detected_bitrate, detected_frame = try_detect_bitrate()
        if detected_bitrate is not None:
            bitrate = detected_bitrate
            first_frame = detected_frame
        else:
            print("No frames detected during auto-scan, falling back to {} bps".format(bitrate))
            can.configure(bitrate, listen_only=True)
    else:
        can.configure(bitrate, listen_only=True)

    print("Using CAN bitrate {} bps".format(bitrate))

    if first_frame is not None:
        if should_forward_frame(first_frame):
            send_bridge_line(format_forward_line(first_frame), echo=should_echo_frame(first_frame))

    while True:
        poll_uart_inbound()

        while can.has_pending_frame():
            frame = can.read_frame()
            if frame is None:
                break

            if should_forward_frame(frame):
                send_bridge_line(format_forward_line(frame), echo=should_echo_frame(frame))

        time.sleep_ms(10)


main()
