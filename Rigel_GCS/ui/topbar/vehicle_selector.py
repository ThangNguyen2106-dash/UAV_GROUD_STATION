from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QWidget

from ...core.active_vehicle import ActiveVehicleManager, VehicleCandidate


class VehicleSelector(QGroupBox):
    """Displays discovered MAVLink vehicles and controls active selection."""

    vehicle_selected = Signal(object)

    def __init__(self, connection_manager, parent: Optional[QWidget] = None) -> None:
        super().__init__("VEHICLE", parent)
        self.connection_manager = connection_manager
        self.active_manager = ActiveVehicleManager()
        self._updating = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self.status = QLabel("No vehicle")
        self.combo = QComboBox()
        self.combo.setMinimumWidth(330)
        self.combo.currentIndexChanged.connect(self._selected)
        layout.addWidget(self.status)
        layout.addWidget(self.combo, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def refresh(self) -> None:
        try:
            candidates = self.active_manager.refresh(self.connection_manager)
        except Exception as exc:
            self.status.setText("Vehicle error")
            return

        current = self.active_manager.active
        self._updating = True
        self.combo.clear()
        self.combo.addItem("-- SELECT VEHICLE --", None)
        selected_index = 0

        for candidate in candidates:
            self.combo.addItem(candidate.display_name, candidate)
            if current and self._same(current, candidate):
                selected_index = self.combo.count() - 1

        self.combo.setCurrentIndex(selected_index)
        self._updating = False

        if current:
            self.status.setText("ACTIVE")
        elif len(candidates) > 1:
            self.status.setText("SELECT")
        elif len(candidates) == 1:
            self.status.setText("AUTO")
        else:
            self.status.setText("No vehicle")

    @staticmethod
    def _same(a: VehicleCandidate, b: VehicleCandidate) -> bool:
        return (
            a.link_key == b.link_key
            and a.sysid == b.sysid
            and a.compid == b.compid
        )

    def _selected(self, index: int) -> None:
        if self._updating or index <= 0:
            return
        candidate = self.combo.itemData(index)
        if candidate is None:
            return
        try:
            selected = self.active_manager.select(candidate.index)
        except Exception:
            return
        self.status.setText("ACTIVE")
        self.vehicle_selected.emit(selected)
