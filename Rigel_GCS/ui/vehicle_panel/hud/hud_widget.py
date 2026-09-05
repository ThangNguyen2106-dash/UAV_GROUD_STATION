from __future__ import annotations

import math
from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from .artificial_horizon import ArtificialHorizon
from .compass import Compass
from .flight_status import FlightStatus


class HUDWidget(QFrame):
    """Compact Primary Flight Display (Artificial Horizon + Compass Tape)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setObjectName("HUDWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame#HUDWidget {
                background: #020617;
                border: 1px solid #1e293b;
                border-radius: 4px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(3)

        # 1. Artificial Horizon (Attitude Indicator)
        self.horizon = ArtificialHorizon()
        root.addWidget(self.horizon)

        # 2. Compass Tape
        self.compass = Compass()
        root.addWidget(self.compass)

        # 3. Compact Attitude Angles Readout Strip
        readout_layout = QGridLayout()
        readout_layout.setContentsMargins(4, 2, 4, 2)
        readout_layout.setHorizontalSpacing(8)

        self.lbl_roll = QLabel("ROLL: 0.0°")
        self.lbl_pitch = QLabel("PITCH: 0.0°")
        self.lbl_hdg = QLabel("HDG: 000°")

        for lbl in (self.lbl_roll, self.lbl_pitch, self.lbl_hdg):
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #38bdf8; background: #0b1329; border: 1px solid #1e293b; border-radius: 3px; padding: 2px 4px;")

        readout_layout.addWidget(self.lbl_roll, 0, 0)
        readout_layout.addWidget(self.lbl_pitch, 0, 1)
        readout_layout.addWidget(self.lbl_hdg, 0, 2)
        root.addLayout(readout_layout)

    def update_telemetry(self, state: Any) -> None:
        """Refresh HUD elements from a TelemetryState-like object."""
        if state is None:
            self.horizon.set_attitude(0.0, 0.0)
            self.compass.set_heading(0.0)
            self.lbl_roll.setText("ROLL: --")
            self.lbl_pitch.setText("PITCH: --")
            self.lbl_hdg.setText("HDG: --")
            return

        roll_deg = self._angle_rad_to_deg(getattr(state, "roll", None))
        pitch_deg = self._angle_rad_to_deg(getattr(state, "pitch", None))
        hdg = self._heading(state)

        self.horizon.set_attitude(roll_deg, pitch_deg)
        self.compass.set_heading(hdg)

        roll_val = roll_deg if roll_deg is not None else 0.0
        pitch_val = pitch_deg if pitch_deg is not None else 0.0
        hdg_val = hdg if hdg is not None else 0.0

        self.lbl_roll.setText(f"R: {roll_val:+.1f}°")
        self.lbl_pitch.setText(f"P: {pitch_val:+.1f}°")
        self.lbl_hdg.setText(f"HDG: {hdg_val:03.0f}°")

    @staticmethod
    def _angle_rad_to_deg(angle: Any) -> Optional[float]:
        """Convert a MAVLink attitude angle from radians to degrees."""
        if angle is None:
            return None
        try:
            value = float(angle)
            if not math.isfinite(value):
                return None
            return math.degrees(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _heading(state: Any) -> Optional[float]:
        heading = getattr(state, "heading", None)
        if heading is None:
            heading = getattr(state, "vfr_heading", None)
        return heading
