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
        armed = getattr(state, "armed", None)
        mode = getattr(state, "flight_mode", None)
        if mode is None:
            mode = getattr(state, "mode", None)
        fix = getattr(state, "fix_type", None)
        sats = getattr(state, "satellites_visible", None)
        connected = bool(getattr(state, "connected", False))

        if (
            armed != self._armed
            or mode != self._mode
            or fix != self._fix
            or sats != self._sats
            or connected != self._connected
        ):
            self._armed = armed
            self._mode = mode
            self._fix = fix
            self._sats = sats
            self._connected = connected
            self.update()

    def set_status(self, *, armed=None, mode=None, fix=None, sats=None, connected=None) -> None:
        changed = False
        if armed is not None and bool(armed) != self._armed:
            self._armed = bool(armed)
            changed = True
        if mode is not None and str(mode) != self._mode:
            self._mode = str(mode)
            changed = True
        if fix is not None and int(fix) != self._fix:
            self._fix = int(fix)
            changed = True
        if sats is not None and int(sats) != self._sats:
            self._sats = int(sats)
            changed = True
        if connected is not None and bool(connected) != self._connected:
            self._connected = bool(connected)
            changed = True
        if changed:
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
