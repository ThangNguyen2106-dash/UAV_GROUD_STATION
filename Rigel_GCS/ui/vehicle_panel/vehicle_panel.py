from __future__ import annotations

from typing import Any, Optional

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from .hud.hud_widget import HUDWidget


class VehiclePanel(QFrame):
    """Vehicle-side panel.

    HUD is active now. Telemetry and camera sections can be added below it
    later without changing MainWindow's layout.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("VehiclePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.hud = HUDWidget()
        layout.addWidget(self.hud, 1)

    def update_telemetry(self, state: Any) -> None:
        self.hud.update_telemetry(state)
