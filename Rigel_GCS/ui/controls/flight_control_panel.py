from __future__ import annotations

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
    """Compact realtime vehicle status badge and sensor health panel (Display Only)."""

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
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # ----------------------------------------------------
        # 1. ARM & MODE STATUS (COMPACT SIDE-BY-SIDE)
        # ----------------------------------------------------
        status_box = QGroupBox("VEHICLE STATE")
        s_layout = QGridLayout(status_box)
        s_layout.setContentsMargins(6, 6, 6, 6)
        s_layout.setSpacing(6)

        self.arm_status_badge = QLabel("DISARMED")
        self.arm_status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arm_status_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.arm_status_badge.setStyleSheet("""
            QLabel {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 4px;
            }
        """)
        s_layout.addWidget(QLabel("Motors:"), 0, 0)
        s_layout.addWidget(self.arm_status_badge, 0, 1)

        self.mode_badge = QLabel("--")
        self.mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mode_badge.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.mode_badge.setStyleSheet("""
            QLabel {
                background: rgba(2, 132, 199, 0.15);
                color: #38bdf8;
                border: 1px solid #0284c7;
                border-radius: 4px;
                padding: 6px 4px;
            }
        """)
        s_layout.addWidget(QLabel("Mode:"), 1, 0)
        s_layout.addWidget(self.mode_badge, 1, 1)

        layout.addWidget(status_box)

    def set_active_vehicle(self, key: Optional[tuple[str, int, int]]) -> None:
        self.selected_key = key
        if key is None:
            self._reset_display()

    def update_telemetry(self, state: Any) -> None:
        if state is None:
            self._reset_display()
            return

        armed = bool(getattr(state, "armed", False))
        if armed != self._is_armed:
            self._is_armed = armed
            if self._is_armed:
                self.arm_status_badge.setText("⚠️ ARMED")
                self.arm_status_badge.setStyleSheet("""
                    QLabel {
                        background: rgba(239, 68, 68, 0.2);
                        color: #ef4444;
                        border: 1px solid #ef4444;
                        border-radius: 4px;
                        padding: 6px 4px;
                        font-weight: bold;
                    }
                """)
            else:
                self.arm_status_badge.setText("🔒 DISARMED")
                self.arm_status_badge.setStyleSheet("""
                    QLabel {
                        background: #1e293b;
                        color: #94a3b8;
                        border: 1px solid #334155;
                        border-radius: 4px;
                        padding: 6px 4px;
                        font-weight: bold;
                    }
                """)

        mode = getattr(state, "flight_mode", None) or getattr(state, "mode", "--")
        mode_str = str(mode).upper()
        if mode_str != self._current_mode:
            self._current_mode = mode_str
            self.mode_badge.setText(self._current_mode)

    def _reset_display(self) -> None:
        self._is_armed = False
        self._current_mode = "--"
        self.arm_status_badge.setText("DISARMED")
        self.arm_status_badge.setStyleSheet("""
            QLabel {
                background: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 4px;
            }
        """)
        self.mode_badge.setText("--")


# Compatibility Alias
FlightControlPanel = FlightStatusPanel
