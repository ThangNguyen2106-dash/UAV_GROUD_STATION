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
    """Main left-side HUD.

    TelemetryState receives MAVLink ATTITUDE roll/pitch in radians.
    The ArtificialHorizon uses degrees, so conversion is performed here
    at the UI boundary.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setObjectName("HUDWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(300)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        title = QLabel("HUD")
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        self.horizon = ArtificialHorizon()
        root.addWidget(self.horizon, 1)

        self.compass = Compass()
        root.addWidget(self.compass)

        self.flight_status = FlightStatus()
        root.addWidget(self.flight_status)

        self.values = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)

        fields = [
            ("ALT", "altitude", "m"),
            ("REL ALT", "relative_altitude", "m"),
            ("GS", "ground_speed", "m/s"),
            ("V/S", "velocity_z", "m/s"),
            ("BAT", "voltage_battery", "V"),
            ("BAT %", "battery_remaining", "%"),
        ]

        for row, (label, attr, unit) in enumerate(fields):
            name = QLabel(label)
            name.setStyleSheet("color:#9da7b0;")

            value = QLabel("--")
            value.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            value.setAlignment(Qt.AlignmentFlag.AlignRight)

            self.values[attr] = (value, unit)

            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)

        root.addLayout(grid)

        self.position_label = QLabel("LAT --   LON --")
        self.position_label.setStyleSheet(
            "color:#9da7b0; font-size:9px;"
        )
        self.position_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        root.addWidget(self.position_label)

        root.addStretch(1)

    def update_telemetry(self, state: Any) -> None:
        """Refresh every HUD element from a TelemetryState-like object."""

        # MAVLink ATTITUDE.roll/pitch are radians.
        # ArtificialHorizon expects degrees.
        roll_deg = self._angle_rad_to_deg(
            getattr(state, "roll", None)
        )
        pitch_deg = self._angle_rad_to_deg(
            getattr(state, "pitch", None)
        )

        self.horizon.set_attitude(
            roll_deg,
            pitch_deg,
        )

        self.compass.set_heading(
            self._heading(state)
        )

        self.flight_status.update_state(state)

        for attr, (label, unit) in self.values.items():
            value = getattr(state, attr, None)

            if value is None and attr == "ground_speed":
                value = getattr(
                    state,
                    "groundspeed",
                    None,
                )

            label.setText(
                self._format_value(
                    value,
                    unit,
                )
            )

        lat = getattr(state, "latitude", None)
        lon = getattr(state, "longitude", None)

        if lat is None or lon is None:
            self.position_label.setText(
                "LAT --   LON --"
            )
        else:
            try:
                self.position_label.setText(
                    f"LAT {float(lat):.7f}   "
                    f"LON {float(lon):.7f}"
                )
            except (TypeError, ValueError):
                self.position_label.setText(
                    "LAT --   LON --"
                )

    @staticmethod
    def _angle_rad_to_deg(
        angle: Any,
    ) -> Optional[float]:
        """Convert a MAVLink attitude angle from radians to degrees."""

        if angle is None:
            return None

        try:
            value = float(angle)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(value):
            return None

        return math.degrees(value)

    @staticmethod
    def _heading(state: Any) -> Optional[float]:
        heading = getattr(
            state,
            "heading",
            None,
        )

        if heading is None:
            heading = getattr(
                state,
                "vfr_heading",
                None,
            )

        return heading

    @staticmethod
    def _format_value(
        value: Any,
        unit: str,
    ) -> str:
        if value is None:
            return "--"

        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        if unit == "%":
            return f"{number:.0f} %"

        if unit == "m":
            return f"{number:.2f} m"

        if unit == "m/s":
            return f"{number:.2f} m/s"

        if unit == "V":
            return f"{number:.2f} V"

        return f"{number:.2f} {unit}".strip()
