import math
import threading
import tkinter as tk
from pymavlink import mavutil
from .Styles import Colors


class FlightHUD:
    """Compact artificial horizon and primary flight data."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Colors.CARD)
        title = tk.Frame(self.frame, bg=Colors.CARD)
        title.pack(fill="x", padx=12, pady=(10, 5))
        tk.Label(title, text="FLIGHT STATUS", font=("Segoe UI", 9, "bold"),
                 fg=Colors.WHITE, bg=Colors.CARD).pack(side="left")
        tk.Label(title, text="LIVE HUD", font=("Segoe UI", 7, "bold"),
                 fg=Colors.GREEN, bg=Colors.CARD).pack(side="right")

        self.canvas = tk.Canvas(
            self.frame, bg=Colors.BLACK, height=190,
            highlightthickness=1, highlightbackground=Colors.BORDER
        )
        self.canvas.pack(fill="x", padx=10)

        values = tk.Frame(self.frame, bg=Colors.CARD)
        values.pack(fill="x", padx=10, pady=8)
        self.alt = self._metric(values, "ALT", "0.0 m", Colors.GREEN, 0, 0)
        self.speed = self._metric(values, "SPD", "0.0 km/h", Colors.CYAN, 0, 1)
        self.heading = self._metric(values, "HDG", "000°", Colors.AMBER, 1, 0)
        self.attitude = self._metric(values, "ATT", "P 0.0° / R 0.0°", Colors.PURPLE, 1, 1)
        values.grid_columnconfigure((0, 1), weight=1)

        self.altitude = 0.0
        self.speed_value = 0.0
        self.heading_value = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.draw()

    def _metric(self, parent, key, value, fg, row, col):
        box = tk.Frame(parent, bg=Colors.CARD_ALT, padx=8, pady=5)
        box.grid(row=row, column=col, sticky="ew", padx=2, pady=2)
        tk.Label(box, text=key, font=("Segoe UI", 7, "bold"), fg=Colors.MUTED,
                 bg=Colors.CARD_ALT).pack(anchor="w")
        label = tk.Label(box, text=value, font=("Segoe UI", 9, "bold"), fg=fg,
                         bg=Colors.CARD_ALT)
        label.pack(anchor="w")
        return label

    def update(self, altitude, speed, heading, pitch=0.0, roll=0.0):
        self.altitude, self.speed_value, self.heading_value = altitude, speed, heading
        self.pitch, self.roll = pitch, roll
        self.alt.config(text=f"{altitude:.1f} m")
        self.speed.config(text=f"{speed:.1f} km/h")
        self.heading.config(text=f"{heading % 360:.0f}°")
        self.attitude.config(text=f"P {pitch:.1f}° / R {roll:.1f}°")
        self.draw()

    def draw(self):
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 260)
        h = max(c.winfo_height(), 190)
        cx, cy = w / 2, h / 2 - 5
        horizon = cy + self.pitch * 2.2
        c.create_rectangle(6, 6, w - 6, h - 6, fill="#17395a", outline="")
        c.create_rectangle(6, horizon, w - 6, h - 6, fill="#4a382e", outline="")
        angle = math.radians(self.roll)
        dx = math.cos(angle) * (w * .38)
        dy = math.sin(angle) * (w * .38)
        c.create_line(cx-dx, horizon-dy, cx+dx, horizon+dy, fill=Colors.WHITE, width=2)
        for offset in (-30, -15, 15, 30):
            y = horizon + offset
            c.create_line(cx-20, y, cx+20, y, fill="#b8c7d9", width=1)
        c.create_line(cx-38, cy, cx-10, cy, fill=Colors.AMBER, width=3)
        c.create_line(cx+10, cy, cx+38, cy, fill=Colors.AMBER, width=3)
        c.create_line(cx, cy-8, cx, cy+8, fill=Colors.AMBER, width=2)
        c.create_text(18, 18, anchor="w", text="ATTITUDE", fill=Colors.MUTED,
                      font=("Segoe UI", 7, "bold"))
        c.create_text(w-18, 18, anchor="e", text=f"{self.heading_value % 360:03.0f}°",
                      fill=Colors.CYAN, font=("Segoe UI", 9, "bold"))