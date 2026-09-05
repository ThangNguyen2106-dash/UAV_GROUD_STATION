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
    """High-density cockpit telemetry display: Power, GPS, Flight Dynamics, and Coordinates."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("TelemetryCardsWidget")
        self._lat = 0.0
        self._lon = 0.0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        card_box = QGroupBox("📊 TELEMETRY & SENSORS")
        card_box.setStyleSheet("""
            QGroupBox {
                background: #090e1f;
                border: 1px solid #1e293b;
                border-radius: 6px;
                font-size: 8.5pt;
                font-weight: bold;
                color: #38bdf8;
                margin-top: 8px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                background: #090e1f;
            }
        """)
        grid = QGridLayout(card_box)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(5)

        # Explicit column structure with ample width for GPS badge & sats
        grid.setColumnMinimumWidth(0, 68)
        grid.setColumnMinimumWidth(1, 80)
        grid.setColumnMinimumWidth(2, 56)
        grid.setColumnMinimumWidth(3, 94)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        # Row 0 (Left): Battery
        lbl_b_title = QLabel("🔋 Battery:")
        lbl_b_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: 600;")
        grid.addWidget(lbl_b_title, 0, 0)

        bat_row = QHBoxLayout()
        bat_row.setContentsMargins(0, 0, 0, 0)
        bat_row.setSpacing(3)
        self.lbl_voltage = QLabel("--V")
        self.lbl_voltage.setFont(QFont("Consolas", 8.5, QFont.Weight.Bold))
        self.lbl_voltage.setStyleSheet("color: #38bdf8;")
        self.lbl_voltage.setMinimumWidth(36)
        bat_row.addWidget(self.lbl_voltage)

        self.bat_bar = QProgressBar()
        self.bat_bar.setRange(0, 100)
        self.bat_bar.setValue(0)
        self.bat_bar.setFixedHeight(12)
        self.bat_bar.setFixedWidth(40)
        self.bat_bar.setTextVisible(True)
        self.bat_bar.setFormat("%p%")
        self.bat_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 2px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                font-size: 7.5px;
                font-family: Consolas;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 1px;
            }
        """)
        bat_row.addWidget(self.bat_bar)
        bat_row.addStretch(1)
        grid.addLayout(bat_row, 0, 1)

        # Row 0 (Right): GPS Fix & Satellites
        lbl_g_title = QLabel("🛰️ GPS:")
        lbl_g_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: 600;")
        grid.addWidget(lbl_g_title, 0, 2)

        gps_row = QHBoxLayout()
        gps_row.setContentsMargins(0, 0, 0, 0)
        gps_row.setSpacing(3)
        self.lbl_gps_fix = QLabel("NO FIX")
        self.lbl_gps_fix.setFont(QFont("Consolas", 7.5, QFont.Weight.Bold))
        self.lbl_gps_fix.setAlignment(Qt.AlignCenter)
        self.lbl_gps_fix.setFixedWidth(44)
        self.lbl_gps_fix.setFixedHeight(15)
        self.lbl_gps_fix.setStyleSheet("background:#334155; color:#94a3b8; border-radius:2px;")
        gps_row.addWidget(self.lbl_gps_fix)

        self.lbl_satellites = QLabel("0 Sats")
        self.lbl_satellites.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.lbl_satellites.setStyleSheet("color: #38bdf8;")
        gps_row.addWidget(self.lbl_satellites)
        gps_row.addStretch(1)
        grid.addLayout(gps_row, 0, 3)

        # Row 1 (Left): Ground Speed
        lbl_s_title = QLabel("🚀 Speed:")
        lbl_s_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: 600;")
        grid.addWidget(lbl_s_title, 1, 0)

        self.lbl_speed_large = QLabel("0.0 m/s")
        self.lbl_speed_large.setFont(QFont("Consolas", 8.5, QFont.Weight.Bold))
        self.lbl_speed_large.setStyleSheet("color: #38bdf8;")
        grid.addWidget(self.lbl_speed_large, 1, 1)

        # Row 1 (Right): Climb Rate
        lbl_c_title = QLabel("📈 Climb:")
        lbl_c_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: 600;")
        grid.addWidget(lbl_c_title, 1, 2)

        self.lbl_climb_rate = QLabel("━ 0.0 m/s")
        self.lbl_climb_rate.setFont(QFont("Consolas", 8.5, QFont.Weight.Bold))
        self.lbl_climb_rate.setStyleSheet("color: #f1f5f9;")
        grid.addWidget(self.lbl_climb_rate, 1, 3)

        # Row 2 (Left): Altitude AGL
        lbl_a_title = QLabel("📏 Alt (AGL):")
        lbl_a_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: 600;")
        grid.addWidget(lbl_a_title, 2, 0)

        self.lbl_alt_rel = QLabel("0.0 m")
        self.lbl_alt_rel.setFont(QFont("Consolas", 8.5, QFont.Weight.Bold))
        self.lbl_alt_rel.setStyleSheet("color: #4ade80;")
        grid.addWidget(self.lbl_alt_rel, 2, 1)

        # Row 2 (Right): MSL Altitude
        lbl_m_title = QLabel("🏔️ MSL Alt:")
        lbl_m_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: 600;")
        grid.addWidget(lbl_m_title, 2, 2)

        self.lbl_alt_msl = QLabel("0.0 m")
        self.lbl_alt_msl.setFont(QFont("Consolas", 8.5))
        self.lbl_alt_msl.setStyleSheet("color: #cbd5e1;")
        grid.addWidget(self.lbl_alt_msl, 2, 3)

        # Row 3: GPS Coordinates & Copy Button (Spanning full width)
        lbl_coord_title = QLabel("📍 Coords:")
        lbl_coord_title.setStyleSheet("color: #94a3b8; font-size: 8pt; font-weight: 600;")
        grid.addWidget(lbl_coord_title, 3, 0)

        coord_row = QHBoxLayout()
        coord_row.setContentsMargins(0, 0, 0, 0)
        coord_row.setSpacing(6)
        self.lbl_coords = QLabel("--, --")
        self.lbl_coords.setFont(QFont("Consolas", 8))
        self.lbl_coords.setStyleSheet("color: #f8fafc;")
        coord_row.addWidget(self.lbl_coords)

        self.btn_copy_coords = QPushButton("📋 Copy")
        self.btn_copy_coords.setFixedHeight(18)
        self.btn_copy_coords.setFixedWidth(50)
        self.btn_copy_coords.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 3px;
                font-size: 7.5pt;
                padding: 0 4px;
            }
            QPushButton:hover {
                background: #334155;
                color: white;
            }
        """)
        self.btn_copy_coords.clicked.connect(self._copy_coordinates)
        coord_row.addWidget(self.btn_copy_coords)
        coord_row.addStretch(1)
        grid.addLayout(coord_row, 3, 1, 1, 3)

        # Hidden fields for compatibility
        self.lbl_current = QLabel("")
        self.lbl_attitude = QLabel("")

        layout.addWidget(card_box, 1)

    def update_telemetry(self, state: Any) -> None:
        if state is None:
            self._reset()
            return

        # 1. Battery
        bat_v = getattr(state, "battery_voltage", None)
        bat_pct = getattr(state, "battery_remaining", None)

        if bat_v is not None and math.isfinite(bat_v):
            self.lbl_voltage.setText(f"{bat_v:.1f}V")
        else:
            self.lbl_voltage.setText("--V")

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
                    border-radius: 2px;
                    text-align: center;
                    color: white;
                    font-weight: bold;
                    font-size: 8px;
                }}
                QProgressBar::chunk {{
                    background-color: {chunk_color};
                    border-radius: 2px;
                }}
            """)
        else:
            self.bat_bar.setValue(0)

        # 2. GPS & Coordinates
        lat = getattr(state, "latitude", None)
        lon = getattr(state, "longitude", None)
        sats = getattr(state, "satellites_visible", None)
        fix_type = getattr(state, "gps_fix_type", 0) or 0

        if lat is not None and lon is not None and math.isfinite(lat) and math.isfinite(lon) and (lat != 0.0 or lon != 0.0):
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
            self.lbl_gps_fix.setStyleSheet("background:rgba(34,197,94,0.2); color:#4ade80; border:1px solid #22c55e; border-radius:2px; padding:1px 4px;")
        elif fix_type == 2:
            self.lbl_gps_fix.setStyleSheet("background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid #f59e0b; border-radius:2px; padding:1px 4px;")
        else:
            self.lbl_gps_fix.setStyleSheet("background:#334155; color:#94a3b8; border-radius:2px; padding:1px 4px;")

        # 3. Flight Dynamics
        spd = getattr(state, "ground_speed", None)
        climb = getattr(state, "climb_rate", None)
        alt = getattr(state, "altitude", None)
        rel_alt = getattr(state, "relative_altitude", None) or getattr(state, "relative_alt", None)

        if spd is not None and math.isfinite(spd):
            self.lbl_speed_large.setText(f"{spd:.1f} m/s")
        else:
            self.lbl_speed_large.setText("0.0 m/s")

        if climb is not None and math.isfinite(climb):
            arrow = "▲" if climb > 0.1 else ("▼" if climb < -0.1 else "━")
            self.lbl_climb_rate.setText(f"{arrow} {abs(climb):.1f} m/s")
            self.lbl_climb_rate.setStyleSheet("color:#4ade80;" if climb > 0.1 else ("#f87171;" if climb < -0.1 else "#f1f5f9;"))
        else:
            self.lbl_climb_rate.setText("━ 0.0 m/s")
            self.lbl_climb_rate.setStyleSheet("color:#f1f5f9;")

        if rel_alt is not None and math.isfinite(rel_alt):
            self.lbl_alt_rel.setText(f"{rel_alt:.1f} m")
        else:
            self.lbl_alt_rel.setText("0.0 m")

        if alt is not None and math.isfinite(alt):
            self.lbl_alt_msl.setText(f"{alt:.1f} m")
        else:
            self.lbl_alt_msl.setText("0.0 m")

    def _copy_coordinates(self) -> None:
        if self._lat != 0.0 or self._lon != 0.0:
            coords_str = f"{self._lat:.7f}, {self._lon:.7f}"
            clipboard = QGuiApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(coords_str)

    def _reset(self) -> None:
        self.lbl_voltage.setText("--V")
        self.bat_bar.setValue(0)
        self.lbl_coords.setText("--, --")
        self.lbl_satellites.setText("0 Sats")
        self.lbl_gps_fix.setText("NO FIX")
        self.lbl_gps_fix.setStyleSheet("background:#334155; color:#94a3b8; border-radius:2px; padding:1px 4px;")
        self.lbl_speed_large.setText("0.0 m/s")
        self.lbl_climb_rate.setText("━ 0.0 m/s")
        self.lbl_alt_rel.setText("0.0 m")
        self.lbl_alt_msl.setText("0.0 m")
