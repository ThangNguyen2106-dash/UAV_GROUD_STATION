import tkinter as tk
from tkinter import ttk

from .Styles import Colors, button


class TelemetryPanel:
    """System telemetry + serial connection controls."""

    def __init__(
        self,
        parent,
        on_refresh_ports=None,
        on_connect=None,
        on_disconnect=None,
    ):
        self.on_refresh_ports = on_refresh_ports or (lambda: None)
        self.on_connect = on_connect or (lambda port, baudrate: None)
        self.on_disconnect = on_disconnect or (lambda: None)

        self.frame = tk.Frame(parent, bg=Colors.CARD)

        # =====================================================
        # HEADER
        # =====================================================

        header = tk.Frame(self.frame, bg=Colors.CARD)
        header.pack(fill="x", padx=12, pady=(8, 5))

        tk.Label(
            header,
            text="TELEMETRY LINK",
            font=("Segoe UI", 9, "bold"),
            fg=Colors.WHITE,
            bg=Colors.CARD,
        ).pack(side="left")

        self.health = tk.Label(
            header,
            text="WAITING",
            font=("Segoe UI", 7, "bold"),
            fg=Colors.AMBER,
            bg=Colors.CARD,
        )
        self.health.pack(side="right")

        # =====================================================
        # SERIAL CONFIG
        # =====================================================

        serial_box = tk.Frame(
            self.frame,
            bg=Colors.CARD_ALT,
            padx=7,
            pady=7,
        )
        serial_box.pack(fill="x", padx=8, pady=(0, 6))

        tk.Label(
            serial_box,
            text="COM PORT",
            font=("Segoe UI", 7, "bold"),
            fg=Colors.MUTED,
            bg=Colors.CARD_ALT,
        ).grid(row=0, column=0, sticky="w", padx=(0, 4), pady=(0, 3))

        tk.Label(
            serial_box,
            text="BAUDRATE",
            font=("Segoe UI", 7, "bold"),
            fg=Colors.MUTED,
            bg=Colors.CARD_ALT,
        ).grid(row=0, column=1, sticky="w", padx=(4, 0), pady=(0, 3))

        self.port_var = tk.StringVar()
        self.port_box = ttk.Combobox(
            serial_box,
            textvariable=self.port_var,
            state="readonly",
            width=10,
            style="Rigel.TCombobox",
        )
        self.port_box.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        self.baud_var = tk.StringVar(value="57600")
        self.baud_box = ttk.Combobox(
            serial_box,
            textvariable=self.baud_var,
            state="readonly",
            values=(
                "9600",
                "19200",
                "38400",
                "57600",
                "115200",
                "230400",
                "460800",
                "921600",
            ),
            width=10,
            style="Rigel.TCombobox",
        )
        self.baud_box.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        serial_box.grid_columnconfigure(0, weight=1)
        serial_box.grid_columnconfigure(1, weight=1)

        buttons = tk.Frame(serial_box, bg=Colors.CARD_ALT)
        buttons.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(6, 0),
        )

        self.refresh_button = button(
            buttons,
            "↻ PORT",
            self.on_refresh_ports,
            "#37474f",
            pady=4,
            padx=7,
        )
        self.refresh_button.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.connect_button = button(
            buttons,
            "CONNECT",
            self._connect_clicked,
            "#1565c0",
            pady=4,
            padx=7,
        )
        self.connect_button.pack(side="left", fill="x", expand=True, padx=2)

        self.disconnect_button = button(
            buttons,
            "DISCONNECT",
            self._disconnect_clicked,
            "#7f1d1d",
            pady=4,
            padx=7,
        )
        self.disconnect_button.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # =====================================================
        # METRICS
        # =====================================================

        grid = tk.Frame(self.frame, bg=Colors.CARD)
        grid.pack(fill="x", padx=10, pady=(0, 10))

        self.battery = self._metric(
            grid, "BATTERY", "--", Colors.GREEN, 0, 0
        )
        self.gps = self._metric(
            grid, "GPS", "--", Colors.CYAN, 0, 1
        )
        self.telemetry = self._metric(
            grid, "LINK", "--", Colors.AMBER, 1, 0
        )
        self.fix = self._metric(
            grid, "FIX", "--", Colors.PURPLE, 1, 1
        )

        grid.grid_columnconfigure((0, 1), weight=1)

        self._set_connected_ui(False)

    def _metric(self, parent, key, value, fg, row, col):
        box = tk.Frame(
            parent,
            bg=Colors.CARD_ALT,
            padx=8,
            pady=6,
        )
        box.grid(
            row=row,
            column=col,
            sticky="ew",
            padx=2,
            pady=2,
        )

        tk.Label(
            box,
            text=key,
            font=("Segoe UI", 7, "bold"),
            fg=Colors.MUTED,
            bg=Colors.CARD_ALT,
        ).pack(anchor="w")

        label = tk.Label(
            box,
            text=value,
            font=("Segoe UI", 9, "bold"),
            fg=fg,
            bg=Colors.CARD_ALT,
        )
        label.pack(anchor="w")

        return label

    def set_ports(self, ports):
        values = list(ports or [])
        self.port_box["values"] = values

        if self.port_var.get() not in values:
            self.port_var.set(values[0] if values else "")

    def get_selected_port(self):
        return self.port_var.get().strip()

    def get_selected_baudrate(self):
        return int(self.baud_var.get())

    def _connect_clicked(self):
        port = self.get_selected_port()
        baudrate = self.get_selected_baudrate()
        self.on_connect(port, baudrate)

    def _disconnect_clicked(self):
        self.on_disconnect()

    def set_connection_status(self, connected, text=None):
        self.health.configure(
            text=text or ("CONNECTED" if connected else "WAITING"),
            fg=Colors.GREEN if connected else Colors.AMBER,
        )
        self._set_connected_ui(connected)

    def _set_connected_ui(self, connected):
        if connected:
            self.connect_button.configure(
                state="disabled",
                bg="#37474f",
            )
            self.disconnect_button.configure(
                state="normal",
            )
            self.port_box.configure(state="disabled")
            self.baud_box.configure(state="disabled")
        else:
            self.connect_button.configure(
                state="normal",
                bg="#1565c0",
            )
            self.disconnect_button.configure(
                state="disabled",
            )
            self.port_box.configure(state="readonly")
            self.baud_box.configure(state="readonly")

    def update(
        self,
        battery_pct=None,
        voltage=None,
        satellites=None,
        fix_type=None,
        signal_pct=None,
        signal_dbm=None,
    ):
        if battery_pct is not None:
            v = f" {voltage:.1f}V" if voltage is not None else ""
            self.battery.config(text=f"{battery_pct:.0f}%{v}")
        elif voltage is not None:
            self.battery.config(text=f"-- / {voltage:.1f}V")

        if satellites is not None:
            self.gps.config(text=f"{satellites} SAT")

        if signal_pct is not None:
            dbm = f" / {signal_dbm} dBm" if signal_dbm is not None else ""
            self.telemetry.config(text=f"{signal_pct:.0f}%{dbm}")
        elif signal_dbm is not None:
            self.telemetry.config(text=f"{signal_dbm} dBm")

        if fix_type is not None:
            self.fix.config(text=str(fix_type))

        self.health.config(
            text="DATA ACTIVE",
            fg=Colors.GREEN,
        )
