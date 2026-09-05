from __future__ import annotations

from typing import Any, Optional
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class SafetyBannerWidget(QFrame):
    """Realtime visual safety alert banner."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("SafetyBannerWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.icon_label = QLabel("🟢")
        self.icon_label.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.icon_label)

        self.text_label = QLabel("ALL SYSTEMS NOMINAL")
        self.text_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.text_label.setStyleSheet("color: #4ade80;")
        layout.addWidget(self.text_label, 1)

        self.setStyleSheet("""
            QFrame#SafetyBannerWidget {
                background: rgba(34, 197, 94, 0.1);
                border: 1px solid rgba(34, 197, 94, 0.3);
                border-radius: 6px;
            }
        """)

    def update_state(self, state: Any) -> None:
        if state is None:
            self._set_banner("📡 WAITING FOR TELEMETRY...", "#94a3b8", "rgba(148, 163, 184, 0.1)", "rgba(148, 163, 184, 0.3)", "⚪")
            return

        armed = bool(getattr(state, "armed", False))
        bat_pct = getattr(state, "battery_remaining", None)
        bat_v = getattr(state, "battery_voltage", None)
        gps_fix = getattr(state, "gps_fix_type", 0) or 0
        last_update = getattr(state, "last_update", None)

        # 1. Telemetry Link Lost Check
        if last_update is not None and (time.monotonic() - last_update) > 3.5:
            self._set_banner("⚠️ TELEMETRY LINK LOST (> 3.5s)", "#f87171", "rgba(239, 68, 68, 0.2)", "rgba(239, 68, 68, 0.5)", "🔴")
            return

        # 2. Critical Battery Check (< 12% or < 14.0V on 4S)
        if bat_pct is not None and bat_pct <= 12.0:
            self._set_banner(f"🚨 CRITICAL BATTERY: {bat_pct:.0f}% ({bat_v:.1f}V) - LAND IMMEDIATELY!", "#ef4444", "rgba(239, 68, 68, 0.25)", "#ef4444", "🚨")
            return

        # 3. Low Battery Warning (< 25%)
        if bat_pct is not None and bat_pct <= 25.0:
            self._set_banner(f"⚠️ LOW BATTERY WARNING: {bat_pct:.0f}% ({bat_v:.1f}V)", "#f59e0b", "rgba(245, 158, 11, 0.2)", "rgba(245, 158, 11, 0.5)", "🟡")
            return

        # 4. GPS Fix Warning (Armed but GPS Fix < 3)
        if armed and gps_fix < 3:
            self._set_banner("⚠️ POOR GPS FIX - FLIGHT IN NON-GPS MODE", "#f59e0b", "rgba(245, 158, 11, 0.2)", "rgba(245, 158, 11, 0.5)", "🟡")
            return

        # 5. Armed Flight Active
        if armed:
            self._set_banner("⚡ MOTORS ARMED - FLIGHT ACTIVE", "#38bdf8", "rgba(56, 189, 248, 0.15)", "rgba(56, 189, 248, 0.4)", "✈️")
            return

        # 6. Standby Nominal
        self._set_banner("ALL SYSTEMS NOMINAL (SAFE TO ARM)", "#4ade80", "rgba(34, 197, 94, 0.1)", "rgba(34, 197, 94, 0.3)", "🟢")

    def _set_banner(self, text: str, text_color: str, bg_color: str, border_color: str, icon: str) -> None:
        self.text_label.setText(text)
        self.text_label.setStyleSheet(f"color: {text_color};")
        self.icon_label.setText(icon)
        self.setStyleSheet(f"""
            QFrame#SafetyBannerWidget {{
                background: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
