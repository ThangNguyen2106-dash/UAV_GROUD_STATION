from __future__ import annotations

import math
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class FlightStatusPanel(QFrame):
    """Realtime vehicle status and safety monitoring panel (Display Only).
    
    Flight control (Arm, Disarm, Modes) is operated directly from the physical RC transmitter.
    This panel purely monitors live flight state.
    """

    def __init__(self, connection_manager=None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.connection_manager = connection_manager
        self.selected_key: Optional[tuple[str, int, int]] = None
        self._is_armed = False
        self._current_mode = "--"

        self.setObjectName("FlightStatusPanel")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ----------------------------------------------------
        # 1. ARM / DISARM STATE (DISPLAY ONLY)
        # ----------------------------------------------------
        arm_box = QGroupBox("ARM / MOTOR STATUS")
        arm_layout = QVBoxLayout(arm_box)
        arm_layout.setContentsMargins(8, 8, 8, 8)
        arm_layout.setSpacing(4)

        self.arm_status_badge = QLabel("DISARMED (SAFE)")
        self.arm_status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arm_status_badge.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.arm_status_badge.setStyleSheet("""
            QLabel {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        arm_layout.addWidget(self.arm_status_badge)

        self.arm_hint = QLabel("Operated via RC Transmitter switch")
        self.arm_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arm_hint.setStyleSheet("color: #64748b; font-size: 10px;")
        arm_layout.addWidget(self.arm_hint)

        layout.addWidget(arm_box)

        # ----------------------------------------------------
        # 2. FLIGHT MODE (DISPLAY ONLY)
        # ----------------------------------------------------
        mode_box = QGroupBox("ACTIVE FLIGHT MODE")
        mode_layout = QVBoxLayout(mode_box)
        mode_layout.setContentsMargins(8, 8, 8, 8)
        mode_layout.setSpacing(4)

        self.mode_badge = QLabel("--")
        self.mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_badge.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.mode_badge.setStyleSheet("""
            QLabel {
                background: rgba(2, 132, 199, 0.15);
                color: #38bdf8;
                border: 1px solid #0284c7;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        mode_layout.addWidget(self.mode_badge)

        layout.addWidget(mode_box)

        # ----------------------------------------------------
        # 3. LIVE FLIGHT METRICS SUMMARY
        # ----------------------------------------------------
        metrics_box = QGroupBox("FLIGHT DYNAMICS")
        m_layout = QGridLayout(metrics_box)
        m_layout.setContentsMargins(8, 8, 8, 8)
        m_layout.setSpacing(6)

        self.val_altitude = QLabel("-- m")
        self.val_rel_altitude = QLabel("-- m")
        self.val_speed = QLabel("-- m/s")
        self.val_climb = QLabel("-- m/s")
        self.val_battery = QLabel("-- V (--%)")
        self.val_gps = QLabel("-- (0 Sats)")

        for lbl in (self.val_altitude, self.val_rel_altitude, self.val_speed,
                    self.val_climb, self.val_battery, self.val_gps):
            lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #f1f5f9;")

        m_layout.addWidget(QLabel("Alt (MSL):"), 0, 0)
        m_layout.addWidget(self.val_altitude, 0, 1)

        m_layout.addWidget(QLabel("Alt (Rel):"), 1, 0)
        m_layout.addWidget(self.val_rel_altitude, 1, 1)

        m_layout.addWidget(QLabel("Ground Speed:"), 2, 0)
        m_layout.addWidget(self.val_speed, 2, 1)

        m_layout.addWidget(QLabel("Climb Rate:"), 3, 0)
        m_layout.addWidget(self.val_climb, 3, 1)

        m_layout.addWidget(QLabel("Battery:"), 4, 0)
        m_layout.addWidget(self.val_battery, 4, 1)

        m_layout.addWidget(QLabel("GPS:"), 5, 0)
        m_layout.addWidget(self.val_gps, 5, 1)

        layout.addWidget(metrics_box)

        # ----------------------------------------------------
        # 4. SENSOR / LINK HEALTH
        # ----------------------------------------------------
        health_box = QGroupBox("SYSTEM HEALTH")
        h_layout = QGridLayout(health_box)
        h_layout.setContentsMargins(8, 8, 8, 8)
        h_layout.setSpacing(6)

        self.lbl_gyro = QLabel("🟢 OK")
        self.lbl_accel = QLabel("🟢 OK")
        self.lbl_mag = QLabel("🟢 OK")
        self.lbl_gps_status = QLabel("🟢 READY")

        for lbl in (self.lbl_gyro, self.lbl_accel, self.lbl_mag, self.lbl_gps_status):
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #4ade80;")

        h_layout.addWidget(QLabel("Gyroscope:"), 0, 0)
        h_layout.addWidget(self.lbl_gyro, 0, 1)

        h_layout.addWidget(QLabel("Accelerometer:"), 1, 0)
        h_layout.addWidget(self.lbl_accel, 1, 1)

        h_layout.addWidget(QLabel("Compass (Mag):"), 2, 0)
        h_layout.addWidget(self.lbl_mag, 2, 1)

        h_layout.addWidget(QLabel("GPS Sensor:"), 3, 0)
        h_layout.addWidget(self.lbl_gps_status, 3, 1)

        layout.addWidget(health_box)

        layout.addStretch(1)

    def set_active_vehicle(self, key: Optional[tuple[str, int, int]]) -> None:
        self.selected_key = key
        if key is None:
            self._reset_display()

    def update_telemetry(self, state: Any) -> None:
        if state is None:
            self._reset_display()
            return

        # 1. Arm Status
        armed = bool(getattr(state, "armed", False))
        if armed != self._is_armed:
            self._is_armed = armed
            if self._is_armed:
                self.arm_status_badge.setText("⚠️ ARMED (MOTORS LIVE)")
                self.arm_status_badge.setStyleSheet("""
                    QLabel {
                        background: rgba(239, 68, 68, 0.2);
                        color: #ef4444;
                        border: 2px solid #ef4444;
                        border-radius: 6px;
                        padding: 10px;
                        font-weight: bold;
                    }
                """)
            else:
                self.arm_status_badge.setText("🔒 DISARMED (SAFE)")
                self.arm_status_badge.setStyleSheet("""
                    QLabel {
                        background: #1e293b;
                        color: #94a3b8;
                        border: 1px solid #334155;
                        border-radius: 6px;
                        padding: 10px;
                        font-weight: bold;
                    }
                """)

        # 2. Flight Mode
        mode = getattr(state, "flight_mode", None) or getattr(state, "mode", "--")
        mode_str = str(mode).upper()
        if mode_str != self._current_mode:
            self._current_mode = mode_str
            self.mode_badge.setText(self._current_mode)

        # 3. Dynamic metrics
        alt = getattr(state, "altitude", None)
        rel_alt = getattr(state, "relative_alt", None)
        speed = getattr(state, "ground_speed", None)
        climb = getattr(state, "climb_rate", None)
        bat_v = getattr(state, "battery_voltage", None)
        bat_pct = getattr(state, "battery_remaining", None)
        sats = getattr(state, "satellites_visible", None)
        gps_fix = getattr(state, "gps_fix_type", None)

        if alt is not None and math.isfinite(alt):
            self.val_altitude.setText(f"{alt:.1f} m")
        if rel_alt is not None and math.isfinite(rel_alt):
            self.val_rel_altitude.setText(f"{rel_alt:.1f} m")
        if speed is not None and math.isfinite(speed):
            self.val_speed.setText(f"{speed:.1f} m/s")
        if climb is not None and math.isfinite(climb):
            self.val_climb.setText(f"{climb:+.1f} m/s")

        if bat_v is not None and math.isfinite(bat_v):
            pct_str = f"{bat_pct:.0f}%" if (bat_pct is not None and math.isfinite(bat_pct)) else "--%"
            self.val_battery.setText(f"{bat_v:.1f} V ({pct_str})")

        fix_str = f"Fix {gps_fix}" if gps_fix is not None else "--"
        sat_str = f"{sats} Sats" if sats is not None else "0 Sats"
        self.val_gps.setText(f"{fix_str} ({sat_str})")

    def _reset_display(self) -> None:
        self._is_armed = False
        self._current_mode = "--"
        self.arm_status_badge.setText("DISARMED (SAFE)")
        self.arm_status_badge.setStyleSheet("""
            QLabel {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self.mode_badge.setText("--")
        self.val_altitude.setText("-- m")
        self.val_rel_altitude.setText("-- m")
        self.val_speed.setText("-- m/s")
        self.val_climb.setText("-- m/s")
        self.val_battery.setText("-- V (--%)")
        self.val_gps.setText("-- (0 Sats)")


# Compatibility Alias
FlightControlPanel = FlightStatusPanel
