import argparse
import math
import queue
import random
import re
import threading
import time
import tkinter as tk
from tkinter import colorchooser, simpledialog
from tkinter import ttk
from dataclasses import dataclass, field
from pathlib import Path

try:
    import serial
    from serial import SerialException
except ImportError:  # pragma: no cover - handled at runtime
    serial = None
    SerialException = Exception

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - handled at runtime
    Image = None
    ImageTk = None


BACKGROUND = "#0F1116"
CARD_BG = "#171A21"
CARD_BORDER = "#2A2F3A"
TEXT = "#E7EAF0"
MUTED = "#9DA6B5"
ACCENT = "#FFC627"
ACCENT_2 = "#8C1D40"
WARNING = "#F3C746"
DANGER = "#C25170"
GRID = "#232833"
TRACK = "#242933"

DEFAULT_PANEL_LAYOUTS = {
    "wheel_gauge": {"x": 0.015, "y": 0.04, "w": 0.20, "h": 0.18, "visible": False},
    "tps_gauge": {"x": 0.015, "y": 0.25, "w": 0.20, "h": 0.18, "visible": False},
    "aps_gauge": {"x": 0.015, "y": 0.46, "w": 0.20, "h": 0.18, "visible": False},
    "gear_stat": {"x": 0.015, "y": 0.67, "w": 0.20, "h": 0.18, "visible": False},
    "oil_temp_gauge": {"x": 0.785, "y": 0.04, "w": 0.20, "h": 0.145, "visible": False},
    "coolant_gauge": {"x": 0.785, "y": 0.225, "w": 0.20, "h": 0.145, "visible": False},
    "lambda_gauge": {"x": 0.785, "y": 0.41, "w": 0.20, "h": 0.145, "visible": False},
    "fuel_pressure_gauge": {"x": 0.785, "y": 0.595, "w": 0.20, "h": 0.145, "visible": False},
    "oil_pressure_gauge": {"x": 0.785, "y": 0.78, "w": 0.20, "h": 0.145, "visible": False},
    "rpm_tach": {"x": 0.225, "y": 0.04, "w": 0.55, "h": 0.86, "visible": False},
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
    "throttle_trend": {"x": 0.68, "y": 0.77, "w": 0.30, "h": 0.20, "visible": False},
    "temp_trend": {"x": 0.02, "y": 1.02, "w": 0.48, "h": 0.20, "visible": False},
    "pressure_trend": {"x": 0.52, "y": 1.02, "w": 0.46, "h": 0.20, "visible": False},
    "custom_trend": {"x": 0.20, "y": 0.20, "w": 0.56, "h": 0.28, "visible": False},
}

PANEL_MIN_SIZE = {
    "default": (170, 120),
    "trend": (360, 180),
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
    "fuel_pressure_gauge": {"label": "Fuel Pressure", "section": "live"},
    "oil_pressure_gauge": {"label": "Oil Pressure", "section": "live"},
    "rpm_trend": {"label": "RPM Graph", "section": "graphs"},
    "wheel_trend": {"label": "Wheel Speed Graph", "section": "graphs"},
    "tps_trend": {"label": "TPS Graph", "section": "graphs"},
    "aps_trend": {"label": "APS Graph", "section": "graphs"},
    "gear_trend": {"label": "Gear Graph", "section": "graphs"},
    "oil_temp_trend_single": {"label": "Oil Temp Graph", "section": "graphs"},
    "coolant_trend": {"label": "Coolant Graph", "section": "graphs"},
    "throughput_trend": {"label": "Throughput Graph", "section": "graphs"},
    "lambda_trend": {"label": "Lambda Graph", "section": "graphs"},
    "fuel_pressure_trend_single": {"label": "Fuel Pressure Graph", "section": "graphs"},
    "oil_pressure_trend_single": {"label": "Oil Pressure Graph", "section": "graphs"},
    "throttle_trend": {"label": "Throttle Graph", "section": "graphs"},
    "temp_trend": {"label": "Temp Graph", "section": "graphs"},
    "pressure_trend": {"label": "Pressure Graph", "section": "graphs"},
    "custom_trend": {"label": "Custom Graph", "section": "graphs"},
}

GRAPH_METRIC_OPTIONS = {
    "rpm": {"label": "RPM", "color": ACCENT, "axis_min": 0.0, "axis_max": 15000.0, "decimals": 0},
    "tps": {"label": "TPS", "color": ACCENT, "axis_min": 0.0, "axis_max": 100.0, "decimals": 0},
    "aps": {"label": "APS", "color": ACCENT_2, "axis_min": 0.0, "axis_max": 100.0, "decimals": 0},
    "lambda1": {"label": "Lambda", "color": WARNING, "axis_min": 0.0, "axis_max": 2.0, "decimals": 2},
    "wheel_speed": {"label": "Wheel Speed", "color": "#68D391", "axis_min": 0.0, "axis_max": 220.0, "decimals": 0},
    "gear": {"label": "Gear", "color": "#63B3ED", "axis_min": 0.0, "axis_max": 6.0, "decimals": 0},
    "oil_temp": {"label": "Oil Temp", "color": ACCENT, "axis_min": 0.0, "axis_max": 140.0, "decimals": 0},
    "ect": {"label": "Coolant Temp", "color": ACCENT_2, "axis_min": 0.0, "axis_max": 130.0, "decimals": 0},
    "fuel_pressure": {"label": "Fuel Pressure", "color": "#4FD1C5", "axis_min": 0.0, "axis_max": 200.0, "decimals": 0},
    "oil_pressure": {"label": "Oil Pressure", "color": "#F6AD55", "axis_min": 0.0, "axis_max": 200.0, "decimals": 0},
    "throughput": {"label": "Throughput", "color": "#B794F4", "axis_min": 0.0, "axis_max": 2500.0, "decimals": 0},
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

@dataclass
class Metric:
    value: float | int | None = None
    display_value: float | None = None
    minimum: float | int | None = None
    maximum: float | int | None = None

    def update(self, new_value):
        self.value = new_value
        if self.display_value is None:
            self.display_value = float(new_value)
        if self.minimum is None or new_value < self.minimum:
            self.minimum = new_value
        if self.maximum is None or new_value > self.maximum:
            self.maximum = new_value

    def animate(self, alpha: float):
        if self.value is None:
            return
        target = float(self.value)
        if self.display_value is None:
            self.display_value = target
            return
        delta = target - self.display_value
        if abs(delta) < 0.02:
            self.display_value = target
            return
        self.display_value += delta * alpha

    @property
    def rendered_value(self):
        if self.display_value is not None:
            return self.display_value
        return self.value

    def reset_bounds(self):
        self.minimum = self.value
        self.maximum = self.value


@dataclass
class DashboardState:
    rpm: Metric = field(default_factory=Metric)
    ect: Metric = field(default_factory=Metric)
    oil_temp: Metric = field(default_factory=Metric)
    oil_pressure: Metric = field(default_factory=Metric)
    fuel_pressure: Metric = field(default_factory=Metric)
    lambda1: Metric = field(default_factory=Metric)
    tps: Metric = field(default_factory=Metric)
    aps: Metric = field(default_factory=Metric)
    gear: Metric = field(default_factory=Metric)
    wheel_speed: Metric = field(default_factory=Metric)
    throughput: Metric = field(default_factory=Metric)
    neutral_park: Metric = field(default_factory=Metric)
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
            self.lambda1,
            self.tps,
            self.aps,
            self.gear,
            self.wheel_speed,
            self.throughput,
            self.neutral_park,
        ):
            metric.reset_bounds()

    def animate_metrics(self):
        now = time.monotonic()
        dt = max(0.0, min(0.12, now - self.last_animation_monotonic))
        self.last_animation_monotonic = now
        alpha = 1.0 - math.exp(-dt * 11.0)
        for metric in (
            self.rpm,
            self.ect,
            self.oil_temp,
            self.oil_pressure,
            self.fuel_pressure,
            self.lambda1,
            self.tps,
            self.aps,
            self.gear,
            self.wheel_speed,
            self.throughput,
            self.neutral_park,
        ):
            metric.animate(alpha)

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

    def run(self):
        if self.demo_mode:
            self._run_demo()
            return

        if serial is None:
            self.line_queue.put("ERROR: pyserial is not installed.")
            return

        while True:
            try:
                with serial.Serial(self.port, self.baudrate, timeout=1) as ser:
                    self.line_queue.put(f"INFO: connected to {self.port} @ {self.baudrate}")
                    while True:
                        raw = ser.readline()
                        if not raw:
                            continue
                        line = raw.decode("utf-8", errors="replace").strip()
                        if line:
                            self.line_queue.put(line)
            except SerialException as exc:
                self.line_queue.put(f"ERROR: serial {self.port}: {exc}")
                time.sleep(2.0)

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
            self, text=title, bg=CARD_BG, fg=MUTED, font=("Bahnschrift SemiBold", 15)
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))

        self.min_label = tk.Label(
            self, text="MIN --", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift Condensed", 13)
        )
        self.min_label.grid(row=0, column=1, sticky="e", padx=(8, 18), pady=(14, 0))

        self.value_label = tk.Label(
            self, text="--", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift SemiBold", 34)
        )
        self.value_label.grid(row=1, column=0, sticky="w", padx=18, pady=(4, 0))

        self.max_label = tk.Label(
            self, text="MAX --", bg=CARD_BG, fg=ACCENT, font=("Bahnschrift Condensed", 13)
        )
        self.max_label.grid(row=1, column=1, sticky="ne", padx=(8, 18), pady=(8, 0))

        self.unit_label = tk.Label(
            self, text=unit, bg=CARD_BG, fg=MUTED, font=("Bahnschrift SemiBold", 12)
        )
        self.unit_label.grid(row=2, column=0, sticky="w", padx=18, pady=(8, 16))

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
            self, text=title, bg=CARD_BG, fg=MUTED, font=("Bahnschrift SemiBold", 15)
        )
        self.title_label.pack(anchor="w", padx=18, pady=(14, 8))

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
        self.body_label.pack(fill="both", expand=True, padx=18, pady=(0, 14))

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
        self.value = metric.rendered_value
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
        title_size = max(10, min(19, int(scale * 0.078)))
        value_size = max(18, min(40, int(scale * 0.17)))
        unit_size = max(9, min(13, int(scale * 0.055)))
        footer_size = max(8, min(12, int(scale * 0.041)))
        top_pad = max(8, int(h * 0.04))
        self.canvas.create_text(
            w / 2,
            top_pad,
            anchor="n",
            text=self.title,
            width=w - 18,
            fill=MUTED,
            font=("Bahnschrift SemiBold", title_size),
            justify="center",
        )

        cx = w / 2
        cy = h * 0.61
        r = max(28, min(w * 0.40, h * 0.36))
        bbox = (cx - r, cy - r, cx + r, cy + r)
        start = 150
        extent = 240

        arc_width = max(6, int(scale * 0.065))
        marker_width = max(2, int(scale * 0.015))
        self.canvas.create_arc(bbox, start=start, extent=extent, style="arc", width=arc_width, outline=TRACK)
        self.canvas.create_arc(bbox, start=start, extent=extent * 0.72, style="arc", width=marker_width, outline=ACCENT)
        self.canvas.create_arc(bbox, start=start + extent * 0.72, extent=extent * 0.20, style="arc", width=marker_width, outline=WARNING)
        self.canvas.create_arc(bbox, start=start + extent * 0.92, extent=extent * 0.08, style="arc", width=marker_width, outline=DANGER)

        value = 0.0 if self.value is None else float(self.value)
        progress = max(0.0, min(1.0, value / self.maximum)) if self.maximum else 0.0
        color = ACCENT if progress < 0.72 else WARNING if progress < 0.92 else DANGER
        self.canvas.create_arc(bbox, start=start, extent=extent * progress, style="arc", width=max(5, arc_width - 2), outline=color)

        self.canvas.create_text(cx, cy - r * 0.01, text=self._fmt(self.value), width=max(60, int(r * 1.65)), fill=color, font=("Bahnschrift Bold", value_size), justify="center")
        if self.unit:
            self.canvas.create_text(cx, cy + r * 0.31, text=self.unit, width=max(60, int(r * 1.50)), fill=MUTED, font=("Bahnschrift SemiBold", unit_size), justify="center")
        self.canvas.create_text(
            12,
            h - max(10, int(scale * 0.05)),
            anchor="sw",
            text=f"Min {self._fmt(self.minimum)}",
            width=max(40, int(w * 0.42)),
            fill=MUTED,
            font=("Consolas", footer_size),
            justify="left",
        )
        self.canvas.create_text(
            w - 12,
            h - max(10, int(scale * 0.05)),
            anchor="se",
            text=f"Max {self._fmt(self.maximum_seen)}",
            width=max(40, int(w * 0.42)),
            fill=MUTED,
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
        title_size = max(9, min(17, int(scale * 0.075)))
        value_size = max(15, min(34, int(scale * 0.18)))
        self.canvas.create_text(w / 2, 10, anchor="n", text=self.title, width=w - 20, fill=MUTED, font=("Bahnschrift SemiBold", title_size), justify="center")
        self.canvas.create_text(w / 2, h / 2, text=self.value_text, fill=ACCENT, width=w - 28, font=("Bahnschrift Bold", value_size), justify="center")


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
            signature.append(
                (
                    item.get("label"),
                    item.get("color"),
                    len(points),
                    points[0][1] if points else None,
                    points[-1][1] if points else None,
                )
            )
        return tuple(signature)

    def _draw(self):
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        draw_key = (w, h, self.title, self._series_signature(self.series))
        if draw_key == self._last_draw_key:
            return
        self._last_draw_key = draw_key
        self.canvas.delete("all")
        scale = min(w, h)
        title_size = max(8, min(14, int(scale * 0.045)))
        legend_size = max(6, min(9, int(scale * 0.028)))
        axis_size = max(6, min(9, int(scale * 0.028)))
        self.canvas.create_text(w / 2, 10, anchor="n", text=self.title, width=w - 20, fill=MUTED, font=("Bahnschrift SemiBold", title_size), justify="center")

        left, top, right, bottom = 42, 34, w - 14, h - 34
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
            self.canvas.create_text(w / 2, h / 2, text="No data", fill=MUTED, font=("Bahnschrift SemiBold", max(12, title_size + 1)))
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

        max_len = max(len(item["points"]) for item in self.series)
        max_len = max(2, max_len)

        for item in self.series:
            points = item["points"]
            if len(points) < 2:
                continue
            coords = []
            start_index = max_len - len(points)
            for index, (_, value) in enumerate(points):
                x = left + plot_w * ((start_index + index) / (max_len - 1))
                y = bottom - plot_h * ((value - min_value) / (max_value - min_value))
                coords.extend((x, y))
            self.canvas.create_line(*coords, fill=item["color"], width=2, smooth=True)

        legend_x = left
        for item in self.series:
            self.canvas.create_rectangle(legend_x, h - 16, legend_x + 10, h - 6, fill=item["color"], outline=item["color"])
            self.canvas.create_text(legend_x + 16, h - 11, anchor="w", text=item["label"], fill=MUTED, font=("Consolas", legend_size))
            legend_x += max(72, min(120, int(w * 0.17)))


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
        title_size = max(8, min(14, int(scale * 0.045)))
        legend_size = max(6, min(9, int(scale * 0.028)))
        axis_size = max(6, min(9, int(scale * 0.027)))
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
                text="No metrics selected",
                fill=MUTED,
                font=("Bahnschrift SemiBold", max(12, title_size + 1)),
            )
            return

        left_axis_count = (len(self.series) + 1) // 2
        right_axis_count = len(self.series) // 2
        outer_margin = 14
        axis_lane = 68
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

        max_len = max(max(len(item["points"]), 2) for item in self.series)

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

            max_plot_points = max(40, int(plot_w / 3))
            if len(points) > max_plot_points:
                stride = max(1, len(points) // max_plot_points)
                points = points[::stride]
                if points[-1] != item["points"][-1]:
                    points.append(item["points"][-1])

            coords = []
            start_index = max_len - len(points)
            for point_index, (_, value) in enumerate(points):
                x = left + plot_w * ((start_index + point_index) / (max_len - 1))
                y = bottom - plot_h * ((value - axis_min) / (axis_max - axis_min))
                coords.extend((x, y))
            self.canvas.create_line(*coords, fill=item["color"], width=2, smooth=True)

        legend_x = left
        for item in self.series:
            self.canvas.create_rectangle(legend_x, h - 16, legend_x + 10, h - 6, fill=item["color"], outline=item["color"])
            self.canvas.create_text(legend_x + 16, h - 11, anchor="w", text=item["label"], fill=MUTED, font=("Consolas", legend_size))
            legend_x += max(88, min(150, int(w * 0.20)))


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
        title_size = max(9, min(17, int(scale * 0.072)))
        value_size = max(14, min(38, int(scale * 0.165)))
        top_pad = max(6, int(h * 0.02))
        self.canvas.create_text(w / 2, top_pad, anchor="n", text=self.title, width=w - 24, fill=MUTED, font=("Bahnschrift SemiBold", title_size), justify="center")

        cx = w / 2
        cy = h * 0.59
        r = max(36, min(w * 0.43, h * 0.42))
        bbox = (cx - r, cy - r, cx + r, cy + r)
        arc_width = max(6, int(scale * 0.065))
        start_deg = 210
        sweep_deg = -240

        self.canvas.create_arc(bbox, start=start_deg, extent=sweep_deg, style="arc", width=arc_width, outline=TRACK)

        rpm = 0.0 if self.rpm_value is None else float(self.rpm_value)
        progress = max(0.0, min(1.0, rpm / self.maximum)) if self.maximum else 0.0
        color = ACCENT if progress < 0.80 else WARNING if progress < 0.92 else DANGER
        self.canvas.create_arc(bbox, start=start_deg, extent=sweep_deg * progress, style="arc", width=max(5, arc_width - 2), outline=color)

        major_ticks = 8
        minor_per_major = 4
        inner_major = r - max(18, int(scale * 0.10))
        inner_minor = r - max(12, int(scale * 0.07))
        outer_tick = r - max(3, int(scale * 0.02))
        label_radius = r - max(34, int(scale * 0.18))

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
            self.canvas.create_line(x1, y1, x2, y2, fill=tick_color, width=2 if is_major else 1)

            if is_major:
                label_value = int((self.maximum / 1000.0) * fraction)
                lx = cx + math.cos(angle_rad) * label_radius
                ly = cy - math.sin(angle_rad) * label_radius
                self.canvas.create_text(
                    lx,
                    ly,
                    text=str(label_value),
                    fill=MUTED,
                    font=("Bahnschrift SemiBold", max(7, int(scale * 0.04))),
                )

        needle_angle_deg = start_deg + sweep_deg * progress
        needle_angle = math.radians(needle_angle_deg)
        needle_length = r - max(28, int(scale * 0.16))
        tail_length = max(10, int(scale * 0.06))
        nx = cx + math.cos(needle_angle) * needle_length
        ny = cy - math.sin(needle_angle) * needle_length
        tx = cx - math.cos(needle_angle) * tail_length
        ty = cy + math.sin(needle_angle) * tail_length
        self.canvas.create_line(tx, ty, nx, ny, fill=color, width=max(3, int(scale * 0.018)))
        self.canvas.create_oval(
            cx - max(7, int(scale * 0.03)),
            cy - max(7, int(scale * 0.03)),
            cx + max(7, int(scale * 0.03)),
            cy + max(7, int(scale * 0.03)),
            fill=TEXT,
            outline="",
        )

        if self.logo_image is not None:
            self.canvas.create_image(cx, cy + max(18, int(scale * 0.08)), image=self.logo_image)

        self.canvas.create_text(
            cx,
            h * 0.79,
            text=f"{int(round(rpm)) if self.rpm_value is not None else '--'}",
            width=w - 20,
            fill=TEXT,
            font=("Bahnschrift Bold", value_size),
            justify="center",
        )
        self.canvas.create_text(
            cx,
            h * 0.90,
            text="x1000 rpm",
            width=w - 20,
            fill=MUTED,
            font=("Consolas", max(7, title_size - 2)),
            justify="center",
        )


class DashboardApp:
    HISTORY_LIMIT = 180
    LIVE_REFRESH_MS = 45
    GRAPH_REFRESH_MS = 180

    def __init__(self, root: tk.Tk, state: DashboardState, line_queue: queue.Queue[str], port_label: str, initial_demo: bool = False):
        self.root = root
        self.state = state
        self.line_queue = line_queue
        self.port_label = port_label
        self.logo_image = None
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
        self._tab_signature = ()
        self._secret_buffer = ""
        self._easter_egg_after_id = None
        self._easter_egg_start = 0.0
        self.settings_dialog = None
        self.settings_model = self._build_default_settings_model()
        self.critical_limits = {
            "rpm": {"label": "RPM", "low": "", "high": ""},
            "ect": {"label": "Coolant Temp", "low": "", "high": ""},
            "oil_temp": {"label": "Oil Temp", "low": "", "high": ""},
            "oil_pressure": {"label": "Oil Pressure", "low": "", "high": ""},
            "fuel_pressure": {"label": "Fuel Pressure", "low": "", "high": ""},
            "lambda1": {"label": "Lambda", "low": "", "high": ""},
            "tps": {"label": "TPS", "low": "", "high": ""},
            "aps": {"label": "APS", "low": "", "high": ""},
            "gear": {"label": "Gear", "low": "", "high": ""},
            "wheel_speed": {"label": "Wheel Speed", "low": "", "high": ""},
            "throughput": {"label": "Throughput", "low": "", "high": ""},
        }
        self.critical_limit_vars = {}
        self.histories = {
            "rpm": [],
            "tps": [],
            "aps": [],
            "oil_temp": [],
            "ect": [],
            "oil_pressure": [],
            "fuel_pressure": [],
            "wheel_speed": [],
            "gear": [],
            "lambda1": [],
            "throughput": [],
        }

        self.root.title("HaLow CAN Dashboard")
        self.root.configure(bg=BACKGROUND)
        self.root.geometry("1600x920")
        self.root.minsize(1400, 860)

        outer = tk.Frame(root, bg=BACKGROUND)
        outer.pack(fill="both", expand=True, padx=12, pady=12)
        self.outer = outer

        header = tk.Frame(outer, bg=BACKGROUND)
        header.pack(fill="x", pady=(0, 10))

        self._load_logo_image()
        if self.logo_image is not None:
            tk.Label(header, image=self.logo_image, bg=BACKGROUND).pack(side="left", padx=(0, 10))

        title_wrap = tk.Frame(header, bg=BACKGROUND)
        title_wrap.pack(side="left")
        tk.Label(
            title_wrap,
            text="General  /  SDM Telemetry Client Go",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Bahnschrift SemiBold", 17),
        ).pack(anchor="w")

        self.settings_button = tk.Button(
            header,
            text="⚙",
            command=self._open_settings_dialog,
            bg=CARD_BG,
            fg=ACCENT,
            activebackground=CARD_BORDER,
            activeforeground=ACCENT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            font=("Bahnschrift Bold", 14),
            padx=10,
            pady=6,
            cursor="hand2",
        )
        self.settings_button.pack(side="right", padx=(0, 8))

        self.reset_button = tk.Button(
            header,
            text="Reset Min/Max",
            command=self._reset_metric_bounds,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BORDER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            font=("Bahnschrift SemiBold", 11),
            padx=12,
            pady=8,
            cursor="hand2",
        )
        self.reset_button.pack(side="right")

        self.stop_demo_button = tk.Button(
            header,
            text="Stop Demo",
            command=self._stop_demo_mode,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BORDER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            font=("Bahnschrift SemiBold", 11),
            padx=12,
            pady=8,
            cursor="hand2",
            state="disabled",
        )
        self.stop_demo_button.pack(side="right", padx=(0, 8))

        self.start_demo_button = tk.Button(
            header,
            text="Start Demo",
            command=self._start_demo_mode,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BORDER,
            activeforeground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            font=("Bahnschrift SemiBold", 11),
            padx=12,
            pady=8,
            cursor="hand2",
        )
        self.start_demo_button.pack(side="right", padx=(0, 8))

        self.port_pill = tk.Label(
            header,
            text=self.port_label,
            bg=CARD_BG,
            fg=TEXT,
            font=("Consolas", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.port_pill.pack(side="right", padx=(0, 10))

        self.throughput_pill = tk.Label(
            header,
            text="-- kbps",
            bg=CARD_BG,
            fg=ACCENT,
            font=("Consolas", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.throughput_pill.pack(side="right", padx=(0, 10))

        self.status_pill = tk.Label(
            header,
            text="OFFLINE",
            bg=ACCENT_2,
            fg=TEXT,
            font=("Consolas", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.status_pill.pack(side="right", padx=(0, 10))

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

        self.lambda_gauge = GaugePanel(self.dashboard, "Lambda", "ratio", maximum=2.0, decimals=2)
        self.fuel_pressure_gauge = GaugePanel(self.dashboard, "Fuel Pressure", "raw", maximum=200)
        self.oil_pressure_gauge = GaugePanel(self.dashboard, "Oil Pressure", "raw", maximum=200)

        self.rpm_trend = TrendPanel(self.dashboard, "RPM Graph")
        self.wheel_trend = TrendPanel(self.dashboard, "Wheel Speed Graph")
        self.tps_trend = TrendPanel(self.dashboard, "TPS Graph")
        self.aps_trend = TrendPanel(self.dashboard, "APS Graph")
        self.gear_trend = TrendPanel(self.dashboard, "Gear Graph")
        self.oil_temp_trend_single = TrendPanel(self.dashboard, "Oil Temp Graph")
        self.coolant_trend = TrendPanel(self.dashboard, "Coolant Graph")
        self.throughput_trend = TrendPanel(self.dashboard, "Throughput Graph")
        self.lambda_trend = TrendPanel(self.dashboard, "Lambda Graph")
        self.fuel_pressure_trend_single = TrendPanel(self.dashboard, "Fuel Pressure Graph")
        self.oil_pressure_trend_single = TrendPanel(self.dashboard, "Oil Pressure Graph")
        self.throttle_trend = TrendPanel(self.dashboard, "Throttle Graph")
        self.temp_trend = TrendPanel(self.dashboard, "Temp Graph")
        self.pressure_trend = TrendPanel(self.dashboard, "Pressure Graph")
        self.custom_trend = CustomTrendPanel(self.dashboard, "Custom Graph", lambda: self._configure_custom_graph("custom_trend"))
        self.rpm_tach = TachPanel(self.dashboard, "Engine Speed", RPM_MAX)
        self.rpm_tach.set_logo(self.logo_image)
        self._register_panel("wheel_gauge", self.wheel_gauge)
        self._register_panel("tps_gauge", self.tps_gauge)
        self._register_panel("aps_gauge", self.aps_gauge)
        self._register_panel("gear_stat", self.gear_stat)
        self._register_panel("oil_temp_gauge", self.oil_temp_gauge)
        self._register_panel("coolant_gauge", self.coolant_gauge)
        self._register_panel("lambda_gauge", self.lambda_gauge)
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
        self._register_panel("throttle_trend", self.throttle_trend)
        self._register_panel("temp_trend", self.temp_trend)
        self._register_panel("pressure_trend", self.pressure_trend)
        self._register_panel("custom_trend", self.custom_trend)
        self._register_panel("rpm_tach", self.rpm_tach)

        self._seed_default_tabs()

        self.root.after(20, self._poll_lines)
        self.root.after(self.LIVE_REFRESH_MS, self._refresh)
        self.root.bind_all("<KeyPress>", self._handle_secret_keypress, add="+")
        if initial_demo:
            self._start_demo_mode()

    def _register_panel(self, name: str, widget: tk.Widget):
        self.panel_widgets[name] = widget
        self._bind_panel_drag(widget, name)
        handle = tk.Frame(self.dashboard, bg=ACCENT, width=14, height=14, cursor="size_nw_se")
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
        if panel_name == "custom_trend":
            widget.bind("<Button-3>", lambda event, panel=panel_name: self._show_custom_graph_menu(event, panel), add="+")
        for child in widget.winfo_children():
            self._bind_panel_drag(child, panel_name)

    def _default_layout_copy(self):
        layout = {}
        for index, name in enumerate(PANEL_DEFS):
            if name in DEFAULT_PANEL_LAYOUTS:
                layout[name] = DEFAULT_PANEL_LAYOUTS[name].copy()
            else:
                if PANEL_DEFS[name]["section"] == "graphs":
                    layout[name] = {"x": 0.04, "y": 0.06 + (index % 4) * 0.06, "w": 0.44, "h": 0.22, "visible": False}
                else:
                    layout[name] = {"x": 0.06 + (index % 4) * 0.08, "y": 0.06 + (index % 4) * 0.05, "w": 0.18, "h": 0.18, "visible": False}
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
        cell_h = 0.40
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

    def _create_tab(self, name: str, layout: dict, select: bool):
        tab_id = f"tab_{len(self.tab_order) + 1}"
        self.tabs[tab_id] = {
            "name": name,
            "layout": layout,
            "custom_graphs": {"custom_trend": []},
            "custom_graph_titles": {"custom_trend": "Custom Graph"},
        }
        self.tab_order.append(tab_id)
        if select or self.current_tab_id is None:
            self.current_tab_id = tab_id
        return tab_id

    def _add_tab(self, initial: bool = False):
        tab_index = len(self.tab_order) + 1
        layout = self._live_layout_copy() if initial else self._blank_layout_copy()
        self._create_tab(f"TAB{tab_index}", layout, select=True)
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()

    def _select_tab(self, tab_id: str):
        if tab_id not in self.tabs:
            return
        self.current_tab_id = tab_id
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()

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
                    bg=BACKGROUND,
                    highlightthickness=1,
                    highlightbackground=CARD_BORDER,
                )
                button.pack(side="left", padx=(0, 8))
                label = tk.Label(
                    button,
                    text=self.tabs[tab_id]["name"],
                    bg=BACKGROUND,
                    fg=MUTED,
                    font=("Bahnschrift SemiBold", 11),
                    padx=14,
                    pady=6,
                    cursor="hand2",
                )
                label.pack()
                for widget in (button, label):
                    widget.bind("<Button-1>", lambda event, t=tab_id: self._select_tab(t))
                    widget.bind("<Double-Button-1>", lambda event, t=tab_id: self._start_tab_rename(t))
                    widget.bind("<Button-3>", lambda event, t=tab_id: self._show_tab_menu(event, t))
                self.tab_buttons[tab_id] = button
                self.tab_labels[tab_id] = label

            plus = tk.Button(
                self.tab_bar,
                text="+",
                command=self._add_tab,
                bg=CARD_BG,
                fg=ACCENT,
                activebackground=CARD_BG,
                activeforeground=ACCENT,
                relief="flat",
                highlightthickness=1,
                highlightbackground=CARD_BORDER,
                font=("Bahnschrift Bold", 12),
                padx=12,
                pady=6,
                cursor="hand2",
            )
            plus.pack(side="left")
            self._tab_signature = signature

        for tab_id in self.tab_order:
            is_active = tab_id == self.current_tab_id
            button = self.tab_buttons[tab_id]
            label = self.tab_labels[tab_id]
            button.config(bg=CARD_BG if is_active else BACKGROUND)
            label.config(
                text=self.tabs[tab_id]["name"],
                bg=CARD_BG if is_active else BACKGROUND,
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
        return self.tabs[self.current_tab_id].setdefault("custom_graphs", {"custom_trend": []})

    def _current_custom_graph_titles(self):
        if self.current_tab_id is None:
            return {}
        return self.tabs[self.current_tab_id].setdefault("custom_graph_titles", {"custom_trend": "Custom Graph"})

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
        self._drag_state = None
        self._resize_state = None

    def _start_resize(self, event, panel_name: str):
        if not self.edit_mode:
            return
        layout = self._current_layout()
        if panel_name not in layout:
            return
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
            layout[panel_name]["visible"] = False
            self._layout_panels()
            self._populate_drawer()

    def _show_panel(self, panel_name: str):
        layout = self._current_layout()
        if panel_name in layout:
            layout[panel_name]["visible"] = True
            self._layout_panels()
            self._populate_drawer()

    def _configure_custom_graph(self, panel_name: str):
        current_entries = self._current_custom_graphs().get(panel_name, [])
        current_map = {entry["key"]: entry["color"] for entry in current_entries if "key" in entry and "color" in entry}

        dialog = tk.Toplevel(self.root)
        dialog.title("Custom Graph")
        dialog.configure(bg=BACKGROUND)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

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
            selected = []
            for metric_key in GRAPH_METRIC_OPTIONS:
                if selections[metric_key].get():
                    selected.append({"key": metric_key, "color": colors[metric_key].get()})
            self._current_custom_graphs()[panel_name] = selected
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
        current_title = self._current_custom_graph_titles().get(panel_name, "Custom Graph")
        new_name = simpledialog.askstring("Rename Graph", "Graph name:", initialvalue=current_title, parent=self.root)
        if not new_name:
            return
        updated = new_name.strip() or current_title
        self._current_custom_graph_titles()[panel_name] = updated
        widget = self.panel_widgets.get(panel_name)
        if widget is not None:
            widget.title = updated
            if self._panel_visible(panel_name):
                widget._draw()

    def _show_custom_graph_menu(self, event, panel_name: str):
        menu = tk.Menu(self.root, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=CARD_BORDER, activeforeground=TEXT)
        menu.add_command(label="Rename Graph", command=lambda p=panel_name: self._rename_custom_graph(p))
        menu.add_command(label="Edit Metrics", command=lambda p=panel_name: self._configure_custom_graph(p))
        menu.tk_popup(event.x_root, event.y_root)

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
        return {
            "mode": {
                "can_module": "CAN 2",
                "mode": "User Defined",
                "bit_rate": "1 Mbit/s",
                "obd": "OFF",
                "channels": [
                    {"name": "1: Link Razor PDM", "mode": "Link Razor PDM", "can_id": "500", "rate": "20 Hz", "format": "Normal"},
                    {"name": "2: Transmit User Stream 2", "mode": "Transmit User Stream 2", "can_id": "1000", "rate": "20 Hz", "format": "Normal"},
                    {"name": "3: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                    {"name": "4: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                    {"name": "5: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                    {"name": "6: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
                    {"name": "7: OFF", "mode": "OFF", "can_id": "", "rate": "", "format": "Normal"},
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
            self.critical_limits[metric_key]["low"] = bounds["low"].get().strip()
            self.critical_limits[metric_key]["high"] = bounds["high"].get().strip()

    def _metric_current_value(self, metric_key: str):
        metric = getattr(self.state, metric_key, None)
        if metric is None:
            return None
        if metric.value is not None:
            return float(metric.value)
        if metric.rendered_value is not None:
            return float(metric.rendered_value)
        return None

    def _active_critical_alerts(self):
        self._sync_critical_limits_from_vars()
        alerts = []
        for metric_key, bounds in self.critical_limits.items():
            value = self._metric_current_value(metric_key)
            if value is None:
                continue
            label = bounds["label"]
            low_raw = bounds.get("low", "")
            high_raw = bounds.get("high", "")
            try:
                low = float(low_raw) if str(low_raw).strip() != "" else None
            except ValueError:
                low = None
            try:
                high = float(high_raw) if str(high_raw).strip() != "" else None
            except ValueError:
                high = None
            if low is not None and value < low:
                alerts.append(f"{label} low")
            if high is not None and value > high:
                alerts.append(f"{label} high")
        return alerts

    def _open_settings_dialog(self):
        if self.settings_dialog is not None and self.settings_dialog.winfo_exists():
            self.settings_dialog.deiconify()
            self.settings_dialog.lift()
            self.settings_dialog.focus_force()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("CAN Setup")
        dialog.configure(bg=BACKGROUND)
        dialog.transient(self.root)
        dialog.geometry("920x560")
        dialog.minsize(860, 520)
        dialog.protocol("WM_DELETE_WINDOW", dialog.withdraw)
        self.settings_dialog = dialog

        style = ttk.Style(dialog)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Pclink.TNotebook", background=BACKGROUND, borderwidth=0)
        style.configure("Pclink.TNotebook.Tab", padding=(10, 6), font=("Bahnschrift SemiBold", 10))
        style.configure("Pclink.Treeview", rowheight=22, font=("Consolas", 10))
        style.configure("Pclink.Treeview.Heading", font=("Bahnschrift SemiBold", 10))

        wrapper = tk.Frame(dialog, bg="#E7E7E7")
        wrapper.pack(fill="both", expand=True, padx=10, pady=10)

        notebook = ttk.Notebook(wrapper, style="Pclink.TNotebook")
        notebook.pack(fill="both", expand=True)

        mode_tab = tk.Frame(notebook, bg="#F2F2F2")
        streams_tab = tk.Frame(notebook, bg="#F2F2F2")
        critical_tab = tk.Frame(notebook, bg="#F2F2F2")
        notebook.add(mode_tab, text="Mode")
        notebook.add(streams_tab, text="Streams")
        notebook.add(critical_tab, text="Critical")

        mode_model = self.settings_model["mode"]
        streams_model = self.settings_model["streams"]

        mode_data = tk.LabelFrame(mode_tab, text="Data", bg="#F2F2F2", padx=10, pady=8)
        mode_data.pack(fill="both", expand=True, padx=10, pady=10)

        channel_list = tk.Listbox(mode_data, exportselection=False, width=28, height=12)
        channel_list.grid(row=0, column=0, rowspan=5, sticky="nsw", padx=(0, 14))

        for item in mode_model["channels"]:
            channel_list.insert("end", item["name"])

        tk.Label(mode_data, text="Mode", bg="#F2F2F2").grid(row=0, column=1, sticky="w")
        channel_mode_var = tk.StringVar()
        channel_mode_combo = ttk.Combobox(mode_data, values=["OFF", "Link Razor PDM", "Transmit User Stream 2", "Receive User Stream 3", "Receive User Stream 4"], textvariable=channel_mode_var, width=22)
        channel_mode_combo.grid(row=0, column=2, sticky="w", padx=(8, 24))

        tk.Label(mode_data, text="CAN ID", bg="#F2F2F2").grid(row=0, column=3, sticky="w")
        channel_id_entry = tk.Entry(mode_data, width=12)
        channel_id_entry.grid(row=0, column=4, sticky="w", padx=(8, 24))

        tk.Label(mode_data, text="Format", bg="#F2F2F2").grid(row=1, column=1, sticky="w", pady=(12, 0))
        channel_format_var = tk.StringVar()
        format_box = tk.Frame(mode_data, bg="#F2F2F2")
        format_box.grid(row=1, column=2, columnspan=3, sticky="w", padx=(8, 0), pady=(12, 0))
        tk.Radiobutton(format_box, text="Normal", value="Normal", variable=channel_format_var, bg="#F2F2F2").pack(anchor="w")
        tk.Radiobutton(format_box, text="Extended", value="Extended", variable=channel_format_var, bg="#F2F2F2").pack(anchor="w")

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

        mode_actions = tk.Frame(mode_data, bg="#F2F2F2")
        mode_actions.grid(row=2, column=1, columnspan=4, sticky="w", pady=(18, 0))
        for text, command in (("Save Channel", save_channel), ("Add Channel", add_channel), ("Delete Channel", delete_channel)):
            tk.Button(mode_actions, text=text, command=command, bg="#E9E9E9", relief="raised", padx=10, pady=4).pack(side="left", padx=(0, 8))

        mode_data.columnconfigure(2, weight=1)
        mode_data.columnconfigure(4, weight=1)

        streams_left = tk.Frame(streams_tab, bg="#F2F2F2")
        streams_left.pack(fill="both", expand=True, padx=10, pady=10)

        stream_tree = ttk.Treeview(streams_left, style="Pclink.Treeview", show="tree", selectmode="browse", height=18)
        stream_tree.grid(row=0, column=0, rowspan=4, sticky="nsw", padx=(0, 12))

        def refresh_stream_tree():
            stream_tree.delete(*stream_tree.get_children())
            for stream_name, frames in streams_model.items():
                stream_id = stream_tree.insert("", "end", text=stream_name, open=True)
                for frame_name in frames.keys():
                    stream_tree.insert(stream_id, "end", text=frame_name)

        refresh_stream_tree()

        frame_meta_box = tk.LabelFrame(streams_left, text="Frame", bg="#F2F2F2", padx=10, pady=8)
        frame_meta_box.grid(row=0, column=1, sticky="new")
        frame_size_var = tk.StringVar()
        id_position_var = tk.StringVar()
        id_decimal_var = tk.StringVar()
        for idx, (label, var) in enumerate((("Frame Size", frame_size_var), ("ID Position", id_position_var), ("ID (decimal)", id_decimal_var))):
            tk.Label(frame_meta_box, text=label, bg="#F2F2F2").grid(row=0, column=idx * 2, sticky="w")
            tk.Entry(frame_meta_box, textvariable=var, width=8).grid(row=0, column=idx * 2 + 1, sticky="w", padx=(6, 14))

        stream_actions = tk.Frame(streams_left, bg="#F2F2F2")
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

        param_editor = tk.LabelFrame(streams_left, text="Parameters", bg="#F2F2F2", padx=10, pady=8)
        param_editor.grid(row=3, column=1, sticky="ew", pady=(10, 0))
        param_vars = {key: tk.StringVar() for key in ("name", "start", "width", "byte_order", "type", "multiply", "divider", "offset")}
        editor_fields = [("name", "Parameter"), ("start", "Start"), ("width", "Width"), ("byte_order", "Byte Order"), ("type", "Type"), ("multiply", "Multiply"), ("divider", "Divider"), ("offset", "Offset")]
        for idx, (key, label) in enumerate(editor_fields):
            row = idx // 4
            col = (idx % 4) * 2
            tk.Label(param_editor, text=label, bg="#F2F2F2").grid(row=row, column=col, sticky="w", padx=(0, 6), pady=4)
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
            tk.Button(stream_actions, text=text, command=command, bg="#E9E9E9", relief="raised", padx=10, pady=4).pack(side="left", padx=(0, 8))

        param_actions = tk.Frame(param_editor, bg="#F2F2F2")
        param_actions.grid(row=2, column=0, columnspan=8, sticky="w", pady=(10, 0))
        for text, command in (("Add Param", add_param), ("Save Param", save_param), ("Delete Param", delete_param)):
            tk.Button(param_actions, text=text, command=command, bg="#E9E9E9", relief="raised", padx=10, pady=4).pack(side="left", padx=(0, 8))

        stream_tree.bind("<<TreeviewSelect>>", on_tree_select)
        param_tree.bind("<<TreeviewSelect>>", on_param_select)
        first_stream = next(iter(streams_model))
        first_frame = next(iter(streams_model[first_stream]))
        selected_frame["stream"] = first_stream
        selected_frame["frame"] = first_frame
        refresh_param_tree()

        streams_left.columnconfigure(1, weight=1)
        streams_left.rowconfigure(2, weight=1)

        critical_wrap = tk.Frame(critical_tab, bg="#F2F2F2")
        critical_wrap.pack(fill="both", expand=True, padx=10, pady=10)

        critical_box = tk.LabelFrame(
            critical_wrap,
            text="Critical Limits",
            bg="#F2F2F2",
            padx=12,
            pady=10,
        )
        critical_box.pack(fill="both", expand=True)

        tk.Label(
            critical_box,
            text="Set low/high alarm thresholds for each metric. Leave a field blank to disable that threshold.",
            bg="#F2F2F2",
            fg="#333333",
            font=("Bahnschrift", 10),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        tk.Label(critical_box, text="Metric", bg="#F2F2F2", font=("Bahnschrift SemiBold", 10)).grid(row=1, column=0, sticky="w", padx=(0, 10))
        tk.Label(critical_box, text="Low", bg="#F2F2F2", font=("Bahnschrift SemiBold", 10)).grid(row=1, column=1, sticky="w", padx=(0, 10))
        tk.Label(critical_box, text="High", bg="#F2F2F2", font=("Bahnschrift SemiBold", 10)).grid(row=1, column=2, sticky="w")

        self.critical_limit_vars = {}
        for row_index, (metric_key, config) in enumerate(self.critical_limits.items(), start=2):
            low_var = tk.StringVar(value=str(config.get("low", "")))
            high_var = tk.StringVar(value=str(config.get("high", "")))
            self.critical_limit_vars[metric_key] = {"low": low_var, "high": high_var}

            tk.Label(
                critical_box,
                text=config["label"],
                bg="#F2F2F2",
                fg="#222222",
                font=("Bahnschrift", 10),
            ).grid(row=row_index, column=0, sticky="w", pady=4, padx=(0, 10))
            tk.Entry(critical_box, textvariable=low_var, width=12).grid(row=row_index, column=1, sticky="w", pady=4, padx=(0, 10))
            tk.Entry(critical_box, textvariable=high_var, width=12).grid(row=row_index, column=2, sticky="w", pady=4)

            low_var.trace_add("write", lambda *_args: self._sync_critical_limits_from_vars())
            high_var.trace_add("write", lambda *_args: self._sync_critical_limits_from_vars())

        critical_box.columnconfigure(0, weight=1)

        footer = tk.Frame(wrapper, bg="#E7E7E7")
        footer.pack(fill="x", pady=(8, 0))
        tk.Button(footer, text="Apply", bg="#E9E9E9", relief="raised", padx=10, pady=4).pack(side="right", padx=(0, 8))
        tk.Button(footer, text="OK", command=dialog.withdraw, bg="#E9E9E9", relief="raised", padx=10, pady=4).pack(side="right", padx=(0, 8))
        tk.Button(footer, text="Cancel", command=dialog.withdraw, bg="#E9E9E9", relief="raised", padx=10, pady=4).pack(side="right", padx=(0, 8))

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

        pulse = 0.5 + 0.5 * math.sin(elapsed * 7.5)
        jitter_x = math.sin(elapsed * 36.0) * 6.0
        jitter_y = math.cos(elapsed * 28.0) * 4.0
        font_size = int(64 + 18 * pulse)
        flash_on = int(elapsed * 8.0) % 2 == 0
        color = DANGER if flash_on else ACCENT

        self.easter_egg_label.config(
            fg=color,
            font=("Bahnschrift Bold", font_size),
        )
        self.easter_egg_label.place(relx=0.5, rely=0.5, anchor="center", x=int(jitter_x), y=int(jitter_y))
        self._easter_egg_after_id = self.root.after(33, self._animate_easter_egg)

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
            self.tabs[tab_id]["name"] = new_name.strip() or self.tabs[tab_id]["name"]
            self._render_tab_buttons()

    def _remove_tab(self, tab_id: str):
        if tab_id not in self.tabs or len(self.tab_order) <= 1:
            return
        remove_index = self.tab_order.index(tab_id)
        self.tab_order.remove(tab_id)
        del self.tabs[tab_id]
        if self.current_tab_id == tab_id:
            fallback_index = max(0, remove_index - 1)
            self.current_tab_id = self.tab_order[fallback_index]
        self._render_tab_buttons()
        self._populate_drawer()
        self._layout_panels()

    def _show_tab_menu(self, event, tab_id: str):
        self._select_tab(tab_id)
        menu = tk.Menu(self.root, tearoff=0, bg=CARD_BG, fg=TEXT, activebackground=CARD_BORDER, activeforeground=TEXT)
        menu.add_command(label="Rename Tab", command=lambda t=tab_id: self._start_tab_rename(t))
        if len(self.tab_order) > 1:
            menu.add_command(label="Remove Tab", command=lambda t=tab_id: self._remove_tab(t))
        else:
            menu.add_command(label="Remove Tab", state="disabled")
        menu.tk_popup(event.x_root, event.y_root)

    def _start_demo_mode(self):
        if self.demo_running:
            return
        self.demo_running = True
        self.demo_rpm = 1800
        self.demo_direction = 1
        self.start_demo_button.config(state="disabled")
        self.stop_demo_button.config(state="normal")
        self._queue_demo_line()

    def _stop_demo_mode(self):
        self.demo_running = False
        if self.demo_after_id is not None:
            self.root.after_cancel(self.demo_after_id)
            self.demo_after_id = None
        self.start_demo_button.config(state="normal")
        self.stop_demo_button.config(state="disabled")

    def _queue_demo_line(self):
        if not self.demo_running:
            self.demo_after_id = None
            return

        self.demo_rpm += self.demo_direction * random.randint(120, 320)
        if self.demo_rpm > 11200:
            self.demo_direction = -1
        elif self.demo_rpm < 1800:
            self.demo_direction = 1

        rpm = self.demo_rpm
        ect = random.randint(82, 95)
        oil_temp = random.randint(88, 108)
        oil_pressure = random.randint(28, 78)
        neutral_park = 1 if rpm < 2200 else 0
        lambda1 = random.randint(88, 105)
        tps = max(0, min(100, int((rpm / 15000) * 100) + random.randint(-4, 4)))
        aps = max(0, min(100, tps + random.randint(-3, 3)))
        gear = random.randint(2, 5)
        wheel_speed = max(0, int((rpm / 120.0) + random.randint(-3, 3)))
        fuel_pressure = random.randint(35, 72)

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
        )
        self.demo_after_id = self.root.after(180, self._queue_demo_line)

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
            self._apply_line(line)
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

    def _apply_line(self, line: str):
        self.state.touch(line)
        self._record_rx_throughput(line)
        line = self._normalize_line(line)

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

    def _history_points(self, name: str):
        series = self.histories[name]
        if not series:
            return []
        start = series[0][0]
        return [(t - start, v) for t, v in series]

    def _custom_graph_series(self, panel_name: str):
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
                    "points": self._history_points(key),
                    "axis_min": meta.get("axis_min"),
                    "axis_max": meta.get("axis_max"),
                    "decimals": meta.get("decimals", 1),
                }
            )
        return series

    def _refresh(self):
        self.state.animate_metrics()
        critical_alerts = self._active_critical_alerts()
        self.custom_trend.title = self._current_custom_graph_titles().get("custom_trend", "Custom Graph")
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
        if self._panel_visible("fuel_pressure_gauge"):
            self.fuel_pressure_gauge.set_value(self.state.fuel_pressure)
        if self._panel_visible("oil_pressure_gauge"):
            self.oil_pressure_gauge.set_value(self.state.oil_pressure)

        age = self.state.data_age_seconds
        if age < 1.0:
            link_state = "Live"
        elif age < 3.0:
            link_state = "Stale"
        else:
            link_state = "Offline"

        pill_bg = "#2E7D32" if link_state == "Live" else WARNING if link_state == "Stale" else ACCENT_2
        self.status_pill.config(text=link_state.upper(), bg=pill_bg)
        if critical_alerts:
            self.critical_bar.config(text="CRITICAL: " + "  |  ".join(critical_alerts))
            if self.critical_bar.winfo_manager() != "pack":
                self.critical_bar.pack(fill="x", pady=(0, 8), before=self.tab_bar)
        elif self.critical_bar.winfo_manager() == "pack":
            self.critical_bar.pack_forget()

        gear_text = "--" if self.state.gear.rendered_value is None else str(int(round(self.state.gear.rendered_value)))
        if self._panel_visible("gear_stat"):
            self.gear_stat.set_text(gear_text)
        throughput_value = self.state.throughput.rendered_value
        throughput_text = "--" if throughput_value is None else f"{throughput_value:.1f} kbps"
        self.throughput_pill.config(text=throughput_text)
        now = time.monotonic()
        if now - self._last_graph_refresh_monotonic >= (self.GRAPH_REFRESH_MS / 1000.0):
            if self._panel_visible("rpm_trend"):
                self.rpm_trend.set_series([
                    {"label": "rpm", "color": ACCENT, "points": self._history_points("rpm")},
                ])
            if self._panel_visible("wheel_trend"):
                self.wheel_trend.set_series([
                    {"label": "wheel", "color": ACCENT, "points": self._history_points("wheel_speed")},
                ])
            if self._panel_visible("tps_trend"):
                self.tps_trend.set_series([
                    {"label": "tps", "color": ACCENT, "points": self._history_points("tps")},
                ])
            if self._panel_visible("aps_trend"):
                self.aps_trend.set_series([
                    {"label": "aps", "color": ACCENT, "points": self._history_points("aps")},
                ])
            if self._panel_visible("gear_trend"):
                self.gear_trend.set_series([
                    {"label": "gear", "color": ACCENT, "points": self._history_points("gear")},
                ])
            if self._panel_visible("oil_temp_trend_single"):
                self.oil_temp_trend_single.set_series([
                    {"label": "oil temp", "color": ACCENT, "points": self._history_points("oil_temp")},
                ])
            if self._panel_visible("coolant_trend"):
                self.coolant_trend.set_series([
                    {"label": "coolant", "color": ACCENT_2, "points": self._history_points("ect")},
                ])
            if self._panel_visible("throughput_trend"):
                self.throughput_trend.set_series([
                    {"label": "throughput", "color": ACCENT, "points": self._history_points("throughput")},
                ])
            if self._panel_visible("lambda_trend"):
                self.lambda_trend.set_series([
                    {"label": "lambda", "color": ACCENT, "points": self._history_points("lambda1")},
                ])
            if self._panel_visible("fuel_pressure_trend_single"):
                self.fuel_pressure_trend_single.set_series([
                    {"label": "fuel press", "color": ACCENT_2, "points": self._history_points("fuel_pressure")},
                ])
            if self._panel_visible("oil_pressure_trend_single"):
                self.oil_pressure_trend_single.set_series([
                    {"label": "oil press", "color": ACCENT, "points": self._history_points("oil_pressure")},
                ])
            if self._panel_visible("throttle_trend"):
                self.throttle_trend.set_series([
                    {"label": "tps", "color": ACCENT, "points": self._history_points("tps")},
                    {"label": "aps", "color": ACCENT_2, "points": self._history_points("aps")},
                ])
            if self._panel_visible("temp_trend"):
                self.temp_trend.set_series([
                    {"label": "oil temp", "color": ACCENT, "points": self._history_points("oil_temp")},
                    {"label": "coolant", "color": ACCENT_2, "points": self._history_points("ect")},
                ])
            if self._panel_visible("pressure_trend"):
                self.pressure_trend.set_series([
                    {"label": "oil press", "color": ACCENT, "points": self._history_points("oil_pressure")},
                    {"label": "fuel press", "color": ACCENT_2, "points": self._history_points("fuel_pressure")},
                ])
            if self._panel_visible("custom_trend"):
                self.custom_trend.set_series(self._custom_graph_series("custom_trend"))
            self._last_graph_refresh_monotonic = now

        self.root.after(self.LIVE_REFRESH_MS, self._refresh)

    def _reset_metric_bounds(self):
        self.state.reset_metric_bounds()

    def _load_logo_image(self):
        if Image is None or ImageTk is None:
            self.logo_image = None
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
            logo.thumbnail((30, 30), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(logo)
        else:
            self.logo_image = None


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

    if not args.demo:
        worker = SerialWorker(args.port, args.baudrate, line_queue, False)
        worker.start()

    DashboardApp(root, state, line_queue, args.port if not args.demo else "DEMO", initial_demo=args.demo)
    root.mainloop()


if __name__ == "__main__":
    main()
