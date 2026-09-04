from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .connection_selector import ConnectionSelector
from .vehicle_selector import VehicleSelector


class TopBar(QFrame):
    """Main RIGEL top bar.

    Layout is intentionally compact: application navigation on the left,
    connection source in the middle, and active vehicle on the right.
    """

    connect_requested = Signal(dict)
    disconnect_requested = Signal()
    vehicle_selected = Signal(object)

    def __init__(self, connection_manager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.connection_manager = connection_manager
        self.setObjectName("TopBar")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)

        nav = QHBoxLayout()
        title = QLabel("RIGEL")
        title.setObjectName("AppTitle")
        nav.addWidget(title)

        for text in ("DATA", "PLAN", "SETUP", "CONFIG", "SIMULATION"):
            button = QLabel(text)
            button.setObjectName("NavItem")
            nav.addWidget(button)
        nav.addStretch(1)
        self.connection_status = QLabel("DISCONNECTED")
        self.connection_status.setObjectName("ConnectionStatus")
        nav.addWidget(self.connection_status)
        root.addLayout(nav)

        controls = QHBoxLayout()
        self.connection_selector = ConnectionSelector()
        self.vehicle_selector = VehicleSelector(self.connection_manager)
        controls.addWidget(self.connection_selector, 0)
        controls.addWidget(self.vehicle_selector, 1)
        root.addLayout(controls)

        self.connection_selector.connect_requested.connect(self.connect_requested.emit)
        self.connection_selector.disconnect_requested.connect(self.disconnect_requested.emit)
        self.vehicle_selector.vehicle_selected.connect(self.vehicle_selected.emit)

    def set_connection_status(self, text: str) -> None:
        self.connection_status.setText(str(text).upper())
