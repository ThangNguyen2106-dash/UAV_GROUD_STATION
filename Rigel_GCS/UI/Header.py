import tkinter as tk
from .Styles import Colors


class Header:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Colors.PANEL, height=58)
        self.frame.pack(fill="x", side="top")
        self.frame.pack_propagate(False)
        self._build()

    def _build(self):
        left = tk.Frame(self.frame, bg=Colors.PANEL)
        left.pack(side="left", fill="y", padx=18)

        tk.Label(
            left, text="RIGEL", font=("Segoe UI", 16, "bold"),
            fg=Colors.CYAN, bg=Colors.PANEL
        ).pack(side="left", pady=8)
        tk.Label(
            left, text="GROUND CONTROL STATION", font=("Segoe UI", 9, "bold"),
            fg=Colors.WHITE, bg=Colors.PANEL
        ).pack(side="left", padx=(10, 0), pady=8)
        tk.Label(
            left, text="UAV MISSION CONTROL", font=("Segoe UI", 7),
            fg=Colors.MUTED, bg=Colors.PANEL
        ).pack(side="left", padx=(8, 0), pady=8)

        right = tk.Frame(self.frame, bg=Colors.PANEL)
        right.pack(side="right", fill="y", padx=16)

        self.mode = tk.Label(
            right, text="DISARMED", font=("Segoe UI", 8, "bold"),
            fg=Colors.TEXT, bg=Colors.CARD_ALT, padx=12, pady=6
        )
        self.mode.pack(side="left", padx=4, pady=10)

        self.telemetry = tk.Label(
            right, text="● TELEMETRY OFFLINE", font=("Segoe UI", 8, "bold"),
            fg=Colors.RED, bg=Colors.PANEL
        )
        self.telemetry.pack(side="left", padx=12)

        self.gcs = tk.Label(
            right, text="GCS: READY", font=("Segoe UI", 8, "bold"),
            fg=Colors.CYAN, bg=Colors.PANEL
        )
        self.gcs.pack(side="left")

    def set_mode(self, mode):
        mode = str(mode).upper()
        armed = mode not in {"DISARMED", "OFFLINE"}
        self.mode.config(
            text=mode,
            fg=Colors.GREEN if armed else Colors.TEXT,
            bg="#173a2b" if armed else Colors.CARD_ALT,
        )

    def set_telemetry(self, online):
        self.telemetry.config(
            text="● TELEMETRY ONLINE" if online else "● TELEMETRY OFFLINE",
            fg=Colors.GREEN if online else Colors.RED,
        )

    def set_gcs_status(self, status):
        self.gcs.config(text=f"GCS: {status}")