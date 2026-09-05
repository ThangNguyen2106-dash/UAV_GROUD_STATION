from __future__ import annotations

import math
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class TelemetryCardsWidget(QWidget):
    """Cockpit telemetry cards: Power & Battery, GPS Navigation, Flight Dynamics."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("TelemetryCardsWidget")
        self._lat = 0.0
        self._lon = 0.0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ----------------------------------------------------
        # 1. POWER & BATTERY CARD
        # ----------------------------------------------------
        bat_box = QGroupBox("🔋 POWER & BATTERY")
        bat_layout = QVBoxLayout(bat_box)
        bat_layout.setContentsMargins(8, 8, 8, 8)
        bat_layout.setSpacing(6)

        # Big voltage & current row
        v_row = QHBoxLayout()
        self.lbl_voltage = QLabel("-- V")
        self.lbl_voltage.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_voltage.setStyleSheet("color: #38bdf8;")
        v_row.addWidget(self.lbl_voltage)

        v_row.addStretch(1)

        self.lbl_current = QLabel("-- A")
        self.lbl_current.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_current.setStyleSheet("color: #cbd5e1;")
        v_row.addWidget(self.lbl_current)
        bat_layout.addLayout(v_row)

        # Progress bar
        self.bat_bar = QProgressBar()
        self.bat_bar.setRange(0, 100)
        self.bat_bar.setValue(0)
        self.bat_bar.setFixedHeight(14)
        self.bat_bar.setTextVisible(True)
        self.bat_bar.setFormat("%p%")
        self.bat_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 4px;
                text-align: center;
                color: white;
                font-weight: bold;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 3px;
            }
        """)
        bat_layout.addWidget(self.bat_bar)

        layout.addWidget(bat_box)

        # ----------------------------------------------------
        # 2. GPS & NAVIGATION CARD
        # ----------------------------------------------------
        gps_box = QGroupBox("🛰️ GPS & POSITION")
        gps_layout = QGridLayout(gps_box)
        gps_layout.setContentsMargins(8, 8, 8, 8)
        gps_layout.setSpacing(6)

        self.lbl_gps_fix = QLabel("NO FIX")
        self.lbl_gps_fix.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_gps_fix.setStyleSheet("background:#334155; color:#94a3b8; border-radius:3px; padding:2px 6px;")
        gps_layout.addWidget(QLabel("Fix Status:"), 0, 0)
        gps_layout.addWidget(self.lbl_gps_fix, 0, 1)

        self.lbl_satellites = QLabel("0 Sats")
        self.lbl_satellites.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_satellites.setStyleSheet("color: #38bdf8;")
        gps_layout.addWidget(QLabel("Satellites:"), 0, 2)
        gps_layout.addWidget(self.lbl_satellites, 0, 3)

        self.lbl_coords = QLabel("--, --")
        self.lbl_coords.setFont(QFont("Consolas", 10))
        self.lbl_coords.setStyleSheet("color: #f8fafc;")
        gps_layout.addWidget(QLabel("Coords:"), 1, 0)
        gps_layout.addWidget(self.lbl_coords, 1, 1, 1, 2)

        self.btn_copy_coords = QPushButton("📋 Copy")
        self.btn_copy_coords.setFixedHeight(22)
        self.btn_copy_coords.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background: #334155;
                color: white;
            }
        """)
        self.btn_copy_coords.clicked.connect(self._copy_coordinates)
        gps_layout.addWidget(self.btn_copy_coords, 1, 3)

        layout.addWidget(gps_box)

        # ----------------------------------------------------
        # 3. FLIGHT DYNAMICS CARD
        # ----------------------------------------------------
        dyn_box = QGroupBox("✈️ FLIGHT DYNAMICS")
        dyn_layout = QGridLayout(dyn_box)
        dyn_layout.setContentsMargins(8, 8, 8, 8)
        dyn_layout.setSpacing(6)

        self.lbl_speed_large = QLabel("0.0 m/s")
        self.lbl_speed_large.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_speed_large.setStyleSheet("color: #38bdf8;")
        dyn_layout.addWidget(QLabel("Ground Speed:"), 0, 0)
        dyn_layout.addWidget(self.lbl_speed_large, 0, 1)

        self.lbl_climb_rate = QLabel("0.0 m/s")
        self.lbl_climb_rate.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_climb_rate.setStyleSheet("color: #f1f5f9;")
        dyn_layout.addWidget(QLabel("Climb Rate:"), 0, 2)
        dyn_layout.addWidget(self.lbl_climb_rate, 0, 3)

        self.lbl_alt_rel = QLabel("0.0 m (AGL)")
        self.lbl_alt_rel.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_alt_rel.setStyleSheet("color: #4ade80;")
        dyn_layout.addWidget(QLabel("Relative Alt:"), 1, 0)
        dyn_layout.addWidget(self.lbl_alt_rel, 1, 1)

        self.lbl_alt_msl = QLabel("0.0 m (MSL)")
        self.lbl_alt_msl.setFont(QFont("Segoe UI", 10))
        self.lbl_alt_msl.setStyleSheet("color: #cbd5e1;")
        dyn_layout.addWidget(QLabel("MSL Alt:"), 1, 2)
        dyn_layout.addWidget(self.lbl_alt_msl, 1, 3)

        self.lbl_attitude = QLabel("R: +0.0°   P: +0.0°   Y: 000°")
        self.lbl_attitude.setFont(QFont("Consolas", 10))
        self.lbl_attitude.setStyleSheet("color: #e2e8f0;")
        dyn_layout.addWidget(QLabel("Attitude:"), 2, 0)
        dyn_layout.addWidget(self.lbl_attitude, 2, 1, 1, 3)

        layout.addWidget(dyn_box)

    def update_telemetry(self, state: Any) -> None:
        if state is None:
            self._reset()
            return

        # 1. Battery
        bat_v = getattr(state, "battery_voltage", None)
        bat_pct = getattr(state, "battery_remaining", None)
        bat_curr = getattr(state, "battery_current", None)

        if bat_v is not None and math.isfinite(bat_v):
            self.lbl_voltage.setText(f"{bat_v:.1f} V")
        else:
            self.lbl_voltage.setText("-- V")

        if bat_curr is not None and math.isfinite(bat_curr) and bat_curr >= 0:
            self.lbl_current.setText(f"{bat_curr:.1f} A")
        else:
            self.lbl_current.setText("-- A")

        if bat_pct is not None and math.isfinite(bat_pct):
            pct = max(0, min(100, int(bat_pct)))
            self.bat_bar.setValue(pct)
            if pct > 40:
                chunk_color = "#22c55e"  # Green
            elif pct > 20:
                chunk_color = "#f59e0b"  # Amber
            else:
                chunk_color = "#ef4444"  # Red

            self.bat_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                    font-size: 10px;
                }}
                QProgressBar::chunk {{
                    background-color: {chunk_color};
                    border-radius: 3px;
                }}
            """)
        else:
            self.bat_bar.setValue(0)

        # 2. GPS & Coordinates
        lat = getattr(state, "latitude", None)
        lon = getattr(state, "longitude", None)
        sats = getattr(state, "satellites_visible", None)
        fix_type = getattr(state, "gps_fix_type", 0) or 0

        if lat is not None and lon is not None and math.isfinite(lat) and math.isfinite(lon):
            self._lat = lat
            self._lon = lon
            self.lbl_coords.setText(f"{lat:.6f}, {lon:.6f}")
        else:
            self.lbl_coords.setText("--, --")

        self.lbl_satellites.setText(f"{sats if sats is not None else 0} Sats")

        # GPS Fix Badge styling
        fix_names = {0: "NO GPS", 1: "NO FIX", 2: "2D FIX", 3: "3D FIX", 4: "DGPS", 5: "RTK FLT", 6: "RTK FIX"}
        fix_name = fix_names.get(fix_type, f"FIX {fix_type}")
        self.lbl_gps_fix.setText(fix_name)
        if fix_type >= 3:
            self.lbl_gps_fix.setStyleSheet("background:rgba(34,197,94,0.2); color:#4ade80; border:1px solid #22c55e; border-radius:3px; padding:2px 6px;")
        elif fix_type == 2:
            self.lbl_gps_fix.setStyleSheet("background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid #f59e0b; border-radius:3px; padding:2px 6px;")
        else:
            self.lbl_gps_fix.setStyleSheet("background:#334155; color:#94a3b8; border-radius:3px; padding:2px 6px;")

        # 3. Flight Dynamics
        spd = getattr(state, "ground_speed", None)
        climb = getattr(state, "climb_rate", None)
        alt = getattr(state, "altitude", None)
        rel_alt = getattr(state, "relative_alt", None)
        roll = getattr(state, "roll", 0.0) or 0.0
        pitch = getattr(state, "pitch", 0.0) or 0.0
        yaw = getattr(state, "yaw", 0.0) or 0.0
        heading = getattr(state, "heading", None) or yaw

        if spd is not None and math.isfinite(spd):
            kmh = spd * 3.6
            self.lbl_speed_large.setText(f"{spd:.1f} m/s ({kmh:.0f} km/h)")
        else:
            self.lbl_speed_large.setText("0.0 m/s")

        if climb is not None and math.isfinite(climb):
            arrow = "▲" if climb > 0.1 else ("▼" if climb < -0.1 else "━")
            self.lbl_climb_rate.setText(f"{arrow} {climb:+.1f} m/s")
            self.lbl_climb_rate.setStyleSheet("color:#4ade80;" if climb > 0.1 else ("#f87171;" if climb < -0.1 else "#f1f5f9;"))
        else:
            self.lbl_climb_rate.setText("━ 0.0 m/s")
            self.lbl_climb_rate.setStyleSheet("color:#f1f5f9;")

        if rel_alt is not None and math.isfinite(rel_alt):
            self.lbl_alt_rel.setText(f"{rel_alt:.1f} m (AGL)")
        else:
            self.lbl_alt_rel.setText("0.0 m (AGL)")

        if alt is not None and math.isfinite(alt):
            self.lbl_alt_msl.setText(f"{alt:.1f} m (MSL)")
        else:
            self.lbl_alt_msl.setText("0.0 m (MSL)")

        self.lbl_attitude.setText(f"R: {roll:+.1f}°   P: {pitch:+.1f}°   HDG: {heading:03.0f}°")

    def _copy_coordinates(self) -> None:
        if self._lat != 0.0 or self._lon != 0.0:
            coords_str = f"{self._lat:.7f}, {self._lon:.7f}"
            clipboard = QGuiApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(coords_str)

    def _reset(self) -> None:
        self.lbl_voltage.setText("-- V")
        self.lbl_current.setText("-- A")
        self.bat_bar.setValue(0)
        self.lbl_coords.setText("--, --")
        self.lbl_satellites.setText("0 Sats")
        self.lbl_gps_fix.setText("NO FIX")
        self.lbl_gps_fix.setStyleSheet("background:#334155; color:#94a3b8; border-radius:3px; padding:2px 6px;")
        self.lbl_speed_large.setText("0.0 m/s")
        self.lbl_climb_rate.setText("━ 0.0 m/s")
        self.lbl_alt_rel.setText("0.0 m (AGL)")
        self.lbl_alt_msl.setText("0.0 m (MSL)")
        self.lbl_attitude.setText("R: +0.0°   P: +0.0°   HDG: 000°")
