from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QFont, QPainter
from PySide6.QtWidgets import QWidget


class FlightStatus(QWidget):
    """Status block for arm state, mode, GPS and link state."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._armed: Optional[bool] = None
        self._mode: Optional[str] = None
        self._fix: Optional[int] = None
        self._sats: Optional[int] = None
        self._connected = False
        self.setMinimumHeight(104)

    def update_state(self, state: Any) -> None:
        self._armed = getattr(state, "armed", None)
        self._mode = getattr(state, "flight_mode", None)
        if self._mode is None:
            self._mode = getattr(state, "mode", None)
        self._fix = getattr(state, "fix_type", None)
        self._sats = getattr(state, "satellites_visible", None)
        self._connected = bool(getattr(state, "connected", False))
        self.update()

    def set_status(self, *, armed=None, mode=None, fix=None, sats=None, connected=None) -> None:
        if armed is not None:
            self._armed = bool(armed)
        if mode is not None:
            self._mode = str(mode)
        if fix is not None:
            self._fix = int(fix)
        if sats is not None:
            self._sats = int(sats)
        if connected is not None:
            self._connected = bool(connected)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QBrush("#11161c"))

        w = self.width()
        x = 10
        y = 8

        armed_text = "ARMED" if self._armed else "DISARMED"
        armed_font = QFont("Arial", 14, QFont.Weight.Bold)
        painter.setFont(armed_font)
        painter.setPen("#e65a5a" if self._armed else "#aeb7c0")
        painter.drawText(x, y, w - 20, 24, Qt.AlignmentFlag.AlignCenter, armed_text)

        painter.setFont(QFont("Arial", 9))
        painter.setPen("#d5dbe0")
        mode = self._mode or "UNKNOWN"
        link = "ONLINE" if self._connected else "OFFLINE"
        painter.drawText(x, 37, w - 20, 18, Qt.AlignmentFlag.AlignCenter, f"MODE: {mode}")
        painter.drawText(x, 58, w - 20, 16, Qt.AlignmentFlag.AlignCenter, f"GPS FIX: {self._fix_text()}   SAT: {self._sats_text()}")
        painter.drawText(x, 78, w - 20, 16, Qt.AlignmentFlag.AlignCenter, f"LINK: {link}")

    def _fix_text(self) -> str:
        names = {
            0: "NO GPS",
            1: "NO FIX",
            2: "2D",
            3: "3D",
            4: "DGPS",
            5: "RTK FLOAT",
            6: "RTK FIX",
        }
        if self._fix is None:
            return "--"
        return names.get(int(self._fix), str(self._fix))

    def _sats_text(self) -> str:
        return "--" if self._sats is None else str(self._sats)
