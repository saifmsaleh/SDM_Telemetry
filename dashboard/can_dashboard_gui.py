import argparse
import csv
import ctypes
import json
import math
import os
import queue
import random
import re
import threading
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, simpledialog
from tkinter import ttk
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    import serial
    from serial import SerialException
    try:
        from serial.tools import list_ports
    except ImportError:  # pragma: no cover - optional pyserial helper
        list_ports = None
except ImportError:  # pragma: no cover - handled at runtime
    serial = None
    SerialException = Exception
    list_ports = None

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - handled at runtime
    Image = None
    ImageTk = None


BACKGROUND = "#0F1116"
CARD_BG = "#171A21"
CARD_BORDER = "#232833"
CARD_HOVER = "#1D222C"
TEXT = "#E7EAF0"
MUTED = "#9DA6B5"
ACCENT = "#F4B41A"
ACCENT_2 = "#8C1D40"
HALOW_ACCENT = "#7DD3FC"
WARNING = "#F3C746"
DANGER = "#C25170"
GRID = "#232833"
TRACK = "#242933"
GAP_XS = 4
GAP_SM = 8
GAP_MD = 12
GAP_LG = 16
GAP_XL = 24
PILL_FONT = ("Bahnschrift SemiBold", 10)
LABEL_FONT = ("Bahnschrift SemiBold", 11)
PERSISTED_STATE_FILE = "dashboard_state.json"
PROFILES_DIR_NAME = "profiles"
CUSTOM_GRAPH_PANEL_NAMES = ("custom_trend", "custom_trend_2", "custom_trend_3", "custom_trend_4")
CORE_TAB_NAMES = {"LIVE", "LOGGING"}

DEFAULT_PANEL_LAYOUTS = {
    "wheel_gauge": {"x": 0.015, "y": 0.04, "w": 0.215, "h": 0.19, "visible": False},
    "tps_gauge": {"x": 0.015, "y": 0.255, "w": 0.215, "h": 0.19, "visible": False},
    "aps_gauge": {"x": 0.015, "y": 0.47, "w": 0.215, "h": 0.19, "visible": False},
    "gear_stat": {"x": 0.015, "y": 0.685, "w": 0.215, "h": 0.19, "visible": False},
    "oil_temp_gauge": {"x": 0.77, "y": 0.04, "w": 0.215, "h": 0.125, "visible": False},
    "coolant_gauge": {"x": 0.77, "y": 0.175, "w": 0.215, "h": 0.125, "visible": False},
    "lambda_gauge": {"x": 0.77, "y": 0.31, "w": 0.215, "h": 0.125, "visible": False},
    "map_gauge": {"x": 0.77, "y": 0.445, "w": 0.215, "h": 0.125, "visible": False},
    "fuel_pressure_gauge": {"x": 0.77, "y": 0.58, "w": 0.215, "h": 0.125, "visible": False},
    "oil_pressure_gauge": {"x": 0.77, "y": 0.715, "w": 0.215, "h": 0.125, "visible": False},
    "rpm_tach": {"x": 0.24, "y": 0.035, "w": 0.515, "h": 0.89, "visible": False},
    "rpm_trend": {"x": 0.02, "y": 0.02, "w": 0.31, "h": 0.20, "visible": False},
    "wheel_trend": {"x": 0.35, "y": 0.02, "w": 0.31, "h": 0.20, "visible": False},
    "tps_trend": {"x": 0.68, "y": 0.02, "w": 0.30, "h": 0.20, "visible": False},
    "aps_trend": {"x": 0.02, "y": 0.27, "w": 0.31, "h": 0.20, "visible": False},
    "gear_trend": {"x": 0.35, "y": 0.27, "w": 0.31, "h": 0.20, "visible": False},
    "oil_temp_trend_single": {"x": 0.68, "y": 0.27, "w": 0.30, "h": 0.20, "visible": False},
    "coolant_trend": {"x": 0.02, "y": 0.52, "w": 0.31, "h": 0.20, "visible": False},
    "throughput_trend": {"x": 0.35, "y": 0.52, "w": 0.31, "h": 0.20, "visible": False},
    "lambda_trend": {"x": 0.68, "y": 0.52, "w": 0.30, "h": 0.20, "visible": False},
    "fuel_pressure_trend_single": {"x": 0.02, "y": 0.77, "w": 0.31, "h": 0.20, "visible": False},
    "oil_pressure_trend_single": {"x": 0.35, "y": 0.77, "w": 0.31, "h": 0.20, "visible": False},
    "map_trend": {"x": 0.68, "y": 0.77, "w": 0.30, "h": 0.20, "visible": False},
    "throttle_trend": {"x": 0.02, "y": 1.02, "w": 0.31, "h": 0.20, "visible": False},
    "temp_trend": {"x": 0.35, "y": 1.02, "w": 0.31, "h": 0.20, "visible": False},
    "pressure_trend": {"x": 0.68, "y": 1.02, "w": 0.30, "h": 0.20, "visible": False},
    "custom_trend": {"x": 0.20, "y": 0.20, "w": 0.56, "h": 0.28, "visible": False},
    "custom_trend_2": {"x": 0.18, "y": 0.52, "w": 0.56, "h": 0.28, "visible": False},
    "custom_trend_3": {"x": 0.08, "y": 0.16, "w": 0.40, "h": 0.24, "visible": False},
    "custom_trend_4": {"x": 0.52, "y": 0.16, "w": 0.40, "h": 0.24, "visible": False},
}

PANEL_MIN_SIZE = {
    "default": (220, 150),
    "trend": (420, 240),
}

PANEL_DEFS = {
    "wheel_gauge": {"label": "Wheel Speed", "section": "live"},
    "tps_gauge": {"label": "TPS", "section": "live"},
    "aps_gauge": {"label": "APS", "section": "live"},
    "gear_stat": {"label": "Gear", "section": "live"},
    "oil_temp_gauge": {"label": "Oil Temp", "section": "live"},
    "coolant_gauge": {"label": "Coolant Temp", "section": "live"},
    "rpm_tach": {"label": "Engine Speed", "section": "live"},
    "lambda_gauge": {"label": "Lambda", "section": "live"},
    "map_gauge": {"label": "MAP", "section": "live"},
    "fuel_pressure_gauge": {"label": "Fuel Pressure", "section": "live"},
    "oil_pressure_gauge": {"label": "Oil Pressure", "section": "live"},
    "rpm_trend": {"label": "RPM Graph", "section": "graphs"},
    "wheel_trend": {"label": "Wheel Speed Graph", "section": "graphs"},
    "tps_trend": {"label": "TPS Graph", "section": "graphs"},
    "aps_trend": {"label": "APS Graph", "section": "graphs"},
    "gear_trend": {"label": "Gear Graph", "section": "graphs"},
    "oil_temp_trend_single": {"label": "Oil Temp Graph", "section": "graphs"},
    "coolant_trend": {"label": "Coolant Graph", "section": "graphs"},
    "throughput_trend": {"label": "Payload Rate Graph", "section": "graphs"},
    "lambda_trend": {"label": "Lambda Graph", "section": "graphs"},
    "fuel_pressure_trend_single": {"label": "Fuel Pressure Graph", "section": "graphs"},
    "oil_pressure_trend_single": {"label": "Oil Pressure Graph", "section": "graphs"},
    "map_trend": {"label": "MAP Graph", "section": "graphs"},
    "throttle_trend": {"label": "Throttle Graph", "section": "graphs"},
    "temp_trend": {"label": "Temp Graph", "section": "graphs"},
    "pressure_trend": {"label": "Pressure Graph", "section": "graphs"},
    "custom_trend": {"label": "Custom Graph 1", "section": "graphs"},
    "custom_trend_2": {"label": "Custom Graph 2", "section": "graphs"},
    "custom_trend_3": {"label": "Custom Graph 3", "section": "graphs"},
    "custom_trend_4": {"label": "Custom Graph 4", "section": "graphs"},
}

GRAPH_METRIC_OPTIONS = {
    "rpm": {"label": "RPM", "color": ACCENT, "axis_min": 0.0, "axis_max": 15000.0, "decimals": 0},
    "tps": {"label": "TPS", "color": ACCENT, "axis_min": 0.0, "axis_max": 100.0, "decimals": 0},
    "aps": {"label": "APS", "color": ACCENT_2, "axis_min": 0.0, "axis_max": 100.0, "decimals": 0},
    "lambda1": {"label": "Lambda", "color": WARNING, "axis_min": 0.0, "axis_max": 20.0, "decimals": 1},
    "wheel_speed": {"label": "Wheel Speed", "color": "#68D391", "axis_min": 0.0, "axis_max": 220.0, "decimals": 0},
    "gear": {"label": "Gear", "color": "#63B3ED", "axis_min": 0.0, "axis_max": 6.0, "decimals": 0},
    "oil_temp": {"label": "Oil Temp", "color": ACCENT, "axis_min": 0.0, "axis_max": 140.0, "decimals": 0},
    "ect": {"label": "Coolant Temp", "color": ACCENT_2, "axis_min": 0.0, "axis_max": 130.0, "decimals": 0},
    "fuel_pressure": {"label": "Fuel Pressure", "color": "#4FD1C5", "axis_min": 0.0, "axis_max": 200.0, "decimals": 0},
    "oil_pressure": {"label": "Oil Pressure", "color": "#F6AD55", "axis_min": 0.0, "axis_max": 200.0, "decimals": 0},
    "map": {"label": "MAP", "color": "#A3E635", "axis_min": 0.0, "axis_max": 200.0, "decimals": 0},
    "throughput": {"label": "Payload Rate", "color": "#B794F4", "axis_min": 0.0, "axis_max": 2500.0, "decimals": 0},
}

RPM_MAX = 15000

FRAME1_RE = re.compile(
    r"ECU Frame1 "
    r"rpm=(?P<rpm>-?\d+) "
    r"ect=(?P<ect>-?\d+) "
    r"oil_temp=(?P<oil_temp>-?\d+) "
    r"oil_pressure=(?P<oil_pressure>-?\d+) "
    r"neutral_park=(?P<neutral_park>\d+) "
    r"raw=(?P<raw>[0-9A-F]+)"
)

FRAME2_RE = re.compile(
    r"ECU Frame2 "
    r"lambda1_raw=(?P<lambda1>\d+) "
    r"tps_main_raw=(?P<tps_main>\d+) "
    r"gear_status=(?P<gear>\d+) "
    r"driven_wheel_speed=(?P<wheel_speed>\d+) "
    r"oil_pressure=(?P<oil_pressure>\d+) "
    r"raw=(?P<raw>[0-9A-F]+)"
)

FRAME3_RE = re.compile(
    r"ECU Frame3 "
    r"aps_main_raw=(?P<aps>\d+) "
    r"fuel_pressure=(?P<fuel_pressure>\d+) "
    r"raw=(?P<raw>[0-9A-F]+)"
)

STREAM5_RE = re.compile(
    r"ECU Stream5 Frame1 id=(?P<can_id>[0-9A-Fa-f]+) "
    r"rpm=(?P<rpm>-?\d+) "
    r"tps=(?P<tps>-?\d+) "
    r"aps=(?P<aps>-?\d+) "
    r"lambda1=(?P<lambda1>-?\d+) "
    r"raw=(?P<raw>[0-9A-F]+)"
)

STREAM6_RE = re.compile(
    r"ECU Stream6 Frame1 id=(?P<can_id>[0-9A-Fa-f]+) "
    r"oil_pressure=(?P<oil_pressure>-?\d+) "
    r"fuel_pressure=(?P<fuel_pressure>-?\d+) "
    r"map=(?P<map>-?\d+) "
    r"raw=(?P<raw>[0-9A-F]+)"
)

STREAM7_RE = re.compile(
    r"ECU Stream7 Frame1 id=(?P<can_id>[0-9A-Fa-f]+) "
    r"ect=(?P<ect>-?\d+) "
    r"oil_temp=(?P<oil_temp>-?\d+) "
    r"raw=(?P<raw>[0-9A-F]+)"
)

HALOW_KV_RE = re.compile(r"([A-Za-z_]+)=([^\s]+)")

@dataclass
class Metric:
    value: float | int | None = None
    display_value: float | None = None
    velocity: float = 0.0
    minimum: float | int | None = None
    maximum: float | int | None = None

    def update(self, new_value):
        self.value = new_value
        if self.display_value is None:
            self.display_value = float(new_value)
            self.velocity = 0.0
        if self.minimum is None or new_value < self.minimum:
            self.minimum = new_value
        if self.maximum is None or new_value > self.maximum:
            self.maximum = new_value

    def animate(self, dt: float):
        if self.value is None:
            return
        target = float(self.value)
        if self.display_value is None:
            self.display_value = target
            self.velocity = 0.0
            return
        delta = target - self.display_value
        if abs(delta) < 0.01 and abs(self.velocity) < 0.01:
            self.display_value = target
            self.velocity = 0.0
            return
        # Critically damped spring smoothing keeps the gauges fluid without overshoot.
        omega = 14.0
        x = self.display_value
        v = self.velocity
        f = 1.0 + 2.0 * dt * omega
        oo = omega * omega
        hoo = dt * oo
        hhoo = dt * hoo
        det_inv = 1.0 / (f + hhoo)
        self.display_value = (f * x + dt * v + hhoo * target) * det_inv
        self.velocity = (v + hoo * (target - x)) * det_inv

    @property
    def rendered_value(self):
        if self.display_value is not None:
            return self.display_value
        return self.value

    def reset_bounds(self):
        self.minimum = self.value
        self.maximum = self.value
        self.velocity = 0.0


@dataclass
class DashboardState:
    rpm: Metric = field(default_factory=Metric)
    ect: Metric = field(default_factory=Metric)
    oil_temp: Metric = field(default_factory=Metric)
    oil_pressure: Metric = field(default_factory=Metric)
    fuel_pressure: Metric = field(default_factory=Metric)
    map: Metric = field(default_factory=Metric)
    lambda1: Metric = field(default_factory=Metric)
    tps: Metric = field(default_factory=Metric)
    aps: Metric = field(default_factory=Metric)
    gear: Metric = field(default_factory=Metric)
    wheel_speed: Metric = field(default_factory=Metric)
    throughput: Metric = field(default_factory=Metric)
    halow_link_mbps: Metric = field(default_factory=Metric)
    neutral_park: Metric = field(default_factory=Metric)
    halow_bw_mhz: float | None = None
    halow_rssi: float | None = None
    halow_mcs: str = "--"
    last_line: str = "Waiting for serial data..."
    last_update_monotonic: float = 0.0
    last_animation_monotonic: float = field(default_factory=time.monotonic)
    line_count: int = 0

    def touch(self, line: str):
        self.last_line = line
        self.last_update_monotonic = time.monotonic()
        self.line_count += 1

    def reset_metric_bounds(self):
        for metric in (
            self.rpm,
            self.ect,
            self.oil_temp,
            self.oil_pressure,
            self.fuel_pressure,
            self.map,
            self.lambda1,
            self.tps,
            self.aps,
            self.gear,
            self.wheel_speed,
            self.throughput,
            self.halow_link_mbps,
            self.neutral_park,
        ):
            metric.reset_bounds()

    def clear_metrics(self):
        for metric in (
            self.rpm,
            self.ect,
            self.oil_temp,
            self.oil_pressure,
            self.fuel_pressure,
            self.map,
            self.lambda1,
            self.tps,
            self.aps,
            self.gear,
            self.wheel_speed,
            self.throughput,
            self.halow_link_mbps,
            self.neutral_park,
        ):
            metric.value = None
            metric.display_value = None
            metric.velocity = 0.0
            metric.minimum = None
            metric.maximum = None
        self.halow_bw_mhz = None
        self.halow_rssi = None
        self.halow_mcs = "--"

    def animate_metrics(self):
        now = time.monotonic()
        dt = max(0.0, min(0.08, now - self.last_animation_monotonic))
        self.last_animation_monotonic = now
        for metric in (
            self.rpm,
            self.ect,
            self.oil_temp,
            self.oil_pressure,
            self.fuel_pressure,
            self.map,
            self.lambda1,
            self.tps,
            self.aps,
            self.gear,
            self.wheel_speed,
            self.throughput,
            self.halow_link_mbps,
            self.neutral_park,
        ):
            metric.animate(dt)

    @property
    def data_age_seconds(self) -> float:
        if self.last_update_monotonic <= 0:
            return 0.0
        return max(0.0, time.monotonic() - self.last_update_monotonic)


class SerialWorker(threading.Thread):
    def __init__(self, port: str, baudrate: int, line_queue: queue.Queue[str], demo_mode: bool):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.line_queue = line_queue
        self.demo_mode = demo_mode
        self._stop_event = threading.Event()
        self._serial = None

    def stop(self):
        self._stop_event.set()
        try:
            if self._serial is not None:
                self._serial.close()
        except Exception:
            pass

    def run(self):
        if self.demo_mode:
            self._run_demo()
            return

        if serial is None:
            self.line_queue.put("ERROR: pyserial is not installed.")
            return

        while not self._stop_event.is_set():
            try:
                with serial.Serial(self.port, self.baudrate, timeout=0.1) as ser:
                    self._serial = ser
                    self.line_queue.put(f"INFO: connected to {self.port} @ {self.baudrate}")
                    while not self._stop_event.is_set():
                        raw = ser.readline()
                        if not raw:
                            continue
                        line = raw.decode("utf-8", errors="replace").strip()
                        if line:
                            self.line_queue.put(line)
            except SerialException as exc:
                if self._stop_event.is_set():
                    break
                self.line_queue.put(f"ERROR: serial {self.port}: {exc}")
                time.sleep(0.5)
            finally:
                self._serial = None

    def _run_demo(self):
        rpm = 1800
        direction = 1
        while True:
            rpm += direction * random.randint(150, 400)
            if rpm > 11200:
                direction = -1
            elif rpm < 2000:
                direction = 1

            ect = random.randint(82, 95)
            oil_temp = random.randint(88, 108)
            oil_pressure = random.randint(28, 78)
            neutral_park = 1 if rpm < 2200 else 0
            lambda1 = random.randint(88, 105)
            tps = max(0, min(100, int((rpm / 15000) * 100) + random.randint(-4, 4)))
            gear = random.randint(2, 5)
            wheel_speed = max(0, int((rpm / 120.0) + random.randint(-3, 3)))

            self.line_queue.put(
                f"ECU Frame1 rpm={rpm} ect={ect} oil_temp={oil_temp} "
                f"oil_pressure={oil_pressure} neutral_park={neutral_park} raw=DEMO0001"
            )
            self.line_queue.put(
                f"ECU Frame2 lambda1_raw={lambda1} tps_main_raw={tps} "
                f"gear_status={gear} driven_wheel_speed={wheel_speed} oil_pressure={oil_pressure} raw=DEMO0002"
            )
            self.line_queue.put(
                f"ECU Frame3 aps_main_raw={tps} fuel_pressure={oil_pressure} raw=DEMO0003"
            )
            self.line_queue.put("PDM,id=1F4,ext=0,dlc=6,data=010203040506")
            time.sleep(0.25)


class ValueCard(tk.Frame):
    def __init__(self, master, title: str, unit: str):
        super().__init__(master, bg=CARD_BG, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.configure(width=260, height=146)
        self.grid_propagate(False)

        self.title_label = tk.Label(
            self, text=title, bg=CARD_BG, fg=MUTED, font=("Bahnschrift SemiBold", 14)
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=GAP_LG, pady=(GAP_LG, 2))

        self.min_label = tk.Label(
            self, text="MIN --", bg=CARD_BG, fg=MUTED, font=("Bahnschrift Condensed", 12)
        )
        self.min_label.grid(row=0, column=1, sticky="e", padx=(GAP_SM, GAP_LG), pady=(GAP_LG, 0))

        self.value_label = tk.Label(
            self, text="--", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 32)
        )
        self.value_label.grid(row=1, column=0, sticky="w", padx=GAP_LG, pady=(4, 0))

        self.max_label = tk.Label(
            self, text="MAX --", bg=CARD_BG, fg=MUTED, font=("Bahnschrift Condensed", 12)
        )
        self.max_label.grid(row=1, column=1, sticky="ne", padx=(GAP_SM, GAP_LG), pady=(GAP_SM, 0))

        self.unit_label = tk.Label(
            self, text=unit, bg=CARD_BG, fg=MUTED, font=("Bahnschrift SemiBold", 12)
        )
        self.unit_label.grid(row=2, column=0, sticky="w", padx=GAP_LG, pady=(GAP_SM, GAP_LG))

        self.columnconfigure(0, weight=1)

    def set_metric(self, metric: Metric, formatter=str):
        current = metric.rendered_value
        self.value_label.config(text="--" if current is None else formatter(current))
        self.min_label.config(text="MIN --" if metric.minimum is None else f"MIN {formatter(metric.minimum)}")
        self.max_label.config(text="MAX --" if metric.maximum is None else f"MAX {formatter(metric.maximum)}")


class TextCard(tk.Frame):
    def __init__(self, master, title: str, height: int = 118):
        super().__init__(master, bg=CARD_BG, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.configure(width=260, height=height)
        self.grid_propagate(False)

        self.title_label = tk.Label(
            self, text=title, bg=CARD_BG, fg=MUTED, font=("Bahnschrift SemiBold", 14)
        )
        self.title_label.pack(anchor="w", padx=GAP_LG, pady=(GAP_LG, GAP_SM))

        self.body_label = tk.Label(
            self,
            text="--",
            bg=CARD_BG,
            fg=TEXT,
            justify="left",
            anchor="nw",
            wraplength=220,
            font=("Consolas", 12),
        )
        self.body_label.pack(fill="both", expand=True, padx=GAP_LG, pady=(0, GAP_LG))

    def set_text(self, text: str):
        self.body_label.config(text=text)


class GaugePanel(tk.Frame):
    def __init__(self, master, title: str, unit: str, maximum: float, decimals: int = 0):
        super().__init__(master, bg=CARD_BG, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.title = title
        self.unit = unit
        self.maximum = maximum
        self.decimals = decimals
        self.value = None
        self.minimum = None
        self.maximum_seen = None
        self._last_draw_key = None
        self.canvas = tk.Canvas(self, bg=CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

    def set_value(self, metric: Metric):
        rendered = metric.rendered_value
        if rendered is not None:
            try:
                rendered = float(rendered)
            except (TypeError, ValueError):
                rendered = None
            else:
                if not math.isfinite(rendered):
                    rendered = None
        self.value = rendered
        self.minimum = metric.minimum
        self.maximum_seen = metric.maximum
        self._draw()

    def _fmt(self, value):
        if value is None:
            return "--"
        if self.decimals:
            return f"{value:.{self.decimals}f}"
        return f"{int(round(value))}"

    def _draw(self):
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        value_key = None if self.value is None else round(float(self.value), self.decimals + 1)
        min_key = None if self.minimum is None else round(float(self.minimum), self.decimals + 1)
        max_key = None if self.maximum_seen is None else round(float(self.maximum_seen), self.decimals + 1)
        draw_key = (w, h, value_key, min_key, max_key)
        if draw_key == self._last_draw_key:
            return
        self._last_draw_key = draw_key
        self.canvas.delete("all")
        scale = min(w, h)
        title_size = max(11, min(13, int(scale * 0.060)))
        value_size = max(26, min(36, int(scale * 0.165)))
        unit_size = max(10, min(12, int(scale * 0.048)))
        footer_size = max(9, min(10, int(scale * 0.036)))
        top_pad = max(12, int(h * 0.065))
        self.canvas.create_text(
            w / 2,
            top_pad,
            anchor="n",
            text=self.title,
            width=w - 24,
            fill=MUTED,
            font=("Bahnschrift SemiBold", title_size),
            justify="center",
        )

        cx = w / 2
        cy = h * 0.60
        r = max(40, min(w * 0.39, h * 0.35))
        bbox = (cx - r, cy - r, cx + r, cy + r)
        start = 150
        extent = 240

        arc_width = max(6, int(scale * 0.055))
        marker_width = max(2, int(scale * 0.015))
        self.canvas.create_arc(bbox, start=start, extent=extent, style="arc", width=arc_width, outline=TRACK)
        self.canvas.create_arc(bbox, start=start, extent=extent * 0.72, style="arc", width=marker_width, outline="#C69A21")
        self.canvas.create_arc(bbox, start=start + extent * 0.72, extent=extent * 0.20, style="arc", width=marker_width, outline=WARNING)
        self.canvas.create_arc(bbox, start=start + extent * 0.92, extent=extent * 0.08, style="arc", width=marker_width, outline=DANGER)

        value = 0.0 if self.value is None else float(self.value)
        if not math.isfinite(value):
            value = 0.0
        progress = max(0.0, min(1.0, value / self.maximum)) if self.maximum else 0.0
        if not math.isfinite(progress):
            progress = 0.0
        color = ACCENT if progress < 0.72 else WARNING if progress < 0.92 else DANGER
        if progress > 0.0005:
            self.canvas.create_arc(bbox, start=start, extent=extent * progress, style="arc", width=max(5, arc_width - 2), outline=color)

        self.canvas.create_text(cx, cy - r * 0.01, text=self._fmt(self.value), width=max(80, int(r * 1.70)), fill=color, font=("Bahnschrift Bold", value_size), justify="center")
        if self.unit:
            self.canvas.create_text(cx, cy + r * 0.30, text=self.unit, width=max(80, int(r * 1.52)), fill=MUTED, font=("Bahnschrift SemiBold", unit_size), justify="center")
        self.canvas.create_text(
            12,
            h - 12,
            anchor="sw",
            text=f"Min {self._fmt(self.minimum)}",
            width=max(64, int(w * 0.44)),
            fill="#8690A1",
            font=("Consolas", footer_size),
            justify="left",
        )
        self.canvas.create_text(
            w - 12,
            h - 12,
            anchor="se",
            text=f"Max {self._fmt(self.maximum_seen)}",
            width=max(64, int(w * 0.44)),
            fill="#8690A1",
            font=("Consolas", footer_size),
            justify="right",
        )


class StatPanel(tk.Frame):
    def __init__(self, master, title: str):
        super().__init__(master, bg=CARD_BG, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.title = title
        self.value_text = "--"
        self._last_draw_key = None
        self.canvas = tk.Canvas(self, bg=CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

    def set_text(self, text: str):
        self.value_text = text
        self._draw()

    def _draw(self):
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        draw_key = (w, h, self.title, self.value_text)
        if draw_key == self._last_draw_key:
            return
        self._last_draw_key = draw_key
        self.canvas.delete("all")
        scale = min(w, h)
        title_size = max(11, min(13, int(scale * 0.060)))
        value_size = max(28, min(36, int(scale * 0.170)))
        self.canvas.create_text(w / 2, 12, anchor="n", text=self.title, width=w - 24, fill=MUTED, font=("Bahnschrift SemiBold", title_size), justify="center")
        self.canvas.create_text(w / 2, h / 2, text=self.value_text, fill=ACCENT, width=w - 24, font=("Bahnschrift Bold", value_size), justify="center")


class TrendPanel(tk.Frame):
    def __init__(self, master, title: str):
        super().__init__(master, bg=CARD_BG, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.title = title
        self.series = []
        self._last_draw_key = None
        self.canvas = tk.Canvas(self, bg=CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

    def set_series(self, series):
        self.series = series
        self._draw()

    @staticmethod
    def _series_signature(series):
        signature = []
        for item in series:
            points = item.get("points", [])
            first_point = points[0] if points else None
            last_point = points[-1] if points else None
            mid_point = points[len(points) // 2] if points else None
            signature.append(
                (
                    item.get("label"),
                    item.get("color"),
                    len(points),
                    first_point,
                    mid_point,
                    last_point,
                )
            )
        return tuple(signature)

    @staticmethod
    def _downsample_points(points, max_points: int):
        if len(points) <= max_points:
            return points
        stride = max(1, len(points) // max_points)
        sampled = points[::stride]
        if sampled[-1] != points[-1]:
            sampled.append(points[-1])
        return sampled

    def _draw(self):
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        draw_key = (w, h, self.title, self._series_signature(self.series))
        if draw_key == self._last_draw_key:
            return
        self._last_draw_key = draw_key
        self.canvas.delete("all")
        scale = min(w, h)
        title_size = max(11, min(12, int(scale * 0.040)))
        legend_size = max(8, min(9, int(scale * 0.026)))
        axis_size = max(8, min(9, int(scale * 0.025)))
        self.canvas.create_text(w / 2, 12, anchor="n", text=self.title.title(), width=w - 24, fill=MUTED, font=("Bahnschrift SemiBold", title_size), justify="center")

        left, top, right, bottom = 42, 34, w - 16, h - 34
        plot_w = max(40, right - left)
        plot_h = max(40, bottom - top)

        self.canvas.create_line(left, top, left, bottom, fill=MUTED, width=1)

        for i in range(6):
            y = top + (plot_h * i / 5.0)
            self.canvas.create_line(left, y, right, y, fill=GRID, width=1)
        for i in range(7):
            x = left + (plot_w * i / 6.0)
            self.canvas.create_line(x, top, x, bottom, fill=GRID, width=1)

        all_values = []
        for item in self.series:
            all_values.extend(v for _, v in item["points"])
        if not all_values:
            self.canvas.create_text(w / 2, h / 2 - 8, text="Waiting For Telemetry", fill=MUTED, font=("Bahnschrift SemiBold", max(11, title_size)))
            self.canvas.create_text(w / 2, h / 2 + 12, text="No samples in the current window", fill="#7F8898", font=("Bahnschrift", max(9, axis_size)))
            return

        min_value = min(all_values)
        max_value = max(all_values)
        if math.isclose(min_value, max_value):
            max_value += 1.0

        for i in range(6):
            fraction = 1.0 - (i / 5.0)
            y = top + (plot_h * i / 5.0)
            label_value = min_value + ((max_value - min_value) * fraction)
            self.canvas.create_text(left - 8, y, anchor="e", text=f"{label_value:.1f}", fill=MUTED, font=("Consolas", axis_size))

        max_time = 0.0
        for item in self.series:
            if item["points"]:
                max_time = max(max_time, item["points"][-1][0])
        max_time = max(1e-6, max_time)

        for item in self.series:
            points = self._downsample_points(item["points"], max(60, int(plot_w / 2.5)))
            if len(points) < 2:
                continue
            coords = []
            for sample_time, value in points:
                x = left + plot_w * (max(0.0, min(max_time, sample_time)) / max_time)
                y = bottom - plot_h * ((value - min_value) / (max_value - min_value))
                coords.extend((x, y))
            self.canvas.create_line(
                *coords,
                fill=item["color"],
                width=max(2, int(scale * 0.007)),
                smooth=True,
                splinesteps=20,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )

        legend_x = left
        for item in self.series:
            self.canvas.create_rectangle(legend_x, h - 16, legend_x + 10, h - 6, fill=item["color"], outline=item["color"])
            self.canvas.create_text(legend_x + 16, h - 11, anchor="w", text=item["label"], fill=MUTED, font=("Consolas", legend_size))
            legend_x += max(84, min(126, int(w * 0.18)))


class CustomTrendPanel(TrendPanel):
    def __init__(self, master, title: str, pick_callback):
        super().__init__(master, title)
        self.pick_callback = pick_callback

    def set_series(self, series):
        super().set_series(series)

    @staticmethod
    def _format_axis_value(value: float, decimals: int) -> str:
        if decimals <= 0:
            return f"{int(round(value))}"
        return f"{value:.{decimals}f}"

    @staticmethod
    def _axis_bounds(item):
        values = [value for _, value in item["points"]] or [0.0]
        configured_min = item.get("axis_min", min(values))
        configured_max = item.get("axis_max", max(values))
        data_min = min(values)
        data_max = max(values)
        axis_min = min(configured_min, data_min)
        axis_max = max(configured_max, data_max)
        if math.isclose(axis_min, axis_max):
            axis_max = axis_min + 1.0
        span = axis_max - axis_min
        pad = span * 0.05
        axis_min -= pad
        axis_max += pad
        return axis_min, axis_max

    def _draw(self):
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        draw_key = (w, h, self.title, self._series_signature(self.series))
        if draw_key == self._last_draw_key:
            return
        self._last_draw_key = draw_key
        self.canvas.delete("all")
        scale = min(w, h)
        title_size = max(11, min(12, int(scale * 0.040)))
        legend_size = max(8, min(9, int(scale * 0.026)))
        axis_size = max(8, min(9, int(scale * 0.024)))
        self.canvas.create_text(
            w / 2,
            10,
            anchor="n",
            text=self.title,
            width=w - 20,
            fill=MUTED,
            font=("Bahnschrift SemiBold", title_size),
            justify="center",
        )

        if not self.series:
            self.canvas.create_text(
                w / 2,
                h / 2,
                text="No Metrics Selected",
                fill=MUTED,
                font=("Bahnschrift SemiBold", max(11, title_size + 1)),
            )
            self.canvas.create_text(
                w / 2,
                h / 2 + 18,
                text="Right-click the container to add signals",
                fill="#7F8898",
                font=("Bahnschrift", max(9, legend_size + 1)),
            )
            return

        left_axis_count = (len(self.series) + 1) // 2
        right_axis_count = len(self.series) // 2
        outer_margin = 16
        axis_lane = 72
        axis_clearance = 12
        left = outer_margin + left_axis_count * axis_lane
        right = w - outer_margin - right_axis_count * axis_lane
        top, bottom = 34, h - 34
        plot_w = max(40, right - left)
        plot_h = max(40, bottom - top)

        for i in range(6):
            y = top + (plot_h * i / 5.0)
            self.canvas.create_line(left, y, right, y, fill=GRID, width=1)
        for i in range(7):
            x = left + (plot_w * i / 6.0)
            self.canvas.create_line(x, top, x, bottom, fill=GRID, width=1)

        max_time = 0.0
        for item in self.series:
            if item["points"]:
                max_time = max(max_time, item["points"][-1][0])
        max_time = max(1e-6, max_time)

        for idx, item in enumerate(self.series):
            points = item["points"]
            axis_min, axis_max = self._axis_bounds(item)
            decimals = item.get("decimals", 1)

            side = "left" if idx % 2 == 0 else "right"
            slot = idx // 2
            if side == "left":
                lane_left = outer_margin + slot * axis_lane
                lane_right = lane_left + axis_lane
                axis_x = lane_right - axis_clearance
                label_anchor = "e"
                label_x = axis_x - 8
                label_width = axis_lane - axis_clearance - 12
                label_justify = "right"
            else:
                lane_right = w - outer_margin - slot * axis_lane
                lane_left = lane_right - axis_lane
                axis_x = lane_left + axis_clearance
                label_anchor = "w"
                label_x = axis_x + 8
                label_width = axis_lane - axis_clearance - 12
                label_justify = "left"

            self.canvas.create_line(axis_x, top, axis_x, bottom, fill=item["color"], width=2)
            for fraction in (1.0, 0.75, 0.5, 0.25, 0.0):
                y = bottom - plot_h * fraction
                label_value = axis_min + ((axis_max - axis_min) * fraction)
                self.canvas.create_text(
                    label_x,
                    y,
                    anchor=label_anchor,
                    width=label_width,
                    text=self._format_axis_value(label_value, decimals),
                    fill=item["color"],
                    font=("Consolas", axis_size),
                    justify=label_justify,
                )

            if len(points) < 2:
                continue

            points = self._downsample_points(points, max(60, int(plot_w / 2.5)))

            coords = []
            for sample_time, value in points:
                x = left + plot_w * (max(0.0, min(max_time, sample_time)) / max_time)
                y = bottom - plot_h * ((value - axis_min) / (axis_max - axis_min))
                coords.extend((x, y))
            self.canvas.create_line(
                *coords,
                fill=item["color"],
                width=max(2, int(scale * 0.007)),
                smooth=True,
                splinesteps=20,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )

        legend_x = left
        for item in self.series:
            self.canvas.create_rectangle(legend_x, h - 16, legend_x + 10, h - 6, fill=item["color"], outline=item["color"])
            self.canvas.create_text(legend_x + 16, h - 11, anchor="w", text=item["label"], fill=MUTED, font=("Consolas", legend_size))
            legend_x += max(96, min(156, int(w * 0.21)))


class TachPanel(tk.Frame):
    def __init__(self, master, title: str, maximum: float):
        super().__init__(master, bg=CARD_BG, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.title = title
        self.maximum = maximum
        self.logo_image = None
        self.rpm_value = None
        self._last_draw_key = None
        self.canvas = tk.Canvas(self, bg=CARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

    def set_value(self, metric: Metric):
        self.rpm_value = metric.rendered_value
        self._draw()

    def set_logo(self, logo_image):
        self.logo_image = logo_image
        self._draw()

    def _draw(self):
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        rpm_key = None if self.rpm_value is None else int(round(float(self.rpm_value) / 10.0) * 10)
        logo_key = 1 if self.logo_image is not None else 0
        draw_key = (w, h, self.title, rpm_key, logo_key)
        if draw_key == self._last_draw_key:
            return
        self._last_draw_key = draw_key
        self.canvas.delete("all")
        scale = min(w, h)
        title_size = max(13, min(16, int(scale * 0.048)))
        value_size = max(28, min(40, int(scale * 0.135)))
        top_pad = max(8, int(h * 0.02))
        self.canvas.create_text(w / 2, top_pad + 2, anchor="n", text=self.title, width=w - 24, fill=MUTED, font=("Bahnschrift SemiBold", title_size), justify="center")

        cx = w / 2
        cy = h * 0.58
        r = max(54, min(w * 0.435, h * 0.44))
        bbox = (cx - r, cy - r, cx + r, cy + r)
        arc_width = max(6, int(scale * 0.055))
        start_deg = 210
        sweep_deg = -240

        self.canvas.create_arc(bbox, start=start_deg, extent=sweep_deg, style="arc", width=arc_width, outline=TRACK)

        rpm = 0.0 if self.rpm_value is None else float(self.rpm_value)
        progress = max(0.0, min(1.0, rpm / self.maximum)) if self.maximum else 0.0
        color = ACCENT if progress < 0.80 else WARNING if progress < 0.92 else DANGER
        self.canvas.create_arc(bbox, start=start_deg, extent=sweep_deg * progress, style="arc", width=max(4, arc_width - 3), outline=color)

        major_ticks = 8
        minor_per_major = 4
        inner_major = r - max(18, int(scale * 0.10))
        inner_minor = r - max(12, int(scale * 0.07))
        outer_tick = r - max(3, int(scale * 0.02))
        label_radius = r - max(34, int(scale * 0.16))

        for tick in range(major_ticks * minor_per_major + 1):
            fraction = tick / (major_ticks * minor_per_major)
            angle_deg = start_deg + sweep_deg * fraction
            angle_rad = math.radians(angle_deg)
            is_major = tick % minor_per_major == 0
            inner = inner_major if is_major else inner_minor
            x1 = cx + math.cos(angle_rad) * inner
            y1 = cy - math.sin(angle_rad) * inner
            x2 = cx + math.cos(angle_rad) * outer_tick
            y2 = cy - math.sin(angle_rad) * outer_tick
            tick_color = DANGER if fraction >= 0.84 else MUTED
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=tick_color,
                width=2 if is_major else 1,
                capstyle=tk.ROUND,
            )

            if is_major:
                label_value = int((self.maximum / 1000.0) * fraction)
                lx = cx + math.cos(angle_rad) * label_radius
                ly = cy - math.sin(angle_rad) * label_radius
                self.canvas.create_text(
                    lx,
                    ly,
                    text=str(label_value),
                    fill=MUTED,
                    font=("Bahnschrift SemiBold", max(8, int(scale * 0.034))),
                )

        needle_angle_deg = start_deg + sweep_deg * progress
        needle_angle = math.radians(needle_angle_deg)
        needle_length = r - max(28, int(scale * 0.16))
        tail_length = max(10, int(scale * 0.06))
        nx = cx + math.cos(needle_angle) * needle_length
        ny = cy - math.sin(needle_angle) * needle_length
        tx = cx - math.cos(needle_angle) * tail_length
        ty = cy + math.sin(needle_angle) * tail_length
        self.canvas.create_line(
            tx,
            ty,
            nx,
            ny,
            fill=color,
            width=max(2, int(scale * 0.014)),
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
        )
        self.canvas.create_oval(
            cx - max(7, int(scale * 0.03)),
            cy - max(7, int(scale * 0.03)),
            cx + max(7, int(scale * 0.03)),
            cy + max(7, int(scale * 0.03)),
            fill=TEXT,
            outline=CARD_BORDER,
            width=1,
        )

        if self.logo_image is not None:
            self.canvas.create_image(cx, cy + max(18, int(scale * 0.075)), image=self.logo_image)

        self.canvas.create_text(
            cx,
            h * 0.77,
            text=f"{int(round(rpm)) if self.rpm_value is not None else '--'}",
            width=w - 20,
            fill=TEXT,
            font=("Bahnschrift Bold", value_size),
            justify="center",
        )
        self.canvas.create_text(
            cx,
            h * 0.885,
            text="x1000 rpm",
            width=w - 20,
            fill=MUTED,
            font=("Consolas", max(7, title_size - 2)),
            justify="center",
        )


class DashboardApp:
    HISTORY_LIMIT = 180
    LIVE_REFRESH_MS = 16
    GRAPH_REFRESH_MS = 120

    def __init__(self, root: tk.Tk, state: DashboardState, line_queue: queue.Queue[str], initial_port: str, baudrate: int, initial_demo: bool = False):
        self.root = root
        self.state = state
        self.line_queue = line_queue
        self.port_label = initial_port
        self.baudrate = baudrate
        self.initial_demo = initial_demo
        self.header_logo_image = None
        self.tach_logo_image = None
        self._rx_window_start = time.monotonic()
        self._rx_window_bytes = 0
        self.panel_widgets = {}
        self.panel_handles = {}
        self.panel_delete_buttons = {}
        self.tabs = {}
        self.tab_order = []
        self.current_tab_id = None
        self.tab_buttons = {}
        self.tab_labels = {}
        self._drag_state = None
        self._resize_state = None
        self.edit_mode = False
        self.editor_open = False
        self._tab_rename_entry = None
        self.demo_running = False
        self.demo_after_id = None
        self.demo_rpm = 1800
        self.demo_direction = 1
        self._last_graph_refresh_monotonic = 0.0
        self._last_log_monotonic = 0.0
        self._last_logged_line_count = -1
        self._last_serial_error = ""
        self._tab_signature = ()
        self._secret_buffer = ""
        self._easter_egg_after_id = None
        self._easter_egg_start = 0.0
        self._undo_stack = []
        self._undo_signature = None
        self._max_undo = 30
        self.settings_dialog = None
        self.log_handle = None
        self.log_writer = None
        self.log_path = None
        self.log_format = None
        self.log_columns = []
        self.log_session_started_monotonic = None
        self.log_session_started_wallclock = None
        self.logging_active = False
        self.logging_status_text = "LOG OFF"
        self.latched_alerts = {}
        self.last_alert_text = "NONE"
        self._menu_entry_state_cache = {}
        self._logging_pill_cache = None
        self.persisted_state_path = Path(__file__).resolve().with_name(PERSISTED_STATE_FILE)
        self.profiles_dir = Path(__file__).resolve().with_name(PROFILES_DIR_NAME)
        self.current_profile_name = "Default"
        self.settings_model = self._build_default_settings_model()
        self.critical_limits = {
            "rpm": {"label": "RPM", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "ect": {"label": "Coolant Temp", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "oil_temp": {"label": "Oil Temp", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "oil_pressure": {"label": "Oil Pressure", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "fuel_pressure": {"label": "Fuel Pressure", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "map": {"label": "MAP", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "lambda1": {"label": "Lambda", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "tps": {"label": "TPS", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "aps": {"label": "APS", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "gear": {"label": "Gear", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "wheel_speed": {"label": "Wheel Speed", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
            "throughput": {"label": "Payload Rate", "warn_low": "", "warn_high": "", "crit_low": "", "crit_high": ""},
        }
        self._persisted_tabs_payload = None
        self._persisted_current_tab_index = 0
        self._load_persisted_state()
        if initial_port:
            self.settings_model["connection"]["serial_port"] = initial_port
        self.settings_model["connection"]["baud_rate"] = str(baudrate)
        self.connection_state = "disconnected"
        self.serial_worker = None
        self.port_choices = []
        self._graph_panel_options = {}
        self._frozen_graph_series = {}
        self.critical_limit_vars = {}
        self.histories = {
            "rpm": [],
            "tps": [],
            "aps": [],
            "oil_temp": [],
            "ect": [],
            "oil_pressure": [],
            "fuel_pressure": [],
            "map": [],
            "wheel_speed": [],
            "gear": [],
            "lambda1": [],
            "throughput": [],
        }

        self.root.title("HaLow CAN Dashboard")
        self.root.configure(bg=BACKGROUND)
        self.root.geometry("1600x920")
        self.root.minsize(1400, 860)
        self.root.protocol("WM_DELETE_WINDOW", self._on_root_close)
        self._apply_dark_title_bar(self.root)

        outer = tk.Frame(root, bg=BACKGROUND)
        outer.pack(fill="both", expand=True, padx=12, pady=12)
        self.outer = outer

        header = tk.Frame(outer, bg=BACKGROUND)
        header.pack(fill="x", pady=(0, GAP_SM))
        self._load_logo_image()

        self.halow_pill = tk.Label(
            header,
            text="HALOW -- Mbps",
            bg=CARD_BG,
            fg=MUTED,
            font=("Bahnschrift", 9),
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
        )
        self.halow_pill.pack(side="right")

        self.throughput_pill = tk.Label(
            header,
            text="PAYLOAD -- kbps",
            bg=CARD_BG,
            fg=ACCENT,
            font=("Bahnschrift", 9),
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
        )
        self.throughput_pill.pack(side="right", padx=(0, 8))

        header_strip = tk.Frame(header, bg=CARD_BG, highlightthickness=1, highlightbackground=CARD_BORDER, height=34)
        header_strip.pack(side="left", fill="x", expand=True, anchor="w", padx=(0, 8))
        header_strip.pack_propagate(False)
        self.header_strip = header_strip
        header_text_font = ("Bahnschrift", 10)
        header_status_font = ("Bahnschrift", 9)

        def pack_header_item(widget):
            if header_strip.winfo_children():
                tk.Frame(header_strip, bg=CARD_BORDER, width=1).pack(side="left", fill="y")
            widget.pack(side="left", padx=0, pady=0)

        self.header_style = ttk.Style(root)
        try:
            self.header_style.theme_use("clam")
        except tk.TclError:
            pass
        self.header_style.configure(
            "Header.TCombobox",
            fieldbackground=CARD_BG,
            background=CARD_BG,
            foreground=TEXT,
            borderwidth=1,
            relief="flat",
            arrowcolor=ACCENT,
            insertcolor=TEXT,
            lightcolor=CARD_BORDER,
            darkcolor=CARD_BORDER,
            bordercolor=CARD_BORDER,
            padding=2,
        )
        self.header_style.map(
            "Header.TCombobox",
            fieldbackground=[("readonly", CARD_BG)],
            background=[("readonly", CARD_BG)],
            foreground=[("readonly", TEXT)],
        )

        self.profile_pill = tk.Label(
            header_strip,
            text="PROFILE: Default",
            bg=CARD_BG,
            fg=ACCENT,
            font=header_status_font,
            padx=10,
            pady=8,
        )
        pack_header_item(self.profile_pill)
        self._refresh_profile_pill()

        self.profiles_menu_button = tk.Menubutton(
            header_strip,
            text="Profiles",
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            font=header_text_font,
            padx=10,
            pady=8,
            cursor="hand2",
            direction="below",
        )
        self.profiles_menu = tk.Menu(
            self.profiles_menu_button,
            tearoff=0,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BORDER,
            activeforeground=TEXT,
        )
        self.profiles_menu.add_command(label="Open Profile Manager", command=self._open_profile_manager)
        self.profiles_menu.add_command(label="Save Over Current", command=lambda: self._save_profile(self.current_profile_name))
        self.profiles_menu.add_command(label="Save Profile As", command=self._save_profile_as)
        self.profiles_menu_button.config(menu=self.profiles_menu)
        pack_header_item(self.profiles_menu_button)
        self._bind_hover(self.profiles_menu_button, CARD_BG, CARD_HOVER, TEXT, TEXT)

        self.settings_button = tk.Button(
            header_strip,
            text="Settings",
            command=self._open_settings_dialog,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            font=header_text_font,
            padx=10,
            pady=8,
            cursor="hand2",
        )
        pack_header_item(self.settings_button)
        self._bind_hover(self.settings_button, CARD_BG, CARD_HOVER, TEXT, TEXT)

        self.session_menu_button = tk.Menubutton(
            header_strip,
            text="Session",
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            font=header_text_font,
            padx=10,
            pady=8,
            cursor="hand2",
            direction="below",
        )
        self.session_menu = tk.Menu(
            self.session_menu_button,
            tearoff=0,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BORDER,
            activeforeground=TEXT,
        )
        self.session_menu.add_command(label="Reset Min/Max", command=self._reset_metric_bounds)
        self.session_menu.add_command(label="Ack Alerts", command=self._acknowledge_alerts, state="disabled")
        self.session_menu.add_separator()
        self.session_menu.add_command(label="Duplicate Current Tab", command=self._duplicate_current_tab)
        self.session_menu.add_command(label="Reset Current Tab Layout", command=self._reset_current_tab)
        self.session_menu.add_command(label="Reset LIVE Tab", command=lambda: self._reset_named_tab("LIVE"))
        self.session_menu.add_command(label="Reset LOGGING Tab", command=lambda: self._reset_named_tab("LOGGING"))
        self.session_menu.add_command(label="Reset All Tabs", command=self._reset_all_tabs)
        self.session_menu.add_separator()
        self.session_menu.add_command(label="Clear All Graphs", command=self._clear_all_graphs)
        self.session_menu.add_separator()
        self.session_menu.add_command(label="Save Workspace As", command=self._export_workspace)
        self.session_menu.add_command(label="Load Workspace", command=self._import_workspace)
        self.session_menu_button.config(menu=self.session_menu)
        pack_header_item(self.session_menu_button)
        self._bind_hover(self.session_menu_button, CARD_BG, CARD_HOVER, TEXT, TEXT)

        self.logging_menu_button = tk.Menubutton(
            header_strip,
            text="Logging",
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            font=header_text_font,
            padx=10,
            pady=8,
            cursor="hand2",
            direction="below",
        )
        self.logging_menu = tk.Menu(
            self.logging_menu_button,
            tearoff=0,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BORDER,
            activeforeground=TEXT,
        )
        self.logging_menu.add_command(label="Start Logging", command=self._start_logging)
        self.logging_menu.add_command(label="Stop Logging", command=self._stop_logging, state="disabled")
        self.logging_menu.add_command(label="Open Log Folder", command=self._open_log_folder)
        self.logging_menu.add_separator()
        self.logging_menu.add_command(label="Start Demo", command=self._start_demo_mode)
        self.logging_menu.add_command(label="Stop Demo", command=self._stop_demo_mode, state="disabled")
        self.logging_menu_button.config(menu=self.logging_menu)
        pack_header_item(self.logging_menu_button)
        self._bind_hover(self.logging_menu_button, CARD_BG, CARD_HOVER, TEXT, TEXT)

        self.connect_button = tk.Button(
            header_strip,
            text="Connect",
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_HOVER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            font=header_text_font,
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._toggle_connection,
        )
        pack_header_item(self.connect_button)
        self._bind_hover(self.connect_button, CARD_BG, CARD_HOVER, TEXT, TEXT)

        self.port_var = tk.StringVar(value=self.settings_model["connection"].get("serial_port", self.port_label))
        self.port_combo = ttk.Combobox(
            header_strip,
            textvariable=self.port_var,
            state="readonly",
            width=11,
            style="Header.TCombobox",
        )
        pack_header_item(self.port_combo)
        self.port_combo.bind("<<ComboboxSelected>>", self._handle_port_selected, add="+")

        self.refresh_ports_button = tk.Button(
            header_strip,
            text="↻",
            bg=CARD_BG,
            fg=ACCENT,
            activebackground=CARD_HOVER,
            activeforeground=ACCENT,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            font=("Bahnschrift", 11),
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._refresh_port_choices,
        )
        pack_header_item(self.refresh_ports_button)
        self._bind_hover(self.refresh_ports_button, CARD_BG, CARD_HOVER, ACCENT, ACCENT)

        self.logging_pill = tk.Label(
            header_strip,
            text="LOG OFF",
            bg=CARD_BG,
            fg=MUTED,
            font=header_status_font,
            padx=10,
            pady=8,
        )
        pack_header_item(self.logging_pill)

        self.last_alert_pill = tk.Label(
            header_strip,
            text="ALERT: NONE",
            bg=CARD_BG,
            fg=MUTED,
            font=header_status_font,
            padx=10,
            pady=8,
        )
        pack_header_item(self.last_alert_pill)

        self.status_pill = tk.Label(
            header_strip,
            text="OFFLINE",
            bg=ACCENT_2,
            fg=TEXT,
            font=header_status_font,
            padx=10,
            pady=8,
        )
        pack_header_item(self.status_pill)


        self.header_divider = tk.Frame(outer, bg=CARD_BORDER, height=1)
        self.header_divider.pack(fill="x", pady=(0, GAP_SM))

        self.critical_bar = tk.Label(
            outer,
            text="",
            bg=DANGER,
            fg=TEXT,
            font=("Bahnschrift Bold", 12),
            padx=12,
            pady=6,
        )

        self.tab_bar = tk.Frame(outer, bg=BACKGROUND)
        self.tab_bar.pack(fill="x", pady=(0, 10))

        self.easter_egg_label = tk.Label(
            outer,
            text="RANGE MOGGED",
            bg=BACKGROUND,
            fg=ACCENT,
            font=("Bahnschrift Bold", 48),
            justify="center",
        )

        self.main_body = tk.Frame(outer, bg=BACKGROUND)
        self.main_body.pack(fill="both", expand=True)

        self.dashboard_view = tk.Canvas(self.main_body, bg=BACKGROUND, highlightthickness=0)
        self.dashboard_view.pack(side="left", fill="both", expand=True)
        self.dashboard = tk.Frame(self.dashboard_view, bg=BACKGROUND)
        self.dashboard_window = self.dashboard_view.create_window((0, 0), window=self.dashboard, anchor="nw")
        self.dashboard_view.bind("<Configure>", self._on_dashboard_resize)

        self.drawer_toggle = tk.Button(
            self.main_body,
            text="◀",
            command=self._toggle_editor_drawer,
            bg=CARD_BG,
            fg=ACCENT,
            activebackground=CARD_BG,
            activeforeground=ACCENT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            font=("Bahnschrift Bold", 12),
            width=2,
            cursor="hand2",
        )
        self.drawer_toggle.pack(side="left", fill="y", padx=(8, 0))

        self.editor_drawer = tk.Frame(self.main_body, bg=CARD_BG, width=0, highlightthickness=1, highlightbackground=CARD_BORDER)
        self.editor_canvas = tk.Canvas(self.editor_drawer, bg=CARD_BG, highlightthickness=0, width=290)
        self.editor_scrollbar = tk.Scrollbar(self.editor_drawer, orient="vertical", command=self.editor_canvas.yview)
        self.editor_canvas.configure(yscrollcommand=self.editor_scrollbar.set)
        self.editor_content = tk.Frame(self.editor_canvas, bg=CARD_BG)
        self.editor_window = self.editor_canvas.create_window((0, 0), window=self.editor_content, anchor="nw")
        self.editor_content.bind("<Configure>", self._on_editor_content_configure)
        self.editor_canvas.bind("<Configure>", self._on_editor_canvas_configure)
        self.editor_canvas.bind("<MouseWheel>", self._on_drawer_mousewheel)

        self.edit_button = tk.Button(
            self.editor_content,
            text="Enable Edit Mode",
            command=self._toggle_edit_mode,
            bg=ACCENT_2,
            fg=TEXT,
            activebackground=ACCENT_2,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            font=("Bahnschrift SemiBold", 11),
            padx=10,
            pady=8,
            cursor="hand2",
        )
        self.drawer_live_title = tk.Label(self.editor_content, text="Live", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 13))
        self.drawer_live = tk.Frame(self.editor_content, bg=CARD_BG)
        self.drawer_graph_title = tk.Label(self.editor_content, text="Graphs", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 13))
        self.drawer_graphs = tk.Frame(self.editor_content, bg=CARD_BG)
        for widget in (
            self.editor_canvas,
            self.editor_content,
            self.edit_button,
            self.drawer_live_title,
            self.drawer_live,
            self.drawer_graph_title,
            self.drawer_graphs,
        ):
            widget.bind("<MouseWheel>", self._on_drawer_mousewheel)

        self.wheel_gauge = GaugePanel(self.dashboard, "Wheel Speed", "RAW", maximum=220)
        self.tps_gauge = GaugePanel(self.dashboard, "TPS", "%", maximum=100)
        self.aps_gauge = GaugePanel(self.dashboard, "APS", "RAW", maximum=100)
        self.gear_stat = StatPanel(self.dashboard, "Gear")
        self.oil_temp_gauge = GaugePanel(self.dashboard, "Oil Temp", "C", maximum=140)
        self.coolant_gauge = GaugePanel(self.dashboard, "Coolant Temp", "C", maximum=130)

        self.lambda_gauge = GaugePanel(self.dashboard, "Lambda", "raw", maximum=20.0, decimals=1)
        self.map_gauge = GaugePanel(self.dashboard, "MAP", "raw", maximum=200)
        self.fuel_pressure_gauge = GaugePanel(self.dashboard, "Fuel Pressure", "raw", maximum=200)
        self.oil_pressure_gauge = GaugePanel(self.dashboard, "Oil Pressure", "raw", maximum=200)

        self.rpm_trend = TrendPanel(self.dashboard, "RPM Graph")
        self.wheel_trend = TrendPanel(self.dashboard, "Wheel Speed Graph")
        self.tps_trend = TrendPanel(self.dashboard, "TPS Graph")
        self.aps_trend = TrendPanel(self.dashboard, "APS Graph")
        self.gear_trend = TrendPanel(self.dashboard, "Gear Graph")
        self.oil_temp_trend_single = TrendPanel(self.dashboard, "Oil Temp Graph")
        self.coolant_trend = TrendPanel(self.dashboard, "Coolant Graph")
        self.throughput_trend = TrendPanel(self.dashboard, "Payload Rate Graph")
        self.lambda_trend = TrendPanel(self.dashboard, "Lambda Graph")
        self.fuel_pressure_trend_single = TrendPanel(self.dashboard, "Fuel Pressure Graph")
        self.oil_pressure_trend_single = TrendPanel(self.dashboard, "Oil Pressure Graph")
        self.map_trend = TrendPanel(self.dashboard, "MAP Graph")
        self.throttle_trend = TrendPanel(self.dashboard, "Throttle Graph")
        self.temp_trend = TrendPanel(self.dashboard, "Temp Graph")
        self.pressure_trend = TrendPanel(self.dashboard, "Pressure Graph")
        self.custom_trend_panels = {}
        for index, panel_name in enumerate(CUSTOM_GRAPH_PANEL_NAMES, start=1):
            title = "Custom Graph" if index == 1 else f"Custom Graph {index}"
            widget = CustomTrendPanel(self.dashboard, title, lambda name=panel_name: self._configure_custom_graph(name))
            self.custom_trend_panels[panel_name] = widget
            setattr(self, panel_name, widget)
        self.rpm_tach = TachPanel(self.dashboard, "Engine Speed", RPM_MAX)
        self.rpm_tach.set_logo(self.tach_logo_image)
        self._register_panel("wheel_gauge", self.wheel_gauge)
        self._register_panel("tps_gauge", self.tps_gauge)
        self._register_panel("aps_gauge", self.aps_gauge)
        self._register_panel("gear_stat", self.gear_stat)
        self._register_panel("oil_temp_gauge", self.oil_temp_gauge)
        self._register_panel("coolant_gauge", self.coolant_gauge)
        self._register_panel("lambda_gauge", self.lambda_gauge)
        self._register_panel("map_gauge", self.map_gauge)
        self._register_panel("fuel_pressure_gauge", self.fuel_pressure_gauge)
        self._register_panel("oil_pressure_gauge", self.oil_pressure_gauge)
        self._register_panel("rpm_trend", self.rpm_trend)
        self._register_panel("wheel_trend", self.wheel_trend)
        self._register_panel("tps_trend", self.tps_trend)
        self._register_panel("aps_trend", self.aps_trend)
        self._register_panel("gear_trend", self.gear_trend)
        self._register_panel("oil_temp_trend_single", self.oil_temp_trend_single)
        self._register_panel("coolant_trend", self.coolant_trend)
        self._register_panel("throughput_trend", self.throughput_trend)
        self._register_panel("lambda_trend", self.lambda_trend)
        self._register_panel("fuel_pressure_trend_single", self.fuel_pressure_trend_single)
        self._register_panel("oil_pressure_trend_single", self.oil_pressure_trend_single)
        self._register_panel("map_trend", self.map_trend)
        self._register_panel("throttle_trend", self.throttle_trend)
        self._register_panel("temp_trend", self.temp_trend)
        self._register_panel("pressure_trend", self.pressure_trend)
        for panel_name, widget in self.custom_trend_panels.items():
            self._register_panel(panel_name, widget)
        self._register_panel("rpm_tach", self.rpm_tach)

        self._initialize_tabs()
        self.logging_active = bool(self.settings_model["logging"].get("enabled") and self.settings_model["logging"].get("auto_start"))
        self._update_logging_controls()
        self._refresh_port_choices()
        self._update_connection_controls()
        default_window = self._default_graph_window()
        self._graph_panel_options = {
            panel_name: {"paused": False, "window_s": default_window}
            for panel_name, meta in PANEL_DEFS.items()
            if meta["section"] == "graphs"
        }

        self.root.after(20, self._poll_lines)
        self.root.after(self.LIVE_REFRESH_MS, self._refresh)
        self.root.bind_all("<KeyPress>", self._handle_secret_keypress, add="+")
        self.root.bind_all("<Control-z>", self._handle_undo_shortcut, add="+")
        if initial_demo:
            self._start_demo_mode()
        elif self.settings_model["connection"].get("auto_connect", True):
            self._connect_serial()

    def _register_panel(self, name: str, widget: tk.Widget):
        self.panel_widgets[name] = widget
        self._bind_panel_drag(widget, name)
        handle = tk.Frame(self.dashboard, bg=ACCENT, width=14, height=14, cursor="arrow") # cross platform cursor
        handle.bind("<ButtonPress-1>", lambda event, panel=name: self._start_resize(event, panel))
        handle.bind("<B1-Motion>", lambda event, panel=name: self._resize_panel(event, panel))
        handle.bind("<ButtonRelease-1>", self._end_drag)
        self.panel_handles[name] = handle
        delete_button = tk.Button(
            self.dashboard,
            text="×",
            command=lambda panel=name: self._hide_panel(panel),
            bg=ACCENT_2,
            fg=TEXT,
            activebackground=ACCENT_2,
            activeforeground=TEXT,
            relief="flat",
            font=("Bahnschrift Bold", 10),
            padx=0,
            pady=0,
            cursor="hand2",
        )
        self.panel_delete_buttons[name] = delete_button

    def _bind_panel_drag(self, widget: tk.Widget, panel_name: str):
        widget.bind("<ButtonPress-1>", lambda event, panel=panel_name: self._start_drag(event, panel), add="+")
        widget.bind("<B1-Motion>", lambda event, panel=panel_name: self._drag_panel(event, panel), add="+")
        widget.bind("<ButtonRelease-1>", self._end_drag, add="+")
        widget.bind("<Button-3>", lambda event, panel=panel_name: self._show_panel_menu(event, panel), add="+")
        for child in widget.winfo_children():
            self._bind_panel_drag(child, panel_name)

    def _load_persisted_state(self):
        try:
            if not self.persisted_state_path.exists():
                return
            payload = json.loads(self.persisted_state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return

        settings_payload = payload.get("settings")
        if isinstance(settings_payload, dict):
            self._merge_settings_model(self.settings_model, settings_payload)
        profile_name = payload.get("profile_name")
        if isinstance(profile_name, str) and profile_name.strip():
            self.current_profile_name = profile_name.strip()

        critical_payload = payload.get("critical_limits")
        if isinstance(critical_payload, dict):
            for metric_key, config in critical_payload.items():
                if metric_key in self.critical_limits and isinstance(config, dict):
                    if "low" in config:
                        self.critical_limits[metric_key]["crit_low"] = str(config["low"])
                    if "high" in config:
                        self.critical_limits[metric_key]["crit_high"] = str(config["high"])
                    for field_name in ("warn_low", "warn_high", "crit_low", "crit_high"):
                        if field_name in config:
                            self.critical_limits[metric_key][field_name] = str(config[field_name])

        tabs_payload = payload.get("tabs")
        if isinstance(tabs_payload, list):
            self._persisted_tabs_payload = tabs_payload
            try:
                self._persisted_current_tab_index = max(0, int(payload.get("current_tab_index", 0)))
            except (TypeError, ValueError):
                self._persisted_current_tab_index = 0

    def _merge_settings_model(self, target: dict, source: dict):
        for key, value in source.items():
            if key not in target:
                continue
            if isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_settings_model(target[key], value)
            else:
                target[key] = value

    def _default_custom_graph_titles(self):
        return {
            panel_name: ("Custom Graph" if index == 1 else f"Custom Graph {index}")
            for index, panel_name in enumerate(CUSTOM_GRAPH_PANEL_NAMES, start=1)
        }

    def _default_custom_graph_config(self):
        return {panel_name: [] for panel_name in CUSTOM_GRAPH_PANEL_NAMES}

    def _workspace_snapshot_payload(self):
        return {
            "profile_name": self.current_profile_name,
            "settings": json.loads(json.dumps(self.settings_model)),
            "critical_limits": json.loads(json.dumps(self.critical_limits)),
            "tabs": json.loads(json.dumps(self._serialize_tabs_payload())),
            "current_tab_index": max(0, self.tab_order.index(self.current_tab_id)) if self.current_tab_id in self.tab_order else 0,
        }

    def _push_undo_state(self):
        snapshot = self._workspace_snapshot_payload()
        signature = json.dumps(snapshot, sort_keys=True)
        if signature == self._undo_signature:
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._max_undo:
            self._undo_stack.pop(0)
        self._undo_signature = signature

    def _handle_undo_shortcut(self, _event=None):
        focused = self.root.focus_get()
        if focused is not None and focused.winfo_class() in {"Entry", "Text", "TEntry", "Spinbox", "TCombobox"}:
            return
        self._undo_last_action()
        return "break"

    def _undo_last_action(self):
        if not self._undo_stack:
            return
        snapshot = self._undo_stack.pop()
        self._apply_workspace_payload(snapshot)
        self._undo_signature = json.dumps(self._workspace_snapshot_payload(), sort_keys=True)

    def _apply_workspace_payload(self, payload: dict):
        self.current_profile_name = str(payload.get("profile_name", self.current_profile_name or "Default")).strip() or "Default"
        self.settings_model = self._build_default_settings_model()
        self._merge_settings_model(self.settings_model, payload.get("settings", {}))
        for metric_key, bounds in self.critical_limits.items():
            bounds["warn_low"] = ""
            bounds["warn_high"] = ""
            bounds["crit_low"] = ""
            bounds["crit_high"] = ""
        critical_payload = payload.get("critical_limits", {})
        if isinstance(critical_payload, dict):
            for metric_key, config in critical_payload.items():
                if metric_key in self.critical_limits and isinstance(config, dict):
                    for field_name in ("warn_low", "warn_high", "crit_low", "crit_high"):
                        if field_name in config:
                            self.critical_limits[metric_key][field_name] = str(config[field_name])
        self._persisted_tabs_payload = payload.get("tabs") if isinstance(payload.get("tabs"), list) else None
        try:
            self._persisted_current_tab_index = max(0, int(payload.get("current_tab_index", 0)))
        except (TypeError, ValueError):
            self._persisted_current_tab_index = 0
        if not self._restore_tabs_from_persistence():
            self.tabs.clear()
            self.tab_order.clear()
            self.current_tab_id = None
            self._seed_default_tabs()
        self.logging_active = bool(self.settings_model["logging"].get("enabled") and self.settings_model["logging"].get("auto_start"))
        self._close_log_session()
        self._update_logging_controls()
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()
        self._refresh_profile_pill()
        self._save_persisted_state()

    def _sanitize_layout_payload(self, payload):
        layout = self._default_layout_copy()
        if not isinstance(payload, dict):
            return layout
        for panel_name, default_spec in layout.items():
            incoming = payload.get(panel_name)
            if not isinstance(incoming, dict):
                continue
            spec = default_spec.copy()
            for field_name in ("x", "y", "w", "h"):
                try:
                    spec[field_name] = float(incoming.get(field_name, spec[field_name]))
                except (TypeError, ValueError):
                    pass
            spec["x"] = max(0.0, min(1.0, spec["x"]))
            spec["y"] = max(0.0, min(1.0, spec["y"]))
            spec["w"] = max(0.05, min(1.0, spec["w"]))
            spec["h"] = max(0.05, min(1.0, spec["h"]))
            spec["visible"] = bool(incoming.get("visible", spec.get("visible", False)))
            layout[panel_name] = spec
        return layout

    def _apply_core_tab_layout_migrations(self, tab_name: str, raw_layout_payload, layout: dict):
        if not isinstance(layout, dict):
            return layout
        payload = raw_layout_payload if isinstance(raw_layout_payload, dict) else {}
        if tab_name.upper() == "LIVE" and "map_gauge" not in payload and "map_gauge" in DEFAULT_PANEL_LAYOUTS:
            layout["map_gauge"] = DEFAULT_PANEL_LAYOUTS["map_gauge"].copy()
            layout["map_gauge"]["visible"] = True
        return layout

    def _sanitize_custom_graphs_payload(self, payload):
        cleaned = self._default_custom_graph_config()
        if not isinstance(payload, dict):
            return cleaned
        for panel_name in CUSTOM_GRAPH_PANEL_NAMES:
            entries = payload.get(panel_name, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                key = entry.get("key")
                color = entry.get("color")
                if key in GRAPH_METRIC_OPTIONS and isinstance(color, str) and color.strip():
                    cleaned[panel_name].append({"key": key, "color": color})
        return cleaned

    def _sanitize_custom_graph_titles_payload(self, payload):
        cleaned = self._default_custom_graph_titles()
        if not isinstance(payload, dict):
            return cleaned
        for panel_name in CUSTOM_GRAPH_PANEL_NAMES:
            title = payload.get(panel_name)
            if isinstance(title, str) and title.strip():
                cleaned[panel_name] = title.strip()
        return cleaned

    def _restore_tabs_from_persistence(self):
        if not self._persisted_tabs_payload:
            return False

        self.tabs.clear()
        self.tab_order.clear()
        self.current_tab_id = None

        for index, tab_payload in enumerate(self._persisted_tabs_payload, start=1):
            if not isinstance(tab_payload, dict):
                continue
            name = str(tab_payload.get("name", f"TAB{index}")).strip() or f"TAB{index}"
            tab_id = f"tab_{index}"
            layout = self._sanitize_layout_payload(tab_payload.get("layout"))
            layout = self._apply_core_tab_layout_migrations(name, tab_payload.get("layout"), layout)
            self.tabs[tab_id] = {
                "name": name,
                "layout": layout,
                "custom_graphs": self._sanitize_custom_graphs_payload(tab_payload.get("custom_graphs")),
                "custom_graph_titles": self._sanitize_custom_graph_titles_payload(tab_payload.get("custom_graph_titles")),
            }
            self.tab_order.append(tab_id)

        if not self.tab_order:
            return False

        selected_index = min(self._persisted_current_tab_index, len(self.tab_order) - 1)
        self.current_tab_id = self.tab_order[selected_index]
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()
        return True

    def _serialize_tabs_payload(self):
        tabs_payload = []
        for tab_id in self.tab_order:
            tab = self.tabs.get(tab_id)
            if not tab:
                continue
            tabs_payload.append(
                {
                    "name": tab.get("name", tab_id),
                    "layout": tab.get("layout", {}),
                    "custom_graphs": tab.get("custom_graphs", self._default_custom_graph_config()),
                    "custom_graph_titles": tab.get("custom_graph_titles", self._default_custom_graph_titles()),
                }
            )
        return tabs_payload

    def _save_persisted_state(self):
        payload = {
            "profile_name": self.current_profile_name,
            "settings": self.settings_model,
            "critical_limits": {
                metric_key: {
                    "warn_low": bounds.get("warn_low", ""),
                    "warn_high": bounds.get("warn_high", ""),
                    "crit_low": bounds.get("crit_low", ""),
                    "crit_high": bounds.get("crit_high", ""),
                }
                for metric_key, bounds in self.critical_limits.items()
            },
            "tabs": self._serialize_tabs_payload(),
            "current_tab_index": max(0, self.tab_order.index(self.current_tab_id)) if self.current_tab_id in self.tab_order else 0,
        }
        try:
            self.persisted_state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _refresh_profile_pill(self):
        if hasattr(self, "profile_pill"):
            self.profile_pill.config(text=f"PROFILE: {self.current_profile_name}")

    def _apply_dark_title_bar(self, window):
        def colorref(hex_color: str) -> ctypes.c_int:
            value = hex_color.lstrip("#")
            red = int(value[0:2], 16)
            green = int(value[2:4], 16)
            blue = int(value[4:6], 16)
            return ctypes.c_int(red | (green << 8) | (blue << 16))

        def apply_once():
            try:
                window.update_idletasks()
                hwnd = int(window.winfo_id())
                enabled = ctypes.c_int(1)
                for attribute in (20, 19):
                    try:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd,
                            attribute,
                            ctypes.byref(enabled),
                            ctypes.sizeof(enabled),
                        )
                    except Exception:
                        pass

                caption_color = colorref(BACKGROUND)
                text_color = colorref(TEXT)
                border_color = colorref(CARD_BORDER)
                for attribute, value in ((35, caption_color), (36, text_color), (34, border_color)):
                    try:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd,
                            attribute,
                            ctypes.byref(value),
                            ctypes.sizeof(value),
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        apply_once()
        try:
            window.after(50, apply_once)
            window.after(250, apply_once)
        except Exception:
            pass

    def _bind_hover(self, widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
        def on_enter(_event=None):
            kwargs = {"bg": hover_bg}
            if hover_fg is not None:
                kwargs["fg"] = hover_fg
            try:
                widget.config(**kwargs)
            except tk.TclError:
                pass

        def on_leave(_event=None):
            kwargs = {"bg": normal_bg}
            if normal_fg is not None:
                kwargs["fg"] = normal_fg
            try:
                widget.config(**kwargs)
            except tk.TclError:
                pass

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")

    def _available_serial_ports(self):
        discovered = []
        if list_ports is not None:
            try:
                discovered = [port.device for port in list_ports.comports()]
            except Exception:
                discovered = []
        current = str(self.settings_model.get("connection", {}).get("serial_port", "")).strip()
        if current and current not in discovered:
            discovered.append(current)
        if not discovered:
            discovered = [current or self.port_label or "COM12"]
        return sorted(discovered)

    def _refresh_port_choices(self):
        self.port_choices = self._available_serial_ports()
        if hasattr(self, "port_combo"):
            self.port_combo.configure(values=self.port_choices)
            current = self.port_var.get().strip()
            if current not in self.port_choices and self.port_choices:
                self.port_var.set(self.port_choices[0])
        return self.port_choices

    def _handle_port_selected(self, _event=None):
        selected = self.port_var.get().strip()
        if selected:
            self.settings_model["connection"]["serial_port"] = selected
            self.port_label = selected
            self._save_persisted_state()

    def _toggle_connection(self):
        if self.serial_worker is not None:
            self._disconnect_serial()
        else:
            self._connect_serial()

    def _connect_serial(self):
        if self.initial_demo or self.demo_running:
            return
        port = self.port_var.get().strip() or self.settings_model["connection"].get("serial_port", "").strip()
        if not port:
            return
        try:
            baudrate = int(str(self.settings_model["connection"].get("baud_rate", self.baudrate)).strip())
        except ValueError:
            baudrate = self.baudrate
        self._disconnect_serial(save_state=False)
        self.settings_model["connection"]["serial_port"] = port
        self.settings_model["connection"]["baud_rate"] = str(baudrate)
        self.port_label = port
        self.connection_state = "connecting"
        self._last_serial_error = ""
        self.state.last_update_monotonic = 0.0
        self.serial_worker = SerialWorker(port, baudrate, self.line_queue, False)
        self.serial_worker.start()
        self._update_connection_controls()
        self._save_persisted_state()

    def _disconnect_serial(self, save_state: bool = True):
        if self.serial_worker is not None:
            self.serial_worker.stop()
            self.serial_worker = None
        self.connection_state = "disconnected"
        self.state.last_update_monotonic = 0.0
        self._last_serial_error = ""
        self._update_connection_controls()
        if save_state:
            self._save_persisted_state()

    def _update_connection_controls(self):
        if not hasattr(self, "connect_button"):
            return
        connected = self.serial_worker is not None
        self.connect_button.config(
            text="Disconnect" if connected else "Connect",
            fg=WARNING if connected else TEXT,
        )

    def _sanitize_profile_name(self, name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9 _-]+", "", (name or "").strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:40]

    def _profile_path(self, profile_name: str) -> Path:
        safe_name = self._sanitize_profile_name(profile_name).replace(" ", "_")
        return self.profiles_dir / f"{safe_name}.json"

    def _available_profiles(self):
        if not self.profiles_dir.exists():
            return []
        profiles = []
        for path in sorted(self.profiles_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                label = str(payload.get("profile_name", path.stem.replace("_", " "))).strip() or path.stem.replace("_", " ")
            except (OSError, json.JSONDecodeError):
                label = path.stem.replace("_", " ")
            profiles.append((label, path))
        return profiles

    def _save_profile(self, profile_name: str):
        normalized = self._sanitize_profile_name(profile_name)
        if not normalized:
            return False
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        previous = self.current_profile_name
        self.current_profile_name = normalized
        payload = self._workspace_snapshot_payload()
        self.current_profile_name = previous
        payload["profile_name"] = normalized
        try:
            self._profile_path(normalized).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            return False
        self.current_profile_name = normalized
        self._refresh_profile_pill()
        self._save_persisted_state()
        return True

    def _save_profile_as(self, initial_name: str | None = None):
        proposed = initial_name or self.current_profile_name or "Profile"
        name = simpledialog.askstring("Save Profile", "Profile name:", initialvalue=proposed, parent=self.root)
        if not name:
            return False
        self._push_undo_state()
        return self._save_profile(name)

    def _load_profile(self, profile_name: str):
        path = self._profile_path(profile_name)
        if not path.exists():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        self._push_undo_state()
        self._apply_workspace_payload(payload)
        return True

    def _delete_profile(self, profile_name: str):
        path = self._profile_path(profile_name)
        if not path.exists():
            return False
        try:
            path.unlink()
        except OSError:
            return False
        if self.current_profile_name == profile_name:
            self.current_profile_name = "Default"
            self._refresh_profile_pill()
            self._save_persisted_state()
        return True

    def _open_profile_manager(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Profiles")
        dialog.configure(bg=CARD_BG)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._apply_dark_title_bar(dialog)

        tk.Label(dialog, text="Saved Profiles", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 14)).pack(anchor="w", padx=14, pady=(14, 8))

        body = tk.Frame(dialog, bg=CARD_BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        listbox = tk.Listbox(
            body,
            width=34,
            height=10,
            bg=BACKGROUND,
            fg=TEXT,
            selectbackground=ACCENT_2,
            selectforeground=TEXT,
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            font=("Bahnschrift", 11),
            activestyle="none",
            relief="flat",
        )
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(body, orient="vertical", command=listbox.yview, bg=CARD_BG, troughcolor=BACKGROUND, activebackground=CARD_BORDER)
        scrollbar.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scrollbar.set)

        profile_names = []

        def refresh_profiles(select_name: str | None = None):
            nonlocal profile_names
            profile_names = [label for label, _ in self._available_profiles()]
            listbox.delete(0, tk.END)
            for name in profile_names:
                listbox.insert(tk.END, name)
            target = select_name or self.current_profile_name
            if target in profile_names:
                idx = profile_names.index(target)
                listbox.selection_set(idx)
                listbox.see(idx)

        def selected_profile():
            if not listbox.curselection():
                return None
            return profile_names[listbox.curselection()[0]]

        actions = tk.Frame(dialog, bg=CARD_BG)
        actions.pack(fill="x", padx=14, pady=(0, 14))

        tk.Button(actions, text="Save Current As", command=lambda: (self._save_profile_as(), refresh_profiles(self.current_profile_name)), bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Save Over Current", command=lambda: (self._save_profile(self.current_profile_name), refresh_profiles(self.current_profile_name)), bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Load Selected", command=lambda: (self._load_profile(selected_profile()) if selected_profile() else None, refresh_profiles(self.current_profile_name)), bg=ACCENT_2, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Delete Selected", command=lambda: (self._delete_profile(selected_profile()) if selected_profile() else None, refresh_profiles(self.current_profile_name)), bg=CARD_BORDER, fg=TEXT, activebackground=DANGER, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left")

        tk.Label(dialog, text="Profiles save the current settings, alerts, tabs, layouts, and custom graph setup.", bg=CARD_BG, fg=MUTED, font=("Bahnschrift", 10), justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        refresh_profiles()

    def _default_layout_copy(self):
        layout = {}
        for index, name in enumerate(PANEL_DEFS):
            if name in DEFAULT_PANEL_LAYOUTS:
                layout[name] = DEFAULT_PANEL_LAYOUTS[name].copy()
            else:
                if PANEL_DEFS[name]["section"] == "graphs":
                    layout[name] = {"x": 0.04, "y": 0.06 + (index % 4) * 0.06, "w": 0.46, "h": 0.24, "visible": False}
                else:
                    layout[name] = {"x": 0.06 + (index % 4) * 0.08, "y": 0.06 + (index % 4) * 0.05, "w": 0.22, "h": 0.20, "visible": False}
        return layout

    def _blank_layout_copy(self):
        layout = self._default_layout_copy()
        for spec in layout.values():
            spec["visible"] = False
        return layout

    def _live_layout_copy(self):
        layout = self._blank_layout_copy()
        for panel_name in (
            "wheel_gauge",
            "tps_gauge",
            "aps_gauge",
            "gear_stat",
            "oil_temp_gauge",
            "coolant_gauge",
            "lambda_gauge",
            "map_gauge",
            "fuel_pressure_gauge",
            "oil_pressure_gauge",
            "rpm_tach",
        ):
            layout[panel_name] = DEFAULT_PANEL_LAYOUTS[panel_name].copy()
            layout[panel_name]["visible"] = True
        return layout

    def _logging_layout_copy(self):
        layout = self._blank_layout_copy()
        panels = (
            "rpm_trend",
            "tps_trend",
            "aps_trend",
            "lambda_trend",
        )
        columns = 2
        cell_w = 0.46
        cell_h = 0.42
        x_gap = 0.04
        y_gap = 0.06
        x_positions = [0.02, 0.02 + cell_w + x_gap]
        for index, panel_name in enumerate(panels):
            row = index // columns
            col = index % columns
            layout[panel_name] = {
                "x": x_positions[col],
                "y": 0.02 + row * (cell_h + y_gap),
                "w": cell_w,
                "h": cell_h,
                "visible": True,
            }
            layout[panel_name]["visible"] = True
        return layout

    def _seed_default_tabs(self):
        self._create_tab("LIVE", self._live_layout_copy(), select=True)
        self._create_tab("LOGGING", self._logging_layout_copy(), select=False)
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()

    def _initialize_tabs(self):
        if self._restore_tabs_from_persistence():
            return
        self._seed_default_tabs()
        self._save_persisted_state()

    def _create_tab(self, name: str, layout: dict, select: bool):
        tab_id = f"tab_{len(self.tab_order) + 1}"
        self.tabs[tab_id] = {
            "name": name,
            "layout": layout,
            "custom_graphs": self._default_custom_graph_config(),
            "custom_graph_titles": self._default_custom_graph_titles(),
        }
        self.tab_order.append(tab_id)
        if select or self.current_tab_id is None:
            self.current_tab_id = tab_id
        return tab_id

    def _duplicate_current_tab(self):
        if self.current_tab_id is None or self.current_tab_id not in self.tabs:
            return
        self._push_undo_state()
        source = self.tabs[self.current_tab_id]
        new_name = f"{source['name']} Copy"
        new_layout = json.loads(json.dumps(source.get("layout", {})))
        new_tab_id = self._create_tab(new_name, new_layout, select=True)
        self.tabs[new_tab_id]["custom_graphs"] = json.loads(json.dumps(source.get("custom_graphs", self._default_custom_graph_config())))
        self.tabs[new_tab_id]["custom_graph_titles"] = json.loads(json.dumps(source.get("custom_graph_titles", self._default_custom_graph_titles())))
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()
        self._save_persisted_state()

    def _reset_named_tab(self, tab_name: str):
        target_id = None
        for tab_id in self.tab_order:
            if self.tabs.get(tab_id, {}).get("name", "").upper() == tab_name.upper():
                target_id = tab_id
                break
        if target_id is None:
            return
        self._push_undo_state()
        if tab_name.upper() == "LIVE":
            self.tabs[target_id]["layout"] = self._live_layout_copy()
        elif tab_name.upper() == "LOGGING":
            self.tabs[target_id]["layout"] = self._logging_layout_copy()
        else:
            self.tabs[target_id]["layout"] = self._blank_layout_copy()
        self.tabs[target_id]["custom_graphs"] = self._default_custom_graph_config()
        self.tabs[target_id]["custom_graph_titles"] = self._default_custom_graph_titles()
        if self.current_tab_id == target_id:
            self._layout_panels()
            self._populate_drawer()
        self._save_persisted_state()

    def _reset_current_tab(self):
        if self.current_tab_id is None:
            return
        current_name = self.tabs.get(self.current_tab_id, {}).get("name", "")
        if current_name.upper() in {"LIVE", "LOGGING"}:
            self._reset_named_tab(current_name)
            return
        self._push_undo_state()
        self.tabs[self.current_tab_id]["layout"] = self._blank_layout_copy()
        self.tabs[self.current_tab_id]["custom_graphs"] = self._default_custom_graph_config()
        self.tabs[self.current_tab_id]["custom_graph_titles"] = self._default_custom_graph_titles()
        self._layout_panels()
        self._populate_drawer()
        self._save_persisted_state()

    def _reset_all_tabs(self):
        self._push_undo_state()
        self.tabs.clear()
        self.tab_order.clear()
        self.current_tab_id = None
        self._seed_default_tabs()
        self.latched_alerts.clear()
        self._save_persisted_state()

    def _export_workspace(self):
        destination = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export Workspace",
            initialfile="telemetry_workspace.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not destination:
            return
        payload = {
            "profile_name": self.current_profile_name,
            "settings": self.settings_model,
            "critical_limits": {
                metric_key: {
                    "warn_low": bounds.get("warn_low", ""),
                    "warn_high": bounds.get("warn_high", ""),
                    "crit_low": bounds.get("crit_low", ""),
                    "crit_high": bounds.get("crit_high", ""),
                }
                for metric_key, bounds in self.critical_limits.items()
            },
            "tabs": self._serialize_tabs_payload(),
            "current_tab_index": max(0, self.tab_order.index(self.current_tab_id)) if self.current_tab_id in self.tab_order else 0,
        }
        try:
            Path(destination).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _import_workspace(self):
        source = filedialog.askopenfilename(
            parent=self.root,
            title="Import Workspace",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not source:
            return
        try:
            payload = json.loads(Path(source).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self._push_undo_state()
        self._apply_workspace_payload(payload)

    def _add_tab(self, initial: bool = False):
        tab_index = len(self.tab_order) + 1
        layout = self._live_layout_copy() if initial else self._blank_layout_copy()
        self._push_undo_state()
        self._create_tab(f"TAB{tab_index}", layout, select=True)
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()
        self._save_persisted_state()

    def _select_tab(self, tab_id: str):
        if tab_id not in self.tabs:
            return
        self.current_tab_id = tab_id
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()
        self._save_persisted_state()

    def _render_tab_buttons(self):
        signature = tuple(self.tab_order)
        needs_rebuild = signature != self._tab_signature or set(self.tab_buttons) != set(self.tab_order)
        if needs_rebuild:
            for child in self.tab_bar.winfo_children():
                child.destroy()
            self.tab_buttons.clear()
            self.tab_labels.clear()

            for tab_id in self.tab_order:
                button = tk.Frame(
                    self.tab_bar,
                    bg=CARD_BG,
                    highlightthickness=1,
                    highlightbackground=CARD_BORDER,
                )
                button.pack(side="left", padx=(0, GAP_SM))
                label = tk.Label(
                    button,
                    text=self.tabs[tab_id]["name"],
                    bg=CARD_BG,
                    fg=MUTED,
                    font=LABEL_FONT,
                    padx=16,
                    pady=7,
                    cursor="hand2",
                )
                label.pack()
                for widget in (button, label):
                    widget.bind("<Button-1>", lambda event, t=tab_id: self._select_tab(t))
                    widget.bind("<Double-Button-1>", lambda event, t=tab_id: self._start_tab_rename(t))
                    widget.bind("<Button-3>", lambda event, t=tab_id: self._show_tab_menu(event, t))
                self._bind_hover(label, CARD_BG, CARD_HOVER, MUTED, TEXT)
                self.tab_buttons[tab_id] = button
                self.tab_labels[tab_id] = label

            plus = tk.Button(
                self.tab_bar,
                text="+",
                command=self._add_tab,
                bg=CARD_BG,
                fg=ACCENT,
                activebackground=CARD_HOVER,
                activeforeground=ACCENT,
                relief="flat",
                highlightthickness=1,
                highlightbackground=CARD_BORDER,
                font=("Bahnschrift Bold", 12),
                padx=12,
                pady=7,
                cursor="hand2",
            )
            plus.pack(side="left")
            self._bind_hover(plus, CARD_BG, CARD_HOVER, ACCENT, ACCENT)
            self._tab_signature = signature

        for tab_id in self.tab_order:
            is_active = tab_id == self.current_tab_id
            button = self.tab_buttons[tab_id]
            label = self.tab_labels[tab_id]
            button.config(bg=ACCENT_2 if is_active else CARD_BG, highlightbackground=ACCENT_2 if is_active else CARD_BORDER)
            label.config(
                text=self.tabs[tab_id]["name"],
                bg=ACCENT_2 if is_active else CARD_BG,
                fg=TEXT if is_active else MUTED,
            )

    def _on_dashboard_resize(self, _event=None):
        canvas_w = max(1, self.dashboard_view.winfo_width())
        canvas_h = max(1, self.dashboard_view.winfo_height())
        self.dashboard_view.itemconfigure(self.dashboard_window, width=canvas_w, height=canvas_h)
        self.dashboard_view.configure(scrollregion=(0, 0, canvas_w, canvas_h))
        self._layout_panels()

    def _current_layout(self):
        if self.current_tab_id is None:
            return {}
        return self.tabs[self.current_tab_id]["layout"]

    def _current_custom_graphs(self):
        if self.current_tab_id is None:
            return {}
        return self.tabs[self.current_tab_id].setdefault("custom_graphs", self._default_custom_graph_config())

    def _current_custom_graph_titles(self):
        if self.current_tab_id is None:
            return {}
        return self.tabs[self.current_tab_id].setdefault("custom_graph_titles", self._default_custom_graph_titles())

    def _layout_panels(self):
        layout = self._current_layout()
        area_w = max(1, self.dashboard_view.winfo_width())
        area_h = max(1, self.dashboard_view.winfo_height())
        for name, widget in self.panel_widgets.items():
            spec = layout.get(name, self._default_layout_copy()[name])
            if not spec.get("visible", True):
                widget.place_forget()
                self.panel_handles[name].place_forget()
                self.panel_delete_buttons[name].place_forget()
                continue
            min_size = PANEL_MIN_SIZE["trend"] if "trend" in name else PANEL_MIN_SIZE["default"]
            w = max(min_size[0], int(spec["w"] * area_w))
            h = max(min_size[1], int(spec["h"] * area_h))
            x = int(spec["x"] * area_w)
            y = int(spec["y"] * area_h)
            x = max(0, min(x, area_w - w))
            y = max(0, min(y, area_h - h))
            widget.place(x=x, y=y, width=w, height=h)
            if self.edit_mode:
                self.panel_handles[name].place(x=x + w - 14, y=y + h - 14, width=14, height=14)
                self.panel_delete_buttons[name].place(x=x + w - 22, y=y + 4, width=18, height=18)
            else:
                self.panel_handles[name].place_forget()
                self.panel_delete_buttons[name].place_forget()

    def _panel_visible(self, name: str) -> bool:
        return self._current_layout().get(name, {}).get("visible", False)

    def _start_drag(self, event, panel_name: str):
        if not self.edit_mode:
            return
        layout = self._current_layout()
        if panel_name not in layout:
            return
        if not layout[panel_name].get("visible", True):
            return
        self._push_undo_state()
        self._drag_state = {
            "panel": panel_name,
            "root_x": event.x_root,
            "root_y": event.y_root,
            "start": layout[panel_name].copy(),
        }

    def _drag_panel(self, event, panel_name: str):
        if not self.edit_mode or self._drag_state is None or self._drag_state["panel"] != panel_name:
            return
        area_w = max(1, self.dashboard.winfo_width())
        area_h = max(1, self.dashboard.winfo_height())
        dx = (event.x_root - self._drag_state["root_x"]) / area_w
        dy = (event.y_root - self._drag_state["root_y"]) / area_h
        layout = self._current_layout()
        spec = layout[panel_name]
        start = self._drag_state["start"]
        spec["x"] = max(0.0, min(1.0 - spec["w"], start["x"] + dx))
        spec["y"] = max(0.0, min(1.0 - spec["h"], start["y"] + dy))
        self._layout_panels()

    def _end_drag(self, _event=None):
        should_persist = self._drag_state is not None or self._resize_state is not None
        self._drag_state = None
        self._resize_state = None
        if should_persist:
            self._save_persisted_state()

    def _start_resize(self, event, panel_name: str):
        if not self.edit_mode:
            return
        layout = self._current_layout()
        if panel_name not in layout:
            return
        self._push_undo_state()
        self._resize_state = {
            "panel": panel_name,
            "root_x": event.x_root,
            "root_y": event.y_root,
            "start": layout[panel_name].copy(),
        }

    def _resize_panel(self, event, panel_name: str):
        if not self.edit_mode or self._resize_state is None or self._resize_state["panel"] != panel_name:
            return
        area_w = max(1, self.dashboard.winfo_width())
        area_h = max(1, self.dashboard.winfo_height())
        start = self._resize_state["start"]
        spec = self._current_layout()[panel_name]
        min_size = PANEL_MIN_SIZE["trend"] if "trend" in panel_name else PANEL_MIN_SIZE["default"]
        min_w = min_size[0] / area_w
        min_h = min_size[1] / area_h
        dw = (event.x_root - self._resize_state["root_x"]) / area_w
        dh = (event.y_root - self._resize_state["root_y"]) / area_h
        spec["w"] = max(min_w, min(1.0 - start["x"], start["w"] + dw))
        spec["h"] = max(min_h, min(1.0 - start["y"], start["h"] + dh))
        self._layout_panels()

    def _hide_panel(self, panel_name: str):
        layout = self._current_layout()
        if panel_name in layout:
            self._push_undo_state()
            layout[panel_name]["visible"] = False
            self._layout_panels()
            self._populate_drawer()
            self._save_persisted_state()

    def _show_panel(self, panel_name: str):
        layout = self._current_layout()
        if panel_name in layout:
            self._push_undo_state()
            layout[panel_name]["visible"] = True
            self._layout_panels()
            self._populate_drawer()
            self._save_persisted_state()

    def _configure_custom_graph(self, panel_name: str):
        current_entries = self._current_custom_graphs().get(panel_name, [])
        current_map = {entry["key"]: entry["color"] for entry in current_entries if "key" in entry and "color" in entry}

        dialog = tk.Toplevel(self.root)
        dialog.title("Custom Graph")
        dialog.configure(bg=BACKGROUND)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        self._apply_dark_title_bar(dialog)

        tk.Label(
            dialog,
            text="Select metrics and colors",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Bahnschrift SemiBold", 13),
        ).pack(anchor="w", padx=14, pady=(14, 10))

        rows = tk.Frame(dialog, bg=BACKGROUND)
        rows.pack(fill="both", expand=True, padx=14)

        selections = {}
        colors = {}

        def choose_color(metric_key: str):
            picked = colorchooser.askcolor(color=colors[metric_key].get(), parent=dialog)[1]
            if picked:
                colors[metric_key].set(picked)
                color_buttons[metric_key].config(bg=picked, activebackground=picked)

        color_buttons = {}
        for metric_key, meta in GRAPH_METRIC_OPTIONS.items():
            row = tk.Frame(rows, bg=BACKGROUND)
            row.pack(fill="x", pady=4)

            enabled = tk.BooleanVar(value=metric_key in current_map)
            color_var = tk.StringVar(value=current_map.get(metric_key, meta["color"]))
            selections[metric_key] = enabled
            colors[metric_key] = color_var

            tk.Checkbutton(
                row,
                text=meta["label"],
                variable=enabled,
                bg=BACKGROUND,
                fg=TEXT,
                activebackground=BACKGROUND,
                activeforeground=TEXT,
                selectcolor=CARD_BG,
                font=("Bahnschrift SemiBold", 11),
                anchor="w",
                width=18,
            ).pack(side="left")

            button = tk.Button(
                row,
                text="Color",
                command=lambda key=metric_key: choose_color(key),
                bg=color_var.get(),
                fg=TEXT,
                activebackground=color_var.get(),
                activeforeground=TEXT,
                relief="flat",
                highlightthickness=1,
                highlightbackground=CARD_BORDER,
                padx=10,
                pady=4,
                cursor="hand2",
            )
            button.pack(side="right")
            color_buttons[metric_key] = button

        actions = tk.Frame(dialog, bg=BACKGROUND)
        actions.pack(fill="x", padx=14, pady=(12, 14))

        def save_and_close():
            self._push_undo_state()
            selected = []
            for metric_key in GRAPH_METRIC_OPTIONS:
                if selections[metric_key].get():
                    selected.append({"key": metric_key, "color": colors[metric_key].get()})
            self._current_custom_graphs()[panel_name] = selected
            self._save_persisted_state()
            dialog.destroy()
            if self._panel_visible(panel_name):
                self._last_graph_refresh_monotonic = 0.0
                self._refresh()

        tk.Button(
            actions,
            text="Cancel",
            command=dialog.destroy,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BORDER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side="right")

        tk.Button(
            actions,
            text="Save",
            command=save_and_close,
            bg=ACCENT_2,
            fg=TEXT,
            activebackground=ACCENT_2,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        dialog.wait_window()

    def _rename_custom_graph(self, panel_name: str):
        current_title = self._current_custom_graph_titles().get(panel_name, self._default_custom_graph_titles().get(panel_name, "Custom Graph"))
        new_name = simpledialog.askstring("Rename Graph", "Graph name:", initialvalue=current_title, parent=self.root)
        if not new_name:
            return
        self._push_undo_state()
        updated = new_name.strip() or current_title
        self._current_custom_graph_titles()[panel_name] = updated
        widget = self.panel_widgets.get(panel_name)
        if widget is not None:
            widget.title = updated
            if self._panel_visible(panel_name):
                widget._draw()
        self._save_persisted_state()

    def _show_panel_menu(self, event, panel_name: str):
        menu = tk.Menu(self.root, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=CARD_BORDER, activeforeground=TEXT)
        if panel_name in CUSTOM_GRAPH_PANEL_NAMES:
            menu.add_command(label="Rename Graph", command=lambda p=panel_name: self._rename_custom_graph(p))
            menu.add_command(label="Edit Metrics", command=lambda p=panel_name: self._configure_custom_graph(p))
            menu.add_separator()
        if PANEL_DEFS.get(panel_name, {}).get("section") == "graphs":
            paused = self._graph_panel_options.get(panel_name, {}).get("paused", False)
            menu.add_command(
                label="Resume Graph" if paused else "Pause Graph",
                command=lambda p=panel_name: self._set_graph_paused(p, not self._graph_panel_options.get(p, {}).get("paused", False)),
            )
            menu.add_command(label="Clear Graph", command=lambda p=panel_name: self._clear_graph(p))
            window_menu = tk.Menu(menu, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=CARD_BORDER, activeforeground=TEXT)
            for seconds in (5, 10, 30, 60):
                window_menu.add_command(label=f"{seconds}s", command=lambda s=seconds, p=panel_name: self._set_graph_window(p, s))
            menu.add_cascade(label="Time Window", menu=window_menu)
            menu.add_separator()
        menu.add_command(label="Delete Container", command=lambda p=panel_name: self._hide_panel(p))
        menu.tk_popup(event.x_root, event.y_root)

    def _show_custom_graph_menu(self, event, panel_name: str):
        self._show_panel_menu(event, panel_name)

    def _build_default_settings_model(self):
        empty_frame = lambda frame_id, id_position="0", id_decimal="0": {
            "frame_size": "8",
            "id_position": id_position,
            "id_decimal": id_decimal,
            "parameters": [],
        }
        streams = {f"Stream {index}": {} for index in range(1, 11)}
        streams["Stream 1"]["Frame 1"] = empty_frame(1)
        streams["Stream 2"]["Frame 1"] = {
            "frame_size": "8",
            "id_position": "0",
            "id_decimal": "0",
            "parameters": [
                {"name": "Engine Speed", "start": "8", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "ECT", "start": "24", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Oil Temperature", "start": "32", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Oil Pressure", "start": "40", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Neutral/Park (status)", "start": "56", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
            ],
        }
        streams["Stream 2"]["Frame 2"] = {
            "frame_size": "8",
            "id_position": "1",
            "id_decimal": "1",
            "parameters": [
                {"name": "Lambda 1", "start": "8", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "100", "divider": "1", "offset": "0"},
                {"name": "TPS (Main)", "start": "16", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Gear (Status)", "start": "24", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Driven Wheel Speed", "start": "32", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Oil Pressure", "start": "48", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
            ],
        }
        streams["Stream 2"]["Frame 3"] = {
            "frame_size": "8",
            "id_position": "2",
            "id_decimal": "2",
            "parameters": [
                {"name": "APS (Main)", "start": "8", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Fuel Pressure", "start": "24", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "4", "divider": "1", "offset": "0"},
            ],
        }
        streams["Stream 5"]["Frame 1"] = {
            "frame_size": "8",
            "id_position": "0",
            "id_decimal": "0",
            "parameters": [
                {"name": "Engine Speed", "start": "8", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "TPS (Main)", "start": "24", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "APS (Main)", "start": "32", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Lambda 1", "start": "40", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "10", "divider": "1", "offset": "0"},
            ],
        }
        streams["Stream 6"]["Frame 1"] = {
            "frame_size": "8",
            "id_position": "0",
            "id_decimal": "0",
            "parameters": [
                {"name": "Oil Pressure", "start": "8", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Fuel Pressure", "start": "24", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "MAP", "start": "40", "width": "16", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
            ],
        }
        streams["Stream 7"]["Frame 1"] = {
            "frame_size": "8",
            "id_position": "0",
            "id_decimal": "0",
            "parameters": [
                {"name": "ECT", "start": "32", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
                {"name": "Oil Temperature", "start": "40", "width": "8", "byte_order": "MS First", "type": "Unsigned", "multiply": "1", "divider": "1", "offset": "0"},
            ],
        }
        return {
            "connection": {
                "serial_port": "COM12",
                "baud_rate": "115200",
                "auto_connect": True,
                "reconnect": True,
                "launch_demo": False,
            },
            "logging": {
                "enabled": False,
                "file_path": "",
                "format": "CSV",
                "auto_start": False,
                "append_mode": True,
                "auto_name": True,
                "metrics": "rpm,tps,aps,lambda1",
                "interval_ms": "100",
            },
            "graphs": {
                "history_length": "180",
                "auto_scale": True,
                "show_grid": True,
                "show_axis_labels": True,
                "custom_graph_max_metrics": "4",
                "time_window_s": "30",
            },
            "demo": {
                "speed": "1.0",
                "rpm_min": "1200",
                "rpm_max": "11000",
                "temp_min": "75",
                "temp_max": "110",
                "pressure_min": "20",
                "pressure_max": "90",
            },
            "advanced": {
                "developer_mode": False,
                "raw_frame_debug": False,
            },
            "alerts": {
                "latching": False,
            },
            "mode": {
                "can_module": "CAN 1",
                "mode": "User Defined",
                "bit_rate": "1 Mbit/s",
                "obd": "OFF",
                "channels": [
                    {"name": "1: Link Razor PDM", "mode": "Link Razor PDM", "can_id": "500", "rate": "20 Hz", "format": "Normal"},
                    {"name": "2: Transmit User Stream 2", "mode": "Transmit User Stream 2", "can_id": "1000", "rate": "20 Hz", "format": "Normal"},
                    {"name": "3: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                    {"name": "4: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                    {"name": "5: Transmit User Stream 5", "mode": "Transmit User Stream 5", "can_id": "1001", "rate": "100 Hz", "format": "Normal"},
                    {"name": "6: Transmit User Stream 6", "mode": "Transmit User Stream 6", "can_id": "1002", "rate": "50 Hz", "format": "Normal"},
                    {"name": "7: Transmit User Stream 7", "mode": "Transmit User Stream 7", "can_id": "1003", "rate": "10 Hz", "format": "Normal"},
                    {"name": "8: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                    {"name": "9: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                    {"name": "10: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                ],
            },
            "streams": streams,
        }

    def _sync_critical_limits_from_vars(self):
        if not self.critical_limit_vars:
            return
        for metric_key, bounds in self.critical_limit_vars.items():
            if metric_key not in self.critical_limits:
                continue
            for field_name in ("warn_low", "warn_high", "crit_low", "crit_high"):
                if field_name in bounds:
                    self.critical_limits[metric_key][field_name] = bounds[field_name].get().strip()

    def _metric_current_value(self, metric_key: str):
        metric = getattr(self.state, metric_key, None)
        if metric is None:
            return None
        if metric.value is not None:
            return float(metric.value)
        if metric.rendered_value is not None:
            return float(metric.rendered_value)
        return None

    def _active_alert_state(self):
        self._sync_critical_limits_from_vars()
        warning_alerts = []
        critical_alerts = []
        for metric_key, bounds in self.critical_limits.items():
            value = self._metric_current_value(metric_key)
            if value is None:
                continue
            label = bounds["label"]
            thresholds = {}
            for field_name in ("warn_low", "warn_high", "crit_low", "crit_high"):
                raw = bounds.get(field_name, "")
                try:
                    thresholds[field_name] = float(raw) if str(raw).strip() != "" else None
                except ValueError:
                    thresholds[field_name] = None

            is_critical = False
            if thresholds["crit_low"] is not None and value < thresholds["crit_low"]:
                critical_alerts.append(f"{label} low")
                is_critical = True
            if thresholds["crit_high"] is not None and value > thresholds["crit_high"]:
                critical_alerts.append(f"{label} high")
                is_critical = True
            if is_critical:
                continue
            if thresholds["warn_low"] is not None and value < thresholds["warn_low"]:
                warning_alerts.append(f"{label} low")
            if thresholds["warn_high"] is not None and value > thresholds["warn_high"]:
                warning_alerts.append(f"{label} high")

        latching_enabled = bool(self.settings_model.get("alerts", {}).get("latching"))
        if latching_enabled:
            for alert_text in warning_alerts:
                self.latched_alerts.setdefault(alert_text, "warning")
            for alert_text in critical_alerts:
                self.latched_alerts[alert_text] = "critical"
            active_map = dict(self.latched_alerts)
            for alert_text in warning_alerts:
                active_map.setdefault(alert_text, "warning")
            for alert_text in critical_alerts:
                active_map[alert_text] = "critical"
        else:
            self.latched_alerts.clear()
            active_map = {alert_text: "warning" for alert_text in warning_alerts}
            for alert_text in critical_alerts:
                active_map[alert_text] = "critical"

        if any(level == "critical" for level in active_map.values()):
            level = "critical"
        elif active_map:
            level = "warning"
        else:
            level = None
        return level, list(active_map.keys())

    def _acknowledge_alerts(self):
        self.latched_alerts.clear()
        self._refresh()

    def _set_menu_entry_state(self, menu, label: str, state: str):
        cache_key = (str(menu), label)
        if self._menu_entry_state_cache.get(cache_key) == state:
            return
        try:
            current_state = menu.entrycget(label, "state")
            if current_state == state:
                self._menu_entry_state_cache[cache_key] = state
                return
            menu.entryconfig(label, state=state)
            self._menu_entry_state_cache[cache_key] = state
        except tk.TclError:
            pass

    def _update_demo_controls(self):
        if not hasattr(self, "logging_menu"):
            return
        if self.demo_running:
            self._set_menu_entry_state(self.logging_menu, "Start Demo", "disabled")
            self._set_menu_entry_state(self.logging_menu, "Stop Demo", "normal")
        else:
            self._set_menu_entry_state(self.logging_menu, "Start Demo", "normal")
            self._set_menu_entry_state(self.logging_menu, "Stop Demo", "disabled")

    def _metric_logging_value(self, metric_key: str):
        metric = getattr(self.state, metric_key, None)
        if metric is None:
            return None
        return metric.value

    def _update_logging_controls(self):
        if self.logging_active:
            file_label = ""
            if self.log_path:
                file_label = Path(self.log_path).name
                if len(file_label) > 18:
                    file_label = file_label[:15] + "..."
            self.logging_status_text = f"LOG {file_label}" if file_label else ("LOGGING" if self.log_handle is not None else "LOG ARMED")
            pill_state = ("#2E7D32", TEXT, self.logging_status_text)
            self._set_menu_entry_state(self.logging_menu, "Start Logging", "disabled")
            self._set_menu_entry_state(self.logging_menu, "Stop Logging", "normal")
            self._set_menu_entry_state(self.logging_menu, "Open Log Folder", "normal")
        else:
            self.logging_status_text = "LOG OFF"
            pill_state = (CARD_BG, MUTED, self.logging_status_text)
            self._set_menu_entry_state(self.logging_menu, "Start Logging", "normal")
            self._set_menu_entry_state(self.logging_menu, "Stop Logging", "disabled")
            self._set_menu_entry_state(self.logging_menu, "Open Log Folder", "normal")
        if self._logging_pill_cache != pill_state:
            self.logging_pill.config(bg=pill_state[0], fg=pill_state[1], text=pill_state[2])
            self._logging_pill_cache = pill_state

    def _open_log_folder(self):
        log_target = self.log_path or self._resolve_log_path(str(self.settings_model["logging"].get("format", "CSV")).strip().upper() or "CSV")
        if not log_target:
            return
        folder = Path(log_target).expanduser().resolve().parent
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except Exception:
            pass

    def _logging_metric_aliases(self):
        return {
            "rpm": "rpm",
            "engine speed": "rpm",
            "engine_speed": "rpm",
            "engine rpm": "rpm",
            "tps": "tps",
            "tps_main": "tps",
            "throttle pos": "tps",
            "aps": "aps",
            "aps_main": "aps",
            "accel pedal pos": "aps",
            "lambda": "lambda1",
            "lambda1": "lambda1",
            "lambda 1": "lambda1",
            "coolant": "ect",
            "coolant temp": "ect",
            "coolant_temp": "ect",
            "engine temp": "ect",
            "ect": "ect",
            "oil temp": "oil_temp",
            "oil_temp": "oil_temp",
            "eng oil temp": "oil_temp",
            "oil pressure": "oil_pressure",
            "oil_pressure": "oil_pressure",
            "eng oil pres": "oil_pressure",
            "fuel pressure": "fuel_pressure",
            "fuel_pressure": "fuel_pressure",
            "fuel pres": "fuel_pressure",
            "gear": "gear",
            "wheel speed": "wheel_speed",
            "wheel_speed": "wheel_speed",
            "throughput": "throughput",
            "payload": "throughput",
            "payload rate": "throughput",
            "neutral_park": "neutral_park",
            "neutral/park": "neutral_park",
            "neutral park": "neutral_park",
        }

    def _resolve_log_path(self, log_format: str):
        logging_model = self.settings_model["logging"]
        raw_path = str(logging_model.get("file_path", "")).strip()
        default_ext = ".json" if log_format == "JSON" else ".csv"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if raw_path:
            path_obj = Path(raw_path)
            if path_obj.suffix:
                base_dir = path_obj.parent
                stem = path_obj.stem
                ext = path_obj.suffix
            else:
                base_dir = path_obj
                stem = "telemetry"
                ext = default_ext
        else:
            base_dir = Path(__file__).resolve().parent / "logs"
            stem = "telemetry"
            ext = default_ext

        if log_format == "MOTEC CSV":
            ext = ".csv"

        if logging_model.get("auto_name", True):
            return str(base_dir / f"{stem}_{timestamp}{ext}")
        if raw_path and Path(raw_path).suffix:
            return str(Path(raw_path))
        return str(base_dir / f"{stem}{ext}")

    def _start_logging(self):
        self.settings_model["logging"]["enabled"] = True
        self.logging_active = True
        self._last_log_monotonic = 0.0
        self._last_logged_line_count = -1
        self._close_log_session()
        self._update_logging_controls()
        self._save_persisted_state()

    def _stop_logging(self):
        self.logging_active = False
        self._close_log_session()
        self._update_logging_controls()
        self._save_persisted_state()

    def _selected_logging_metrics(self):
        raw_metrics = self.settings_model["logging"].get("metrics", "")
        aliases = self._logging_metric_aliases()
        selected = []
        seen = set()
        for token in str(raw_metrics).split(","):
            key = aliases.get(token.strip().lower())
            if key and key not in seen:
                selected.append(key)
                seen.add(key)
        if selected:
            return selected
        return [
            "rpm",
            "ect",
            "oil_temp",
            "oil_pressure",
            "fuel_pressure",
            "lambda1",
            "tps",
            "aps",
            "gear",
            "wheel_speed",
            "throughput",
        ]

    def _build_log_snapshot(self):
        snapshot = {"timestamp": datetime.now().isoformat(timespec="milliseconds")}
        for metric_name in self._selected_logging_metrics():
            value = self._metric_logging_value(metric_name)
            if value is not None:
                snapshot[metric_name] = value
        return snapshot

    @staticmethod
    def _motec_metric_spec(metric_name: str):
        specs = {
            "rpm": {"channel": "Engine RPM", "unit": "rpm", "decimals": 0},
            "ect": {"channel": "Engine Temp", "unit": "C", "decimals": 1},
            "oil_temp": {"channel": "Eng Oil Temp", "unit": "C", "decimals": 1},
            "oil_pressure": {"channel": "Eng Oil Pres", "unit": "raw", "decimals": 0},
            "fuel_pressure": {"channel": "Fuel Pres", "unit": "raw", "decimals": 0},
            "lambda1": {"channel": "Lambda", "unit": "none", "decimals": 3},
            "tps": {"channel": "Throttle Pos", "unit": "%", "decimals": 1},
            "aps": {"channel": "Accel Pedal Pos", "unit": "%", "decimals": 1},
            "gear": {"channel": "Gear", "unit": "none", "decimals": 0},
            "wheel_speed": {"channel": "Wheel Speed", "unit": "raw", "decimals": 0},
            "throughput": {"channel": "Payload Rate", "unit": "kbps", "decimals": 1},
            "neutral_park": {"channel": "Neutral Park", "unit": "none", "decimals": 0},
        }
        return specs.get(metric_name, {"channel": metric_name, "unit": "none", "decimals": 3})

    def _motec_header_rows(self, columns, sample_rate_hz: float):
        started = self.log_session_started_wallclock or datetime.now()
        date_text = started.strftime("%m/%d/%Y")
        time_text = started.strftime("%I:%M:%S %p").lstrip("0") or "0:00:00 AM"
        channel_row = ["Time"]
        units_row = ["s"]
        for metric_name in columns:
            spec = self._motec_metric_spec(metric_name)
            channel_row.append(spec["channel"])
            units_row.append(spec["unit"])
        return [
            ["Driver", "SDM Telemetry", "", "", "Engine ID", "Telemetry"],
            ["Device", "SDM Telemetry Dashboard"],
            ["Comment", "Generated by SDM Telemetry", "", "", "Session", "1"],
            ["Log Date", date_text, "", "", "Origin Time", "0.000", "s"],
            ["Log Time", time_text, "", "", "Start Time", "0.000", "s"],
            ["Sample Rate", f"{sample_rate_hz:.3f}".rstrip("0").rstrip("."), "Hz", "", "End Time", "0.000", "s"],
            ["Duration", "0.000", "s", "", "Start Distance", "0", "m"],
            ["Range", "entire outing", "", "", "End Distance", "0", "m"],
            ["Beacon Markers", ""],
            channel_row,
            units_row,
        ]

    def _motec_data_row(self, snapshot, elapsed_seconds: float):
        row = [f"{elapsed_seconds:.3f}".rstrip("0").rstrip(".") if elapsed_seconds > 0 else "0"]
        for metric_name in self.log_columns:
            value = snapshot.get(metric_name)
            if value is None:
                row.append("")
                continue
            spec = self._motec_metric_spec(metric_name)
            decimals = spec["decimals"]
            if decimals <= 0:
                row.append(str(int(round(float(value)))))
            else:
                row.append(f"{float(value):.{decimals}f}")
        return row

    def _close_log_session(self):
        if self.log_handle is not None:
            try:
                self.log_handle.close()
            except OSError:
                pass
        self.log_handle = None
        self.log_writer = None
        self.log_path = None
        self.log_format = None
        self.log_columns = []
        self.log_session_started_monotonic = None
        self.log_session_started_wallclock = None
        self._last_logged_line_count = -1
        if hasattr(self, "logging_pill"):
            self._update_logging_controls()

    def _ensure_log_session(self):
        logging_model = self.settings_model["logging"]
        if not self.logging_active:
            self._close_log_session()
            self._update_logging_controls()
            return False

        log_format = str(logging_model.get("format", "CSV")).strip().upper() or "CSV"
        columns = self._selected_logging_metrics()

        if (
            self.log_handle is not None
            and self.log_format == log_format
            and self.log_columns == columns
        ):
            return True

        file_path = self._resolve_log_path(log_format)
        if not file_path:
            self._close_log_session()
            self._update_logging_controls()
            return False
        resolved_path = str(Path(file_path))

        if (
            self.log_handle is not None
            and self.log_path == resolved_path
            and self.log_format == log_format
            and self.log_columns == columns
        ):
            return True

        self._close_log_session()

        path_obj = Path(resolved_path)
        try:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            if log_format == "CSV":
                append_mode = bool(logging_model.get("append_mode", True))
                file_exists = path_obj.exists()
                file_empty = (not file_exists) or path_obj.stat().st_size == 0
                handle = path_obj.open("a" if append_mode else "w", newline="", encoding="utf-8")
                writer = csv.DictWriter(handle, fieldnames=["timestamp", *columns], extrasaction="ignore")
                if file_empty or not append_mode:
                    writer.writeheader()
                self.log_handle = handle
                self.log_writer = writer
            elif log_format == "MOTEC CSV":
                interval_raw = str(logging_model.get("interval_ms", "100")).strip()
                try:
                    sample_rate_hz = 1000.0 / max(1.0, float(interval_raw))
                except ValueError:
                    sample_rate_hz = 10.0
                handle = path_obj.open("w", newline="", encoding="utf-8")
                writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
                self.log_session_started_monotonic = time.monotonic()
                self.log_session_started_wallclock = datetime.now()
                for row in self._motec_header_rows(columns, sample_rate_hz):
                    writer.writerow(row)
                self.log_handle = handle
                self.log_writer = writer
            else:
                append_mode = bool(logging_model.get("append_mode", True))
                self.log_handle = path_obj.open("a" if append_mode else "w", encoding="utf-8")
                self.log_writer = None
                self.log_session_started_monotonic = time.monotonic()
                self.log_session_started_wallclock = datetime.now()
            if self.log_session_started_monotonic is None:
                self.log_session_started_monotonic = time.monotonic()
            if self.log_session_started_wallclock is None:
                self.log_session_started_wallclock = datetime.now()
            self.log_path = resolved_path
            self.log_format = log_format
            self.log_columns = columns
            self._update_logging_controls()
            return True
        except OSError:
            self._close_log_session()
            self._update_logging_controls()
            return False

    def _handle_logging(self):
        if self.state.last_update_monotonic <= 0.0 and not self.demo_running:
            return
        if not self._ensure_log_session():
            return
        if self.state.line_count == self._last_logged_line_count:
            return

        interval_raw = str(self.settings_model["logging"].get("interval_ms", "100")).strip()
        try:
            interval_seconds = max(0.02, float(interval_raw) / 1000.0)
        except ValueError:
            interval_seconds = 0.1

        now = time.monotonic()
        if now - self._last_log_monotonic < interval_seconds:
            return

        snapshot = self._build_log_snapshot()
        if len(snapshot) <= 1:
            return

        try:
            if self.log_format == "CSV" and self.log_writer is not None:
                self.log_writer.writerow(snapshot)
            elif self.log_format == "MOTEC CSV" and self.log_writer is not None:
                start_time = self.log_session_started_monotonic or now
                self.log_writer.writerow(self._motec_data_row(snapshot, max(0.0, now - start_time)))
            elif self.log_handle is not None:
                self.log_handle.write(json.dumps(snapshot) + "\n")
            if self.log_handle is not None:
                self.log_handle.flush()
            self._last_log_monotonic = now
            self._last_logged_line_count = self.state.line_count
        except OSError:
            self._close_log_session()

    def _on_root_close(self):
        self._save_persisted_state()
        self._disconnect_serial(save_state=False)
        self._close_log_session()
        if self.settings_dialog is not None and self.settings_dialog.winfo_exists():
            self.settings_dialog.destroy()
        self.root.destroy()

    def _open_settings_dialog(self):
        if self.settings_dialog is not None and self.settings_dialog.winfo_exists():
            self.settings_dialog.deiconify()
            self.settings_dialog.lift()
            self.settings_dialog.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.configure(bg=BACKGROUND)
        dialog.transient(self.root)
        dialog.geometry("1100x720")
        dialog.minsize(1000, 640)
        dialog.protocol("WM_DELETE_WINDOW", dialog.withdraw)
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)
        self.settings_dialog = dialog
        self._apply_dark_title_bar(dialog)

        style = ttk.Style(dialog)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        dialog.option_add("*Background", CARD_BG)
        dialog.option_add("*Foreground", TEXT)
        dialog.option_add("*activeBackground", CARD_BORDER)
        dialog.option_add("*activeForeground", TEXT)
        dialog.option_add("*selectBackground", ACCENT_2)
        dialog.option_add("*selectForeground", TEXT)
        dialog.option_add("*Entry.Background", BACKGROUND)
        dialog.option_add("*Entry.Foreground", TEXT)
        dialog.option_add("*Entry.insertBackground", ACCENT)
        dialog.option_add("*Entry.highlightThickness", 1)
        dialog.option_add("*Entry.highlightBackground", CARD_BORDER)
        dialog.option_add("*Entry.highlightColor", ACCENT_2)
        dialog.option_add("*Entry.relief", "flat")
        dialog.option_add("*Entry.borderWidth", 1)
        dialog.option_add("*Listbox.Background", BACKGROUND)
        dialog.option_add("*Listbox.Foreground", TEXT)
        dialog.option_add("*Listbox.selectBackground", ACCENT_2)
        dialog.option_add("*Listbox.selectForeground", TEXT)
        dialog.option_add("*Button.Background", CARD_BG)
        dialog.option_add("*Button.Foreground", TEXT)
        dialog.option_add("*Checkbutton.Background", CARD_BG)
        dialog.option_add("*Checkbutton.Foreground", TEXT)
        dialog.option_add("*Radiobutton.Background", CARD_BG)
        dialog.option_add("*Radiobutton.Foreground", TEXT)
        dialog.option_add("*LabelFrame.Background", CARD_BG)
        dialog.option_add("*LabelFrame.Foreground", ACCENT)
        dialog.option_add("*LabelFrame.relief", "flat")
        dialog.option_add("*LabelFrame.borderWidth", 1)
        dialog.option_add("*LabelFrame.highlightThickness", 1)
        dialog.option_add("*LabelFrame.highlightBackground", CARD_BORDER)

        style.configure("Pclink.TNotebook", background=BACKGROUND, borderwidth=0)
        style.configure("Pclink.TNotebook.Tab", background=CARD_BG, foreground=TEXT, padding=(12, 7), font=("Bahnschrift SemiBold", 11), borderwidth=0)
        style.map("Pclink.TNotebook.Tab", background=[("selected", ACCENT_2), ("active", CARD_BORDER)], foreground=[("selected", TEXT), ("active", TEXT)])
        style.configure("Pclink.Treeview", background=BACKGROUND, fieldbackground=BACKGROUND, foreground=TEXT, rowheight=24, font=("Consolas", 10), borderwidth=1, relief="flat", bordercolor=CARD_BORDER, lightcolor=CARD_BORDER, darkcolor=CARD_BORDER)
        style.map("Pclink.Treeview", background=[("selected", ACCENT_2)], foreground=[("selected", TEXT)])
        style.configure("Pclink.Treeview.Heading", background=CARD_BG, foreground=ACCENT, font=("Bahnschrift SemiBold", 11), borderwidth=1, relief="flat", bordercolor=CARD_BORDER, lightcolor=CARD_BORDER, darkcolor=CARD_BORDER)
        style.map("Pclink.Treeview.Heading", background=[("active", CARD_BORDER)])
        style.configure("Pclink.TCombobox", fieldbackground=BACKGROUND, background=CARD_BG, foreground=TEXT, borderwidth=1, relief="flat", padding=1, arrowcolor=ACCENT, bordercolor=CARD_BORDER, lightcolor=CARD_BORDER, darkcolor=CARD_BORDER)
        style.map("Pclink.TCombobox", fieldbackground=[("readonly", BACKGROUND)], background=[("readonly", CARD_BG)], foreground=[("readonly", TEXT)])

        wrapper = tk.Frame(dialog, bg=BACKGROUND)
        wrapper.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

        notebook = ttk.Notebook(wrapper, style="Pclink.TNotebook")
        notebook.pack(fill="both", expand=True)

        connection_tab = tk.Frame(notebook, bg=CARD_BG)
        mapping_tab = tk.Frame(notebook, bg=CARD_BG)
        critical_tab = tk.Frame(notebook, bg=CARD_BG)
        logging_tab = tk.Frame(notebook, bg=CARD_BG)
        graphs_tab = tk.Frame(notebook, bg=CARD_BG)
        demo_tab = tk.Frame(notebook, bg=CARD_BG)
        advanced_tab = tk.Frame(notebook, bg=CARD_BG)
        notebook.add(connection_tab, text="Connection")
        notebook.add(mapping_tab, text="CAN Mapping")
        notebook.add(critical_tab, text="Critical")
        notebook.add(logging_tab, text="Logging")
        notebook.add(graphs_tab, text="Graphs")
        notebook.add(demo_tab, text="Demo")
        notebook.add(advanced_tab, text="Advanced")

        connection_model = self.settings_model["connection"]
        logging_model = self.settings_model["logging"]
        graphs_model = self.settings_model["graphs"]
        demo_model = self.settings_model["demo"]
        advanced_model = self.settings_model["advanced"]
        alert_settings_model = self.settings_model["alerts"]
        mode_model = self.settings_model["mode"]
        streams_model = self.settings_model["streams"]

        connection_box = tk.LabelFrame(connection_tab, text="Serial Connection", bg=CARD_BG, padx=12, pady=10)
        connection_box.pack(fill="both", expand=True, padx=10, pady=10)

        serial_port_var = tk.StringVar(value=connection_model["serial_port"])
        baud_rate_var = tk.StringVar(value=connection_model["baud_rate"])
        auto_connect_var = tk.BooleanVar(value=connection_model["auto_connect"])
        reconnect_var = tk.BooleanVar(value=connection_model["reconnect"])
        launch_demo_var = tk.BooleanVar(value=connection_model["launch_demo"])

        tk.Label(connection_box, text="Serial Port", bg=CARD_BG, fg=TEXT).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 10))
        tk.Entry(connection_box, textvariable=serial_port_var, width=16).grid(row=0, column=1, sticky="w", pady=(0, 10))
        tk.Label(connection_box, text="Baud Rate", bg=CARD_BG, fg=TEXT).grid(row=0, column=2, sticky="w", padx=(30, 10), pady=(0, 10))
        tk.Entry(connection_box, textvariable=baud_rate_var, width=16).grid(row=0, column=3, sticky="w", pady=(0, 10))

        tk.Checkbutton(connection_box, text="Auto Connect On Launch", variable=auto_connect_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND, anchor="w").grid(row=1, column=0, columnspan=2, sticky="w", pady=4)
        tk.Checkbutton(connection_box, text="Reconnect Automatically", variable=reconnect_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND, anchor="w").grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
        tk.Checkbutton(connection_box, text="Launch In Demo Mode", variable=launch_demo_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND, anchor="w").grid(row=3, column=0, columnspan=2, sticky="w", pady=4)

        tk.Label(
            connection_box,
            text="These settings define how the dashboard connects. They do not reconfigure the live decoder.",
            bg=CARD_BG,
            fg=MUTED,
            font=("Bahnschrift", 10),
            justify="left",
        ).grid(row=4, column=0, columnspan=4, sticky="w", pady=(16, 0))

        mapping_wrap = tk.Frame(mapping_tab, bg=CARD_BG)
        mapping_wrap.pack(fill="both", expand=True, padx=10, pady=10)

        mode_data = tk.LabelFrame(mapping_wrap, text="Channels", bg=CARD_BG, padx=10, pady=8)
        mode_data.pack(fill="x", expand=False, pady=(0, 10))

        channel_list = tk.Listbox(mode_data, exportselection=False, width=28, height=12, bg=BACKGROUND, fg=TEXT, selectbackground=ACCENT_2, selectforeground=TEXT, highlightthickness=1, highlightbackground=CARD_BORDER)
        channel_list.grid(row=0, column=0, rowspan=5, sticky="nsw", padx=(0, 14))

        for item in mode_model["channels"]:
            channel_list.insert("end", item["name"])

        tk.Label(mode_data, text="Mode", bg=CARD_BG, fg=TEXT).grid(row=0, column=1, sticky="w")
        channel_mode_var = tk.StringVar()
        channel_mode_combo = ttk.Combobox(
            mode_data,
            style="Pclink.TCombobox",
            values=[
                "OFF",
                "Link Razor PDM",
                "Transmit User Stream 2",
                "Transmit User Stream 5",
                "Transmit User Stream 6",
                "Transmit User Stream 7",
                "Receive User Stream 3",
                "Receive User Stream 4",
            ],
            textvariable=channel_mode_var,
            width=22,
        )
        channel_mode_combo.grid(row=0, column=2, sticky="w", padx=(8, 24))

        tk.Label(mode_data, text="CAN ID", bg=CARD_BG, fg=TEXT).grid(row=0, column=3, sticky="w")
        channel_id_entry = tk.Entry(mode_data, width=12)
        channel_id_entry.grid(row=0, column=4, sticky="w", padx=(8, 24))

        tk.Label(mode_data, text="Format", bg=CARD_BG, fg=TEXT).grid(row=1, column=1, sticky="w", pady=(12, 0))
        channel_format_var = tk.StringVar()
        format_box = tk.Frame(mode_data, bg=CARD_BG)
        format_box.grid(row=1, column=2, columnspan=3, sticky="w", padx=(8, 0), pady=(12, 0))
        tk.Radiobutton(format_box, text="Normal", value="Normal", variable=channel_format_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).pack(anchor="w")
        tk.Radiobutton(format_box, text="Extended", value="Extended", variable=channel_format_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).pack(anchor="w")

        selected_channel_index = {"value": 0}

        def load_channel(index):
            if not mode_model["channels"]:
                return
            selected_channel_index["value"] = index
            item = mode_model["channels"][index]
            channel_mode_var.set(item["mode"])
            channel_id_entry.delete(0, "end")
            channel_id_entry.insert(0, item["can_id"])
            channel_format_var.set(item["format"])

        def save_channel():
            idx = selected_channel_index["value"]
            item = mode_model["channels"][idx]
            item["mode"] = channel_mode_var.get()
            item["can_id"] = channel_id_entry.get()
            item["format"] = channel_format_var.get()
            prefix = item["name"].split(":", 1)[0]
            item["name"] = f"{prefix}: {item['mode'] or 'OFF'}"
            channel_list.delete(idx)
            channel_list.insert(idx, item["name"])
            channel_list.selection_clear(0, "end")
            channel_list.selection_set(idx)

        def add_channel():
            number = len(mode_model["channels"]) + 1
            new_item = {"name": f"{number}: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"}
            mode_model["channels"].append(new_item)
            channel_list.insert("end", new_item["name"])
            channel_list.selection_clear(0, "end")
            channel_list.selection_set("end")
            load_channel(len(mode_model["channels"]) - 1)

        def delete_channel():
            if len(mode_model["channels"]) <= 1:
                return
            idx = selected_channel_index["value"]
            del mode_model["channels"][idx]
            channel_list.delete(idx)
            next_idx = max(0, min(idx, len(mode_model["channels"]) - 1))
            channel_list.selection_set(next_idx)
            load_channel(next_idx)

        def on_channel_select(_event=None):
            selection = channel_list.curselection()
            if selection:
                load_channel(selection[0])

        channel_list.bind("<<ListboxSelect>>", on_channel_select)
        channel_list.selection_set(0)
        load_channel(0)

        mode_actions = tk.Frame(mode_data, bg=CARD_BG)
        mode_actions.grid(row=2, column=1, columnspan=4, sticky="w", pady=(18, 0))
        for text, command in (("Save Channel", save_channel), ("Add Channel", add_channel), ("Delete Channel", delete_channel)):
            tk.Button(mode_actions, text=text, command=command, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))

        mode_data.columnconfigure(2, weight=1)
        mode_data.columnconfigure(4, weight=1)

        streams_left = tk.Frame(mapping_wrap, bg=CARD_BG)
        streams_left.pack(fill="both", expand=True)

        stream_tree = ttk.Treeview(streams_left, style="Pclink.Treeview", show="tree", selectmode="browse", height=18)
        stream_tree.grid(row=0, column=0, rowspan=4, sticky="nsw", padx=(0, 12))

        def refresh_stream_tree():
            stream_tree.delete(*stream_tree.get_children())
            for stream_name, frames in streams_model.items():
                stream_id = stream_tree.insert("", "end", text=stream_name, open=True)
                for frame_name in frames.keys():
                    stream_tree.insert(stream_id, "end", text=frame_name)

        refresh_stream_tree()

        frame_meta_box = tk.LabelFrame(streams_left, text="Frame", bg=CARD_BG, padx=10, pady=8)
        frame_meta_box.grid(row=0, column=1, sticky="new")
        frame_size_var = tk.StringVar()
        id_position_var = tk.StringVar()
        id_decimal_var = tk.StringVar()
        for idx, (label, var) in enumerate((("Frame Size", frame_size_var), ("ID Position", id_position_var), ("ID (decimal)", id_decimal_var))):
            tk.Label(frame_meta_box, text=label, bg=CARD_BG, fg=TEXT).grid(row=0, column=idx * 2, sticky="w")
            tk.Entry(frame_meta_box, textvariable=var, width=8).grid(row=0, column=idx * 2 + 1, sticky="w", padx=(6, 14))

        stream_actions = tk.Frame(streams_left, bg=CARD_BG)
        stream_actions.grid(row=1, column=1, sticky="w", pady=(8, 8))

        param_tree = ttk.Treeview(
            streams_left,
            style="Pclink.Treeview",
            columns=("name", "start", "width", "byte_order", "type", "multiply", "divider", "offset"),
            show="headings",
            height=10,
        )
        param_tree.grid(row=2, column=1, sticky="nsew")
        headings = [("name", "Parameter"), ("start", "Start P."), ("width", "Width"), ("byte_order", "Byte Or."), ("type", "Type"), ("multiply", "Multiplier"), ("divider", "Divider"), ("offset", "Offset")]
        for column, label in headings:
            param_tree.heading(column, text=label)
            param_tree.column(column, width=90 if column == "name" else 70, anchor="w")
        param_tree.column("name", width=160)

        param_editor = tk.LabelFrame(streams_left, text="Parameters", bg=CARD_BG, padx=10, pady=8)
        param_editor.grid(row=3, column=1, sticky="ew", pady=(10, 0))
        param_vars = {key: tk.StringVar() for key in ("name", "start", "width", "byte_order", "type", "multiply", "divider", "offset")}
        editor_fields = [("name", "Parameter"), ("start", "Start"), ("width", "Width"), ("byte_order", "Byte Order"), ("type", "Type"), ("multiply", "Multiply"), ("divider", "Divider"), ("offset", "Offset")]
        for idx, (key, label) in enumerate(editor_fields):
            row = idx // 4
            col = (idx % 4) * 2
            tk.Label(param_editor, text=label, bg=CARD_BG, fg=TEXT).grid(row=row, column=col, sticky="w", padx=(0, 6), pady=4)
            tk.Entry(param_editor, textvariable=param_vars[key], width=14).grid(row=row, column=col + 1, sticky="w", padx=(0, 14), pady=4)

        selected_frame = {"stream": "Stream 1", "frame": "Frame 1"}
        selected_param_index = {"value": None}

        def refresh_param_tree():
            param_tree.delete(*param_tree.get_children())
            frame = streams_model[selected_frame["stream"]][selected_frame["frame"]]
            frame_size_var.set(frame["frame_size"])
            id_position_var.set(frame["id_position"])
            id_decimal_var.set(frame["id_decimal"])
            for index, param in enumerate(frame["parameters"]):
                param_tree.insert("", "end", iid=str(index), values=(
                    param["name"], param["start"], param["width"], param["byte_order"], param["type"], param["multiply"], param["divider"], param["offset"]
                ))

        def load_param(index):
            params = streams_model[selected_frame["stream"]][selected_frame["frame"]]["parameters"]
            if index is None or index >= len(params):
                for var in param_vars.values():
                    var.set("")
                selected_param_index["value"] = None
                return
            selected_param_index["value"] = index
            item = params[index]
            for key, var in param_vars.items():
                var.set(item[key])

        def on_tree_select(_event=None):
            selected = stream_tree.selection()
            if not selected:
                return
            item_id = selected[0]
            parent = stream_tree.parent(item_id)
            if parent:
                selected_frame["stream"] = stream_tree.item(parent, "text")
                selected_frame["frame"] = stream_tree.item(item_id, "text")
                refresh_param_tree()
                load_param(0 if streams_model[selected_frame["stream"]][selected_frame["frame"]]["parameters"] else None)

        def on_param_select(_event=None):
            selection = param_tree.selection()
            if selection:
                load_param(int(selection[0]))

        def save_frame():
            frame = streams_model[selected_frame["stream"]][selected_frame["frame"]]
            frame["frame_size"] = frame_size_var.get()
            frame["id_position"] = id_position_var.get()
            frame["id_decimal"] = id_decimal_var.get()

        def add_frame():
            selected = stream_tree.selection()
            target_stream = selected_frame["stream"]
            if selected:
                node = selected[0]
                parent = stream_tree.parent(node)
                target_stream = stream_tree.item(node if not parent else parent, "text")
            name = simpledialog.askstring("Add Frame", "Frame name:", initialvalue="Frame 4", parent=dialog)
            if not name:
                return
            streams_model[target_stream][name] = {"frame_size": "8", "id_position": "0", "id_decimal": "0", "parameters": []}
            refresh_stream_tree()

        def delete_frame():
            frames = streams_model[selected_frame["stream"]]
            if selected_frame["frame"] in frames:
                del frames[selected_frame["frame"]]
                refresh_stream_tree()
                first_stream = next(iter(streams_model))
                first_frame = next(iter(streams_model[first_stream])) if streams_model[first_stream] else None
                if first_frame:
                    selected_frame["stream"] = first_stream
                    selected_frame["frame"] = first_frame
                    refresh_param_tree()
                else:
                    param_tree.delete(*param_tree.get_children())

        def save_param():
            params = streams_model[selected_frame["stream"]][selected_frame["frame"]]["parameters"]
            index = selected_param_index["value"]
            payload = {key: var.get() for key, var in param_vars.items()}
            if index is None:
                params.append(payload)
            else:
                params[index] = payload
            refresh_param_tree()

        def add_param():
            load_param(None)

        def delete_param():
            params = streams_model[selected_frame["stream"]][selected_frame["frame"]]["parameters"]
            index = selected_param_index["value"]
            if index is None or index >= len(params):
                return
            del params[index]
            refresh_param_tree()
            load_param(None)

        for text, command in (("Add Frame", add_frame), ("Delete Frame", delete_frame), ("Save Frame", save_frame)):
            tk.Button(stream_actions, text=text, command=command, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))

        param_actions = tk.Frame(param_editor, bg=CARD_BG)
        param_actions.grid(row=2, column=0, columnspan=8, sticky="w", pady=(10, 0))
        for text, command in (("Add Param", add_param), ("Save Param", save_param), ("Delete Param", delete_param)):
            tk.Button(param_actions, text=text, command=command, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))

        stream_tree.bind("<<TreeviewSelect>>", on_tree_select)
        param_tree.bind("<<TreeviewSelect>>", on_param_select)
        first_stream = next(iter(streams_model))
        first_frame = next(iter(streams_model[first_stream]))
        selected_frame["stream"] = first_stream
        selected_frame["frame"] = first_frame
        refresh_param_tree()

        streams_left.columnconfigure(1, weight=1)
        streams_left.rowconfigure(2, weight=1)

        critical_wrap = tk.Frame(critical_tab, bg=CARD_BG)
        critical_wrap.pack(fill="both", expand=True, padx=10, pady=10)

        critical_box = tk.LabelFrame(
            critical_wrap,
            text="Critical Limits",
            bg=CARD_BG,
            padx=12,
            pady=10,
        )
        critical_box.pack(fill="both", expand=True)

        tk.Label(
            critical_box,
            text="Set warning and critical thresholds. Leave a field blank to disable that threshold.",
            bg=CARD_BG,
            fg=MUTED,
            font=("Bahnschrift", 10),
        ).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 10))

        alert_settings_model = self.settings_model["alerts"]
        alert_latching_var = tk.BooleanVar(value=alert_settings_model.get("latching", False))
        tk.Checkbutton(
            critical_box,
            text="Latch alerts until acknowledged",
            variable=alert_latching_var,
            bg=CARD_BG,
            fg=TEXT,
            selectcolor=BACKGROUND,
        ).grid(row=1, column=0, columnspan=5, sticky="w", pady=(0, 10))

        tk.Label(critical_box, text="Metric", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 10)).grid(row=2, column=0, sticky="w", padx=(0, 10))
        tk.Label(critical_box, text="Warn Low", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 10)).grid(row=2, column=1, sticky="w", padx=(0, 10))
        tk.Label(critical_box, text="Warn High", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 10)).grid(row=2, column=2, sticky="w", padx=(0, 10))
        tk.Label(critical_box, text="Crit Low", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 10)).grid(row=2, column=3, sticky="w", padx=(0, 10))
        tk.Label(critical_box, text="Crit High", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 10)).grid(row=2, column=4, sticky="w")

        self.critical_limit_vars = {}
        for row_index, (metric_key, config) in enumerate(self.critical_limits.items(), start=3):
            warn_low_var = tk.StringVar(value=str(config.get("warn_low", "")))
            warn_high_var = tk.StringVar(value=str(config.get("warn_high", "")))
            crit_low_var = tk.StringVar(value=str(config.get("crit_low", "")))
            crit_high_var = tk.StringVar(value=str(config.get("crit_high", "")))
            self.critical_limit_vars[metric_key] = {
                "warn_low": warn_low_var,
                "warn_high": warn_high_var,
                "crit_low": crit_low_var,
                "crit_high": crit_high_var,
            }

            tk.Label(
                critical_box,
                text=config["label"],
                bg=CARD_BG,
                fg=TEXT,
                font=("Bahnschrift", 10),
            ).grid(row=row_index, column=0, sticky="w", pady=4, padx=(0, 10))
            tk.Entry(critical_box, textvariable=warn_low_var, width=10).grid(row=row_index, column=1, sticky="w", pady=4, padx=(0, 10))
            tk.Entry(critical_box, textvariable=warn_high_var, width=10).grid(row=row_index, column=2, sticky="w", pady=4, padx=(0, 10))
            tk.Entry(critical_box, textvariable=crit_low_var, width=10).grid(row=row_index, column=3, sticky="w", pady=4, padx=(0, 10))
            tk.Entry(critical_box, textvariable=crit_high_var, width=10).grid(row=row_index, column=4, sticky="w", pady=4)

            warn_low_var.trace_add("write", lambda *_args: self._sync_critical_limits_from_vars())
            warn_high_var.trace_add("write", lambda *_args: self._sync_critical_limits_from_vars())
            crit_low_var.trace_add("write", lambda *_args: self._sync_critical_limits_from_vars())
            crit_high_var.trace_add("write", lambda *_args: self._sync_critical_limits_from_vars())

        critical_box.columnconfigure(0, weight=1)

        logging_box = tk.LabelFrame(logging_tab, text="Logging", bg=CARD_BG, padx=12, pady=10)
        logging_box.pack(fill="both", expand=True, padx=10, pady=10)
        logging_enabled_var = tk.BooleanVar(value=logging_model["enabled"])
        logging_auto_start_var = tk.BooleanVar(value=logging_model["auto_start"])
        logging_append_var = tk.BooleanVar(value=logging_model.get("append_mode", True))
        logging_auto_name_var = tk.BooleanVar(value=logging_model.get("auto_name", True))
        logging_file_var = tk.StringVar(value=logging_model["file_path"])
        logging_format_var = tk.StringVar(value=logging_model["format"])
        logging_metrics_var = tk.StringVar(value=logging_model["metrics"])
        logging_interval_var = tk.StringVar(value=logging_model["interval_ms"])

        def browse_log_file():
            selected_format = logging_format_var.get().upper()
            if selected_format == "JSON":
                default_name = "telemetry_log.json"
                default_ext = ".json"
            elif selected_format == "MOTEC CSV":
                default_name = "telemetry_motec.csv"
                default_ext = ".csv"
            else:
                default_name = "telemetry_log.csv"
                default_ext = ".csv"
            selected_path = filedialog.asksaveasfilename(
                parent=dialog,
                title="Select Log File",
                initialfile=default_name,
                defaultextension=default_ext,
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("MoTeC CSV files", "*.csv"),
                    ("JSON files", "*.json"),
                    ("All files", "*.*"),
                ],
            )
            if selected_path:
                logging_file_var.set(selected_path)

        def metric_labels_from_value(raw_value: str):
            selected = []
            for token in str(raw_value).split(","):
                key = token.strip()
                if key in GRAPH_METRIC_OPTIONS:
                    selected.append(GRAPH_METRIC_OPTIONS[key]["label"])
            return selected

        def logging_metric_summary():
            selected = metric_labels_from_value(logging_metrics_var.get())
            if not selected:
                return "No metrics selected"
            if len(selected) <= 3:
                return ", ".join(selected)
            return ", ".join(selected[:3]) + f" +{len(selected) - 3}"

        metrics_summary_var = tk.StringVar(value=logging_metric_summary())

        def open_logging_metric_picker():
            picker = tk.Toplevel(dialog)
            picker.title("Logging Metrics")
            picker.configure(bg=BACKGROUND)
            picker.transient(dialog)
            picker.grab_set()
            picker.resizable(False, False)
            self._apply_dark_title_bar(picker)

            tk.Label(
                picker,
                text="Select metrics to include in log files",
                bg=BACKGROUND,
                fg=TEXT,
                font=("Bahnschrift SemiBold", 12),
            ).pack(anchor="w", padx=14, pady=(14, 10))

            rows = tk.Frame(picker, bg=BACKGROUND)
            rows.pack(fill="both", expand=True, padx=14, pady=(0, 8))
            selected_keys = {key.strip() for key in str(logging_metrics_var.get()).split(",") if key.strip()}
            metric_vars = {}
            for metric_key, meta in GRAPH_METRIC_OPTIONS.items():
                var = tk.BooleanVar(value=metric_key in selected_keys)
                metric_vars[metric_key] = var
                tk.Checkbutton(
                    rows,
                    text=meta["label"],
                    variable=var,
                    bg=BACKGROUND,
                    fg=TEXT,
                    activebackground=BACKGROUND,
                    activeforeground=TEXT,
                    selectcolor=CARD_BG,
                    anchor="w",
                    font=("Bahnschrift", 10),
                ).pack(anchor="w", pady=2)

            button_row = tk.Frame(picker, bg=BACKGROUND)
            button_row.pack(fill="x", padx=14, pady=(0, 14))

            def apply_selection():
                chosen = [metric_key for metric_key, var in metric_vars.items() if var.get()]
                logging_metrics_var.set(",".join(chosen))
                selected = metric_labels_from_value(logging_metrics_var.get())
                if not selected:
                    metrics_summary_var.set("No metrics selected")
                elif len(selected) <= 3:
                    metrics_summary_var.set(", ".join(selected))
                else:
                    metrics_summary_var.set(", ".join(selected[:3]) + f" +{len(selected) - 3}")
                picker.destroy()

            tk.Button(button_row, text="Cancel", command=picker.destroy, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="right")
            tk.Button(button_row, text="Apply", command=apply_selection, bg=ACCENT_2, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="right", padx=(0, 8))

        tk.Checkbutton(logging_box, text="Enable Logging", variable=logging_enabled_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Checkbutton(logging_box, text="Auto Start Logging", variable=logging_auto_start_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))
        tk.Checkbutton(logging_box, text="Append To Existing File", variable=logging_append_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Checkbutton(logging_box, text="Auto-name File By Date/Time", variable=logging_auto_name_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 12))
        tk.Label(logging_box, text="Log File Path", bg=CARD_BG, fg=TEXT).grid(row=4, column=0, sticky="w", padx=(0, 10), pady=4)
        file_path_row = tk.Frame(logging_box, bg=CARD_BG)
        file_path_row.grid(row=4, column=1, sticky="ew", pady=4)
        tk.Entry(file_path_row, textvariable=logging_file_var, width=48).pack(side="left", fill="x", expand=True)
        tk.Button(file_path_row, text="Browse", command=browse_log_file, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=2).pack(side="left", padx=(8, 0))
        tk.Label(logging_box, text="Format", bg=CARD_BG, fg=TEXT).grid(row=5, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Combobox(logging_box, style="Pclink.TCombobox", values=["CSV", "JSON", "MoTeC CSV"], textvariable=logging_format_var, width=18, state="readonly").grid(row=5, column=1, sticky="w", pady=4)
        tk.Label(logging_box, text="Metrics To Log", bg=CARD_BG, fg=TEXT).grid(row=6, column=0, sticky="w", padx=(0, 10), pady=4)
        metrics_row = tk.Frame(logging_box, bg=CARD_BG)
        metrics_row.grid(row=6, column=1, sticky="ew", pady=4)
        tk.Label(metrics_row, textvariable=metrics_summary_var, bg=BACKGROUND, fg=TEXT, anchor="w", relief="flat", highlightthickness=1, highlightbackground=CARD_BORDER, padx=10, pady=5).pack(side="left", fill="x", expand=True)
        tk.Button(metrics_row, text="Choose", command=open_logging_metric_picker, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=2).pack(side="left", padx=(8, 0))
        tk.Label(logging_box, text="Log Interval (ms)", bg=CARD_BG, fg=TEXT).grid(row=7, column=0, sticky="w", padx=(0, 10), pady=4)
        tk.Entry(logging_box, textvariable=logging_interval_var, width=18).grid(row=7, column=1, sticky="w", pady=4)
        logging_box.columnconfigure(1, weight=1)

        graphs_box = tk.LabelFrame(graphs_tab, text="Graphs", bg=CARD_BG, padx=12, pady=10)
        graphs_box.pack(fill="both", expand=True, padx=10, pady=10)
        history_length_var = tk.StringVar(value=graphs_model["history_length"])
        custom_graph_max_var = tk.StringVar(value=graphs_model["custom_graph_max_metrics"])
        time_window_var = tk.StringVar(value=graphs_model["time_window_s"])
        auto_scale_var = tk.BooleanVar(value=graphs_model["auto_scale"])
        show_grid_var = tk.BooleanVar(value=graphs_model["show_grid"])
        show_axis_labels_var = tk.BooleanVar(value=graphs_model["show_axis_labels"])

        tk.Label(graphs_box, text="Default History Length", bg=CARD_BG, fg=TEXT).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        tk.Entry(graphs_box, textvariable=history_length_var, width=14).grid(row=0, column=1, sticky="w", pady=4)
        tk.Label(graphs_box, text="Default Time Window (s)", bg=CARD_BG, fg=TEXT).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        tk.Entry(graphs_box, textvariable=time_window_var, width=14).grid(row=1, column=1, sticky="w", pady=4)
        tk.Label(graphs_box, text="Custom Graph Max Metrics", bg=CARD_BG, fg=TEXT).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=4)
        tk.Entry(graphs_box, textvariable=custom_graph_max_var, width=14).grid(row=2, column=1, sticky="w", pady=4)
        tk.Checkbutton(graphs_box, text="Enable Auto Scale", variable=auto_scale_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 4))
        tk.Checkbutton(graphs_box, text="Show Grid", variable=show_grid_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        tk.Checkbutton(graphs_box, text="Show Axis Labels", variable=show_axis_labels_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).grid(row=5, column=0, columnspan=2, sticky="w", pady=4)

        demo_box = tk.LabelFrame(demo_tab, text="Demo", bg=CARD_BG, padx=12, pady=10)
        demo_box.pack(fill="both", expand=True, padx=10, pady=10)
        demo_speed_var = tk.StringVar(value=demo_model["speed"])
        demo_rpm_min_var = tk.StringVar(value=demo_model["rpm_min"])
        demo_rpm_max_var = tk.StringVar(value=demo_model["rpm_max"])
        demo_temp_min_var = tk.StringVar(value=demo_model["temp_min"])
        demo_temp_max_var = tk.StringVar(value=demo_model["temp_max"])
        demo_pressure_min_var = tk.StringVar(value=demo_model["pressure_min"])
        demo_pressure_max_var = tk.StringVar(value=demo_model["pressure_max"])

        demo_fields = [
            ("Demo Speed", demo_speed_var),
            ("RPM Min", demo_rpm_min_var),
            ("RPM Max", demo_rpm_max_var),
            ("Temp Min", demo_temp_min_var),
            ("Temp Max", demo_temp_max_var),
            ("Pressure Min", demo_pressure_min_var),
            ("Pressure Max", demo_pressure_max_var),
        ]
        for idx, (label, var) in enumerate(demo_fields):
            row = idx // 2
            col = (idx % 2) * 2
            tk.Label(demo_box, text=label, bg=CARD_BG, fg=TEXT).grid(row=row, column=col, sticky="w", padx=(0, 10), pady=6)
            tk.Entry(demo_box, textvariable=var, width=14).grid(row=row, column=col + 1, sticky="w", padx=(0, 24), pady=6)

        advanced_box = tk.LabelFrame(advanced_tab, text="Advanced", bg=CARD_BG, padx=12, pady=10)
        advanced_box.pack(fill="both", expand=True, padx=10, pady=10)
        developer_mode_var = tk.BooleanVar(value=advanced_model["developer_mode"])
        raw_frame_debug_var = tk.BooleanVar(value=advanced_model["raw_frame_debug"])
        tk.Checkbutton(advanced_box, text="Developer Mode", variable=developer_mode_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).pack(anchor="w", pady=(0, 8))
        tk.Checkbutton(advanced_box, text="Raw Frame Debug", variable=raw_frame_debug_var, bg=CARD_BG, fg=TEXT, selectcolor=BACKGROUND).pack(anchor="w", pady=(0, 8))
        workspace_box = tk.LabelFrame(advanced_box, text="Workspace", bg=CARD_BG, padx=10, pady=8)
        workspace_box.pack(fill="x", pady=(10, 8))
        workspace_actions = tk.Frame(workspace_box, bg=CARD_BG)
        workspace_actions.pack(anchor="w")
        tk.Button(workspace_actions, text="Import Workspace", command=self._import_workspace, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(workspace_actions, text="Export Workspace", command=self._export_workspace, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Label(workspace_box, text="Imports/exports settings, tabs, layouts, thresholds, and custom graph state.", bg=CARD_BG, fg=MUTED, font=("Bahnschrift", 10)).pack(anchor="w", pady=(8, 0))

        profile_box = tk.LabelFrame(advanced_box, text="Profiles", bg=CARD_BG, padx=10, pady=8)
        profile_box.pack(fill="x", pady=(10, 8))
        profile_actions = tk.Frame(profile_box, bg=CARD_BG)
        profile_actions.pack(anchor="w")
        tk.Button(profile_actions, text="Open Profile Manager", command=self._open_profile_manager, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(profile_actions, text="Save Current As Profile", command=self._save_profile_as, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Label(profile_box, text="Current profile: " + self.current_profile_name, bg=CARD_BG, fg=MUTED, font=("Bahnschrift", 10)).pack(anchor="w", pady=(8, 0))

        session_box = tk.LabelFrame(advanced_box, text="Session Tools", bg=CARD_BG, padx=10, pady=8)
        session_box.pack(fill="x", pady=(10, 8))
        session_actions_top = tk.Frame(session_box, bg=CARD_BG)
        session_actions_top.pack(anchor="w")
        tk.Button(session_actions_top, text="Duplicate Current Tab", command=self._duplicate_current_tab, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(session_actions_top, text="Reset LIVE Tab", command=lambda: self._reset_named_tab("LIVE"), bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(session_actions_top, text="Reset LOGGING Tab", command=lambda: self._reset_named_tab("LOGGING"), bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        session_actions_bottom = tk.Frame(session_box, bg=CARD_BG)
        session_actions_bottom.pack(anchor="w", pady=(8, 0))
        tk.Button(session_actions_bottom, text="Reset All Tabs", command=self._reset_all_tabs, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Button(session_actions_bottom, text="Clear Latched Alerts", command=self._acknowledge_alerts, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="left", padx=(0, 8))
        tk.Label(
            advanced_box,
            text="These settings are GUI-side only right now. Decoder behavior does not change unless wired in later.",
            bg=CARD_BG,
            fg=MUTED,
            font=("Bahnschrift", 10),
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

        def save_connection():
            connection_model["serial_port"] = serial_port_var.get()
            connection_model["baud_rate"] = baud_rate_var.get()
            connection_model["auto_connect"] = bool(auto_connect_var.get())
            connection_model["reconnect"] = bool(reconnect_var.get())
            connection_model["launch_demo"] = bool(launch_demo_var.get())

        def save_logging():
            was_active = self.logging_active
            logging_model["enabled"] = bool(logging_enabled_var.get())
            logging_model["auto_start"] = bool(logging_auto_start_var.get())
            logging_model["append_mode"] = bool(logging_append_var.get())
            logging_model["auto_name"] = bool(logging_auto_name_var.get())
            logging_model["file_path"] = logging_file_var.get()
            logging_model["format"] = logging_format_var.get()
            logging_model["metrics"] = logging_metrics_var.get()
            logging_model["interval_ms"] = logging_interval_var.get()
            self._last_log_monotonic = 0.0
            self._close_log_session()
            if not logging_model["enabled"]:
                self.logging_active = False
            elif was_active:
                self.logging_active = True
            else:
                self.logging_active = bool(logging_model["auto_start"])
            self._update_logging_controls()

        def save_graphs():
            graphs_model["history_length"] = history_length_var.get()
            graphs_model["custom_graph_max_metrics"] = custom_graph_max_var.get()
            graphs_model["time_window_s"] = time_window_var.get()
            graphs_model["auto_scale"] = bool(auto_scale_var.get())
            graphs_model["show_grid"] = bool(show_grid_var.get())
            graphs_model["show_axis_labels"] = bool(show_axis_labels_var.get())

        def save_demo():
            demo_model["speed"] = demo_speed_var.get()
            demo_model["rpm_min"] = demo_rpm_min_var.get()
            demo_model["rpm_max"] = demo_rpm_max_var.get()
            demo_model["temp_min"] = demo_temp_min_var.get()
            demo_model["temp_max"] = demo_temp_max_var.get()
            demo_model["pressure_min"] = demo_pressure_min_var.get()
            demo_model["pressure_max"] = demo_pressure_max_var.get()

        def save_advanced():
            advanced_model["developer_mode"] = bool(developer_mode_var.get())
            advanced_model["raw_frame_debug"] = bool(raw_frame_debug_var.get())
            alert_settings_model["latching"] = bool(alert_latching_var.get())

        def save_all_settings():
            save_connection()
            save_channel()
            save_frame()
            save_logging()
            save_graphs()
            save_demo()
            save_advanced()
            self._sync_critical_limits_from_vars()
            self._save_persisted_state()

        footer = tk.Frame(dialog, bg=BACKGROUND)
        footer.grid(row=1, column=0, sticky="ew", padx=10, pady=(8, 10))
        tk.Button(footer, text="Apply", command=save_all_settings, bg=CARD_BORDER, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="right", padx=(0, 8))
        tk.Button(footer, text="OK", command=lambda: (save_all_settings(), dialog.withdraw()), bg=ACCENT_2, fg=TEXT, activebackground=ACCENT_2, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="right", padx=(0, 8))
        tk.Button(footer, text="Cancel", command=dialog.withdraw, bg=CARD_BORDER, fg=TEXT, activebackground=CARD_BORDER, activeforeground=TEXT, relief="flat", padx=10, pady=4).pack(side="right", padx=(0, 8))

    def _handle_secret_keypress(self, event):
        char = (event.char or "").lower()
        if not char or not char.isalpha():
            return
        self._secret_buffer = (self._secret_buffer + char)[-3:]
        if self._secret_buffer.endswith("daq"):
            self._trigger_easter_egg()
            self._secret_buffer = ""

    def _trigger_easter_egg(self):
        if self._easter_egg_after_id is not None:
            self.root.after_cancel(self._easter_egg_after_id)
            self._easter_egg_after_id = None
        self._easter_egg_start = time.monotonic()
        self.easter_egg_label.lift()
        self._animate_easter_egg()

    def _animate_easter_egg(self):
        elapsed = time.monotonic() - self._easter_egg_start
        if elapsed >= 5.0:
            self.easter_egg_label.place_forget()
            self._easter_egg_after_id = None
            return

        pulse = 0.5 + 0.5 * math.sin(elapsed * 5.2)
        jitter_x = math.sin(elapsed * 18.0) * 3.0
        jitter_y = math.cos(elapsed * 14.0) * 2.0
        font_size = int(68 + 14 * pulse)
        flash_on = int(elapsed * 8.0) % 2 == 0
        color = DANGER if flash_on else ACCENT

        self.easter_egg_label.config(
            fg=color,
            font=("Bahnschrift Bold", font_size),
        )
        self.easter_egg_label.place(relx=0.5, rely=0.5, anchor="center", x=int(jitter_x), y=int(jitter_y))
        self._easter_egg_after_id = self.root.after(16, self._animate_easter_egg)

    def _toggle_editor_drawer(self):
        self.editor_open = not self.editor_open
        if self.editor_open:
            self.editor_drawer.pack(side="left", fill="y", padx=(8, 0))
            self.editor_canvas.pack(side="left", fill="both", expand=True)
            self.editor_scrollbar.pack(side="right", fill="y")
            self.drawer_toggle.config(text=">")
            self._populate_drawer()
        else:
            self.editor_drawer.pack_forget()
            self.drawer_toggle.config(text="<")

    def _toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.edit_button.config(text="Disable Edit Mode" if self.edit_mode else "Enable Edit Mode")
        self._layout_panels()

    def _populate_drawer(self):
        for widget in self.drawer_live.winfo_children():
            widget.destroy()
        for widget in self.drawer_graphs.winfo_children():
            widget.destroy()

        if not self.editor_open:
            return

        if not self.edit_button.winfo_ismapped():
            self.edit_button.pack(fill="x", padx=10, pady=(10, 8))
            self.drawer_live_title.pack(anchor="w", padx=10, pady=(8, 4))
            self.drawer_live.pack(fill="x", padx=10)
            self.drawer_graph_title.pack(anchor="w", padx=10, pady=(12, 4))
            self.drawer_graphs.pack(fill="x", padx=10, pady=(0, 10))

        layout = self._current_layout()
        for panel_name, meta in PANEL_DEFS.items():
            parent = self.drawer_live if meta["section"] == "live" else self.drawer_graphs
            is_visible = layout.get(panel_name, {}).get("visible", True)
            btn = tk.Button(
                parent,
                text=("Hide " if is_visible else "Add ") + meta["label"],
                command=lambda name=panel_name: self._hide_panel(name) if layout.get(name, {}).get("visible", True) else self._show_panel(name),
                bg=BACKGROUND,
                fg=TEXT,
                activebackground=CARD_BG,
                activeforeground=TEXT,
                relief="flat",
                highlightthickness=1,
                highlightbackground=CARD_BORDER,
                font=("Bahnschrift SemiBold", 10),
                anchor="w",
                padx=10,
                pady=6,
                cursor="hand2",
            )
            btn.bind("<MouseWheel>", self._on_drawer_mousewheel)
            btn.pack(fill="x", pady=4)
        self.editor_canvas.yview_moveto(0.0)

    def _start_tab_rename(self, tab_id: str):
        new_name = simpledialog.askstring("Rename Tab", "Tab name:", initialvalue=self.tabs[tab_id]["name"], parent=self.root)
        if new_name:
            self._push_undo_state()
            self.tabs[tab_id]["name"] = new_name.strip() or self.tabs[tab_id]["name"]
            self._render_tab_buttons()
            self._save_persisted_state()

    def _remove_tab(self, tab_id: str):
        if tab_id not in self.tabs or len(self.tab_order) <= 1:
            return
        tab_name = self.tabs.get(tab_id, {}).get("name", "").upper()
        if tab_name in CORE_TAB_NAMES:
            return
        self._push_undo_state()
        remove_index = self.tab_order.index(tab_id)
        self.tab_order.remove(tab_id)
        del self.tabs[tab_id]
        if self.current_tab_id == tab_id:
            fallback_index = max(0, remove_index - 1)
            self.current_tab_id = self.tab_order[fallback_index]
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()
        self._save_persisted_state()

    def _show_tab_menu(self, event, tab_id: str):
        self._select_tab(tab_id)
        menu = tk.Menu(self.root, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=CARD_BORDER, activeforeground=TEXT)
        menu.add_command(label="Rename Tab", command=lambda t=tab_id: self._start_tab_rename(t))
        if len(self.tab_order) > 1 and self.tabs.get(tab_id, {}).get("name", "").upper() not in CORE_TAB_NAMES:
            menu.add_command(label="Remove Tab", command=lambda t=tab_id: self._remove_tab(t))
        else:
            menu.add_command(label="Remove Tab", state="disabled")
        menu.tk_popup(event.x_root, event.y_root)

    def _start_demo_mode(self):
        if self.demo_running:
            return
        self._disconnect_serial(save_state=False)
        self.demo_running = True
        self.demo_rpm = 1800
        self.demo_direction = 1
        self._update_demo_controls()
        self._update_connection_controls()
        self._queue_demo_line()

    def _stop_demo_mode(self):
        self.demo_running = False
        if self.demo_after_id is not None:
            self.root.after_cancel(self.demo_after_id)
            self.demo_after_id = None
        self._update_demo_controls()
        self._update_connection_controls()

    def _queue_demo_line(self):
        if not self.demo_running:
            self.demo_after_id = None
            return

        self.demo_rpm += self.demo_direction * random.randint(70, 180)
        if self.demo_rpm > 11200:
            self.demo_direction = -1
        elif self.demo_rpm < 1800:
            self.demo_direction = 1

        rpm = self.demo_rpm
        ect = random.randint(84, 93)
        oil_temp = random.randint(90, 104)
        oil_pressure = random.randint(32, 74)
        neutral_park = 1 if rpm < 2200 else 0
        lambda1 = random.randint(90, 102)
        tps = max(0, min(100, int((rpm / 15000) * 100) + random.randint(-2, 2)))
        aps = max(0, min(100, tps + random.randint(-2, 2)))
        gear = random.randint(2, 5)
        wheel_speed = max(0, int((rpm / 120.0) + random.randint(-2, 2)))
        fuel_pressure = random.randint(40, 68)
        map_value = random.randint(85, 110)

        self._apply_demo_values(
            rpm=rpm,
            ect=ect,
            oil_temp=oil_temp,
            oil_pressure=oil_pressure,
            neutral_park=neutral_park,
            lambda_ratio=lambda1 / 100.0,
            tps=tps,
            aps=aps,
            gear=gear,
            wheel_speed=wheel_speed,
            fuel_pressure=fuel_pressure,
            map_value=map_value,
        )
        self.demo_after_id = self.root.after(90, self._queue_demo_line)

    def _apply_demo_values(
        self,
        *,
        rpm: int,
        ect: int,
        oil_temp: int,
        oil_pressure: int,
        neutral_park: int,
        lambda_ratio: float,
        tps: int,
        aps: int,
        gear: int,
        wheel_speed: int,
        fuel_pressure: int,
        map_value: int,
    ):
        self.state.touch("DEMO")
        self.state.rpm.update(rpm)
        self.state.ect.update(ect)
        self.state.oil_temp.update(oil_temp)
        self.state.oil_pressure.update(oil_pressure)
        self.state.neutral_park.update(neutral_park)
        self.state.lambda1.update(lambda_ratio)
        self.state.tps.update(tps)
        self.state.aps.update(aps)
        self.state.gear.update(gear)
        self.state.wheel_speed.update(wheel_speed)
        self.state.fuel_pressure.update(fuel_pressure)
        self.state.map.update(map_value)
        throughput = max(120.0, min(2200.0, rpm / 6.5 + wheel_speed * 1.2))
        self.state.throughput.update(throughput)
        self._record_history("rpm", rpm)
        self._record_history("ect", ect)
        self._record_history("oil_temp", oil_temp)
        self._record_history("oil_pressure", oil_pressure)
        self._record_history("lambda1", lambda_ratio)
        self._record_history("tps", tps)
        self._record_history("aps", aps)
        self._record_history("gear", gear)
        self._record_history("wheel_speed", wheel_speed)
        self._record_history("fuel_pressure", fuel_pressure)
        self._record_history("map", map_value)
        self._record_history("throughput", throughput)

    def _on_editor_content_configure(self, _event=None):
        self.editor_canvas.configure(scrollregion=self.editor_canvas.bbox("all"))

    def _on_editor_canvas_configure(self, event):
        self.editor_canvas.itemconfigure(self.editor_window, width=event.width)

    def _on_drawer_mousewheel(self, event):
        if not self.editor_open:
            return
        self.editor_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _poll_lines(self):
        while True:
            try:
                line = self.line_queue.get_nowait()
            except queue.Empty:
                break
            if self.demo_running:
                continue
            for chunk in self._split_serial_chunks(line):
                self._apply_line(chunk)
        self.root.after(20, self._poll_lines)

    def _record_history(self, name: str, value):
        if value is None:
            return
        series = self.histories[name]
        series.append((time.monotonic(), float(value)))
        if len(series) > self.HISTORY_LIMIT:
            del series[:-self.HISTORY_LIMIT]

    def _record_rx_throughput(self, line: str):
        now = time.monotonic()
        self._rx_window_bytes += len(line.encode("utf-8", errors="ignore")) + 1
        elapsed = now - self._rx_window_start
        if elapsed >= 0.35:
            kbps = (self._rx_window_bytes * 8.0 / 1000.0) / max(elapsed, 0.001)
            self.state.throughput.update(kbps)
            self._record_history("throughput", kbps)
            self._rx_window_start = now
            self._rx_window_bytes = 0

    @staticmethod
    def _parse_halow_float(raw_value):
        if raw_value is None:
            return None
        try:
            return float(str(raw_value).rstrip(","))
        except (TypeError, ValueError):
            return None

    def _apply_halow_line(self, line: str) -> bool:
        if not (line.startswith("HALOW ") or line.startswith("HALOW:")):
            return False
        pairs = {key.lower(): value for key, value in HALOW_KV_RE.findall(line)}
        if not pairs:
            return True
        link_value = None
        for key in ("link_mbps", "air_link_mbps", "link_rate_mbps", "mbps"):
            link_value = self._parse_halow_float(pairs.get(key))
            if link_value is not None:
                break
        if link_value is not None:
            self.state.halow_link_mbps.update(link_value)
        bw_value = None
        for key in ("bw_mhz", "bandwidth_mhz", "channel_mhz"):
            bw_value = self._parse_halow_float(pairs.get(key))
            if bw_value is not None:
                break
        if bw_value is not None:
            self.state.halow_bw_mhz = bw_value
        rssi_value = self._parse_halow_float(pairs.get("rssi"))
        if rssi_value is not None:
            self.state.halow_rssi = rssi_value
        mcs_value = pairs.get("mcs")
        if mcs_value:
            self.state.halow_mcs = mcs_value.rstrip(",")
        return True

    def _apply_line(self, line: str):
        line = self._normalize_line(line)

        if line.startswith("INFO: connected to "):
            self.connection_state = "connected"
            self._last_serial_error = ""
            self._update_connection_controls()
            return

        if line.startswith("ERROR: serial "):
            self.connection_state = "disconnected"
            self._last_serial_error = line
            self._update_connection_controls()
            return

        self.state.touch(line)
        if self.serial_worker is not None and self.connection_state != "connected":
            self.connection_state = "connected"
            self._last_serial_error = ""
            self._update_connection_controls()
        if self._apply_halow_line(line):
            return
        self._record_rx_throughput(line)

        match = FRAME1_RE.fullmatch(line)
        if match:
            rpm = int(match.group("rpm"))
            ect = int(match.group("ect"))
            oil_temp = int(match.group("oil_temp"))
            oil_pressure = int(match.group("oil_pressure"))
            self.state.rpm.update(rpm)
            self.state.ect.update(ect)
            self.state.oil_temp.update(oil_temp)
            self.state.oil_pressure.update(oil_pressure)
            self.state.neutral_park.update(int(match.group("neutral_park")))
            self._record_history("rpm", rpm)
            self._record_history("ect", ect)
            self._record_history("oil_temp", oil_temp)
            self._record_history("oil_pressure", oil_pressure)
            return

        match = FRAME2_RE.fullmatch(line)
        if match:
            lambda_ratio = int(match.group("lambda1")) / 100.0
            tps = int(match.group("tps_main"))
            wheel_speed = int(match.group("wheel_speed"))
            oil_pressure = int(match.group("oil_pressure"))
            gear = int(match.group("gear"))
            self.state.lambda1.update(lambda_ratio)
            self.state.tps.update(tps)
            self.state.gear.update(gear)
            self.state.wheel_speed.update(wheel_speed)
            self.state.oil_pressure.update(oil_pressure)
            self._record_history("lambda1", lambda_ratio)
            self._record_history("tps", tps)
            self._record_history("gear", gear)
            self._record_history("wheel_speed", wheel_speed)
            self._record_history("oil_pressure", oil_pressure)
            return

        match = FRAME3_RE.fullmatch(line)
        if match:
            aps = int(match.group("aps"))
            fuel_pressure = int(match.group("fuel_pressure"))
            self.state.aps.update(aps)
            self.state.fuel_pressure.update(fuel_pressure)
            self._record_history("aps", aps)
            self._record_history("fuel_pressure", fuel_pressure)
            return

        match = STREAM5_RE.fullmatch(line)
        if match:
            rpm = int(match.group("rpm"))
            tps = int(match.group("tps"))
            aps = int(match.group("aps"))
            lambda_value = int(match.group("lambda1"))
            self.state.rpm.update(rpm)
            self.state.tps.update(tps)
            self.state.aps.update(aps)
            self.state.lambda1.update(lambda_value)
            self._record_history("rpm", rpm)
            self._record_history("tps", tps)
            self._record_history("aps", aps)
            self._record_history("lambda1", lambda_value)
            return

        match = STREAM6_RE.fullmatch(line)
        if match:
            oil_pressure = int(match.group("oil_pressure"))
            fuel_pressure = int(match.group("fuel_pressure"))
            map_value = int(match.group("map"))
            self.state.oil_pressure.update(oil_pressure)
            self.state.fuel_pressure.update(fuel_pressure)
            self.state.map.update(map_value)
            self._record_history("oil_pressure", oil_pressure)
            self._record_history("fuel_pressure", fuel_pressure)
            self._record_history("map", map_value)
            return

        match = STREAM7_RE.fullmatch(line)
        if match:
            ect = int(match.group("ect"))
            oil_temp = int(match.group("oil_temp"))
            self.state.ect.update(ect)
            self.state.oil_temp.update(oil_temp)
            self._record_history("ect", ect)
            self._record_history("oil_temp", oil_temp)
            return

    @staticmethod
    def _normalize_line(line: str) -> str:
        prefixes = ("AP: ", "STA: ", "UART OUT: ", "UART->STA: ")
        changed = True
        while changed:
            changed = False
            for prefix in prefixes:
                if line.startswith(prefix):
                    line = line[len(prefix):]
                    changed = True
        return line.strip()

    @staticmethod
    def _split_serial_chunks(line: str):
        if not line:
            return []
        text = str(line).replace("\r", "\n")
        split_tokens = (
            "AP: ",
            "STA: ",
            "UART OUT: ",
            "UART->STA: ",
            "ECU Stream",
            "ECU Frame",
            "PDM,id=",
            "HALOW ",
            "HALOW:",
            "INFO: connected to ",
            "ERROR: serial ",
        )
        for token in split_tokens:
            text = text.replace(token, f"\n{token}")
        chunks = []
        for chunk in text.splitlines():
            chunk = chunk.strip()
            if not chunk:
                continue
            chunks.append(chunk)
        return chunks

    def _default_graph_window(self) -> float:
        try:
            return max(5.0, float(self.settings_model["graphs"].get("time_window_s", "30")))
        except (TypeError, ValueError):
            return 30.0

    def _history_points(self, name: str, window_s: float | None = None):
        series = self.histories[name]
        if not series:
            return []
        points = series
        if window_s is not None and window_s > 0:
            cutoff = points[-1][0] - window_s
            points = [point for point in points if point[0] >= cutoff]
            if not points:
                points = [series[-1]]
        start = points[0][0]
        return [(t - start, v) for t, v in points]

    def _graph_metrics_for_panel(self, panel_name: str):
        mapping = {
            "rpm_trend": ["rpm"],
            "wheel_trend": ["wheel_speed"],
            "tps_trend": ["tps"],
            "aps_trend": ["aps"],
            "gear_trend": ["gear"],
            "oil_temp_trend_single": ["oil_temp"],
            "coolant_trend": ["ect"],
            "throughput_trend": ["throughput"],
            "lambda_trend": ["lambda1"],
            "fuel_pressure_trend_single": ["fuel_pressure"],
            "oil_pressure_trend_single": ["oil_pressure"],
            "map_trend": ["map"],
            "throttle_trend": ["tps", "aps"],
            "temp_trend": ["oil_temp", "ect"],
            "pressure_trend": ["oil_pressure", "fuel_pressure", "map"],
        }
        if panel_name in CUSTOM_GRAPH_PANEL_NAMES:
            return [entry.get("key") for entry in self._current_custom_graphs().get(panel_name, []) if entry.get("key") in GRAPH_METRIC_OPTIONS]
        return mapping.get(panel_name, [])

    def _set_graph_paused(self, panel_name: str, paused: bool):
        options = self._graph_panel_options.setdefault(panel_name, {"paused": False, "window_s": self._default_graph_window()})
        options["paused"] = paused
        if paused:
            if panel_name in CUSTOM_GRAPH_PANEL_NAMES:
                self._frozen_graph_series[panel_name] = self._custom_graph_series(panel_name)
            else:
                self._frozen_graph_series[panel_name] = self._graph_series_for_panel(panel_name)
        else:
            self._frozen_graph_series.pop(panel_name, None)

    def _clear_graph(self, panel_name: str):
        for metric_name in self._graph_metrics_for_panel(panel_name):
            if metric_name in self.histories:
                self.histories[metric_name].clear()
        self._frozen_graph_series.pop(panel_name, None)

    def _clear_all_graphs(self):
        for series in self.histories.values():
            series.clear()
        self._frozen_graph_series.clear()

    def _set_graph_window(self, panel_name: str, window_s: float):
        options = self._graph_panel_options.setdefault(panel_name, {"paused": False, "window_s": self._default_graph_window()})
        options["window_s"] = max(5.0, float(window_s))
        if options.get("paused"):
            self._set_graph_paused(panel_name, True)

    def _custom_graph_series(self, panel_name: str):
        options = self._graph_panel_options.setdefault(panel_name, {"paused": False, "window_s": self._default_graph_window()})
        series = []
        for entry in self._current_custom_graphs().get(panel_name, []):
            key = entry.get("key")
            if key not in GRAPH_METRIC_OPTIONS:
                continue
            meta = GRAPH_METRIC_OPTIONS[key]
            series.append(
                {
                    "label": meta["label"],
                    "color": entry.get("color", meta["color"]),
                    "points": self._history_points(key, options.get("window_s")),
                    "axis_min": meta.get("axis_min"),
                    "axis_max": meta.get("axis_max"),
                    "decimals": meta.get("decimals", 1),
                }
            )
        return series

    def _graph_series_for_panel(self, panel_name: str):
        window_s = self._graph_panel_options.setdefault(panel_name, {"paused": False, "window_s": self._default_graph_window()}).get("window_s")
        if panel_name == "rpm_trend":
            return [{"label": "rpm", "color": ACCENT, "points": self._history_points("rpm", window_s)}]
        if panel_name == "wheel_trend":
            return [{"label": "wheel", "color": ACCENT, "points": self._history_points("wheel_speed", window_s)}]
        if panel_name == "tps_trend":
            return [{"label": "tps", "color": ACCENT, "points": self._history_points("tps", window_s)}]
        if panel_name == "aps_trend":
            return [{"label": "aps", "color": ACCENT, "points": self._history_points("aps", window_s)}]
        if panel_name == "gear_trend":
            return [{"label": "gear", "color": ACCENT, "points": self._history_points("gear", window_s)}]
        if panel_name == "oil_temp_trend_single":
            return [{"label": "oil temp", "color": ACCENT, "points": self._history_points("oil_temp", window_s)}]
        if panel_name == "coolant_trend":
            return [{"label": "coolant", "color": ACCENT_2, "points": self._history_points("ect", window_s)}]
        if panel_name == "throughput_trend":
            return [{"label": "payload", "color": ACCENT, "points": self._history_points("throughput", window_s)}]
        if panel_name == "lambda_trend":
            return [{"label": "lambda", "color": ACCENT, "points": self._history_points("lambda1", window_s)}]
        if panel_name == "fuel_pressure_trend_single":
            return [{"label": "fuel press", "color": ACCENT_2, "points": self._history_points("fuel_pressure", window_s)}]
        if panel_name == "oil_pressure_trend_single":
            return [{"label": "oil press", "color": ACCENT, "points": self._history_points("oil_pressure", window_s)}]
        if panel_name == "map_trend":
            return [{"label": "map", "color": "#A3E635", "points": self._history_points("map", window_s)}]
        if panel_name == "throttle_trend":
            return [
                {"label": "tps", "color": ACCENT, "points": self._history_points("tps", window_s)},
                {"label": "aps", "color": ACCENT_2, "points": self._history_points("aps", window_s)},
            ]
        if panel_name == "temp_trend":
            return [
                {"label": "oil temp", "color": ACCENT, "points": self._history_points("oil_temp", window_s)},
                {"label": "coolant", "color": ACCENT_2, "points": self._history_points("ect", window_s)},
            ]
        if panel_name == "pressure_trend":
            return [
                {"label": "oil press", "color": ACCENT, "points": self._history_points("oil_pressure", window_s)},
                {"label": "fuel press", "color": ACCENT_2, "points": self._history_points("fuel_pressure", window_s)},
                {"label": "map", "color": "#A3E635", "points": self._history_points("map", window_s)},
            ]
        if panel_name in CUSTOM_GRAPH_PANEL_NAMES:
            return self._custom_graph_series(panel_name)
        return []

    def _refresh(self):
        self.state.animate_metrics()
        alert_level, active_alerts = self._active_alert_state()
        current_titles = self._current_custom_graph_titles()
        for index, panel_name in enumerate(CUSTOM_GRAPH_PANEL_NAMES, start=1):
            widget = self.custom_trend_panels.get(panel_name)
            if widget is not None:
                widget.title = current_titles.get(panel_name, "Custom Graph" if index == 1 else f"Custom Graph {index}")
        if self._panel_visible("wheel_gauge"):
            self.wheel_gauge.set_value(self.state.wheel_speed)
        if self._panel_visible("tps_gauge"):
            self.tps_gauge.set_value(self.state.tps)
        if self._panel_visible("aps_gauge"):
            self.aps_gauge.set_value(self.state.aps)
        if self._panel_visible("oil_temp_gauge"):
            self.oil_temp_gauge.set_value(self.state.oil_temp)
        if self._panel_visible("coolant_gauge"):
            self.coolant_gauge.set_value(self.state.ect)
        if self._panel_visible("rpm_tach"):
            self.rpm_tach.set_value(self.state.rpm)
        if self._panel_visible("lambda_gauge"):
            self.lambda_gauge.set_value(self.state.lambda1)
        if self._panel_visible("map_gauge"):
            self.map_gauge.set_value(self.state.map)
        if self._panel_visible("fuel_pressure_gauge"):
            self.fuel_pressure_gauge.set_value(self.state.fuel_pressure)
        if self._panel_visible("oil_pressure_gauge"):
            self.oil_pressure_gauge.set_value(self.state.oil_pressure)

        age = self.state.data_age_seconds
        if self.serial_worker is None and not self.demo_running:
            link_state = "Disconnected"
            pill_bg = ACCENT_2
        elif self.demo_running:
            link_state = "Demo"
            pill_bg = "#2E7D32"
        elif self.connection_state == "connecting":
            link_state = "Connecting"
            pill_bg = WARNING
        else:
            if age < 1.0:
                link_state = "Connected"
                pill_bg = "#2E7D32"
            else:
                link_state = "No Data"
                pill_bg = WARNING
        self.status_pill.config(text=link_state.upper(), bg=pill_bg)
        self.last_alert_pill.config(text=f"ALERT: {self.last_alert_text}", fg=MUTED if self.last_alert_text == "NONE" else TEXT)
        if active_alerts:
            self.last_alert_text = active_alerts[-1].upper()
            if alert_level == "critical":
                self.critical_bar.config(text="CRITICAL: " + "  |  ".join(active_alerts), bg=DANGER, fg=TEXT)
                self.last_alert_pill.config(bg=DANGER, fg=TEXT)
            else:
                self.critical_bar.config(text="WARNING: " + "  |  ".join(active_alerts), bg=WARNING, fg=BACKGROUND)
                self.last_alert_pill.config(bg=WARNING, fg=BACKGROUND)
            if self.critical_bar.winfo_manager() != "pack":
                self.critical_bar.pack(fill="x", pady=(0, 8), before=self.tab_bar)
            self._set_menu_entry_state(self.session_menu, "Ack Alerts", "normal")
        elif self.critical_bar.winfo_manager() == "pack":
            self.critical_bar.pack_forget()
            self._set_menu_entry_state(self.session_menu, "Ack Alerts", "disabled")
            self.last_alert_pill.config(bg=CARD_BG, fg=MUTED if self.last_alert_text == "NONE" else TEXT)

        gear_text = "--" if self.state.gear.rendered_value is None else str(int(round(self.state.gear.rendered_value)))
        if self._panel_visible("gear_stat"):
            self.gear_stat.set_text(gear_text)
        throughput_value = self.state.throughput.rendered_value
        throughput_text = "PAYLOAD -- kbps" if throughput_value is None else f"PAYLOAD {throughput_value:.1f} kbps"
        self.throughput_pill.config(text=throughput_text)
        halow_value = self.state.halow_link_mbps.rendered_value
        if halow_value is None:
            halow_text = "HALOW -- Mbps"
            halow_fg = MUTED
        else:
            halow_text = f"HALOW {halow_value:.1f} Mbps"
            if self.state.halow_bw_mhz is not None:
                halow_text += f" | {self.state.halow_bw_mhz:g} MHz"
            halow_fg = HALOW_ACCENT
        self.halow_pill.config(text=halow_text, fg=halow_fg)
        self._handle_logging()
        now = time.monotonic()
        if now - self._last_graph_refresh_monotonic >= (self.GRAPH_REFRESH_MS / 1000.0):
            for panel_name, widget in [
                ("rpm_trend", self.rpm_trend),
                ("wheel_trend", self.wheel_trend),
                ("tps_trend", self.tps_trend),
                ("aps_trend", self.aps_trend),
                ("gear_trend", self.gear_trend),
                ("oil_temp_trend_single", self.oil_temp_trend_single),
                ("coolant_trend", self.coolant_trend),
                ("throughput_trend", self.throughput_trend),
                ("lambda_trend", self.lambda_trend),
                ("fuel_pressure_trend_single", self.fuel_pressure_trend_single),
                ("oil_pressure_trend_single", self.oil_pressure_trend_single),
                ("map_trend", self.map_trend),
                ("throttle_trend", self.throttle_trend),
                ("temp_trend", self.temp_trend),
                ("pressure_trend", self.pressure_trend),
            ]:
                if self._panel_visible(panel_name):
                    series = self._frozen_graph_series.get(panel_name) if self._graph_panel_options.get(panel_name, {}).get("paused") else self._graph_series_for_panel(panel_name)
                    widget.set_series(series)
            for panel_name, widget in self.custom_trend_panels.items():
                if self._panel_visible(panel_name):
                    series = self._frozen_graph_series.get(panel_name) if self._graph_panel_options.get(panel_name, {}).get("paused") else self._custom_graph_series(panel_name)
                    widget.set_series(series)
            self._last_graph_refresh_monotonic = now

        self.root.after(self.LIVE_REFRESH_MS, self._refresh)

    def _reset_metric_bounds(self):
        self.state.reset_metric_bounds()

    def _load_logo_image(self):
        if Image is None or ImageTk is None:
            self.header_logo_image = None
            self.tach_logo_image = None
            return

        base_dir = Path(__file__).resolve().parent
        candidate_paths = [
            base_dir / "SDM-FSAE-mark.png",
            base_dir / "SDM-FSAE.jpg",
            base_dir.parent / "assets" / "logos" / "SDM-FSAE-mark.png",
            base_dir.parent / "assets" / "logos" / "SDM-FSAE.jpg",
            base_dir / "assets" / "logos" / "SDM-FSAE-mark.png",
            base_dir / "assets" / "logos" / "SDM-FSAE.jpg",
        ]
        logo_path = next((path for path in candidate_paths if path.exists()), None)
        if logo_path is not None and logo_path.exists():
            logo = Image.open(logo_path)
            if logo.mode != "RGBA":
                logo = logo.convert("RGBA")
            header_logo = logo.copy()
            header_logo.thumbnail((30, 30), Image.Resampling.LANCZOS)
            tach_logo = logo.copy()
            tach_logo.thumbnail((92, 92), Image.Resampling.LANCZOS)
            self.header_logo_image = ImageTk.PhotoImage(header_logo)
            self.tach_logo_image = ImageTk.PhotoImage(tach_logo)
        else:
            self.header_logo_image = None
            self.tach_logo_image = None


def parse_args():
    parser = argparse.ArgumentParser(description="HaLow CAN dashboard for translated ECU/PDM serial output.")
    parser.add_argument("--port", default="COM12", help="Serial port to read, e.g. COM12")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baud rate")
    parser.add_argument("--demo", action="store_true", help="Run with synthetic data instead of serial input")
    return parser.parse_args()


def main():
    args = parse_args()

    root = tk.Tk()
    state = DashboardState()
    line_queue: queue.Queue[str] = queue.Queue()
    DashboardApp(root, state, line_queue, args.port if not args.demo else "DEMO", args.baudrate, initial_demo=args.demo)
    root.mainloop()


if __name__ == "__main__":
    main()
