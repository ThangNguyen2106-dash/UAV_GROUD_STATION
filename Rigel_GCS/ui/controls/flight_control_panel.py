from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FlightControlPanel(QFrame):
    """Realtime vehicle flight action and command panel."""

    def __init__(self, connection_manager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.connection_manager = connection_manager
        self.selected_key: Optional[tuple[str, int, int]] = None
        self._is_armed = False
        self._current_mode = "UNKNOWN"

        self.setObjectName("FlightControlPanel")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # ----------------------------------------------------
        # ARM / DISARM
        # ----------------------------------------------------
        arm_box = QGroupBox("ARM / DISARM CONTROL")
        arm_layout = QVBoxLayout(arm_box)
        arm_layout.setSpacing(6)

        self.arm_status_label = QLabel("STATUS: DISARMED")
        self.arm_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arm_status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.arm_status_label.setStyleSheet("color:#aeb7c0; padding:4px;")
        arm_layout.addWidget(self.arm_status_label)

        arm_btn_row = QHBoxLayout()
        self.btn_arm = QPushButton("🛡️ ARM")
        self.btn_arm.setFixedHeight(34)
        self.btn_arm.setStyleSheet("background:#15803d; color:white; font-weight:bold; border-radius:4px;")
        self.btn_arm.clicked.connect(self._on_arm_clicked)
        arm_btn_row.addWidget(self.btn_arm)

        self.btn_disarm = QPushButton("🛑 DISARM")
        self.btn_disarm.setFixedHeight(34)
        self.btn_disarm.setStyleSheet("background:#b91c1c; color:white; font-weight:bold; border-radius:4px;")
        self.btn_disarm.clicked.connect(self._on_disarm_clicked)
        arm_btn_row.addWidget(self.btn_disarm)
        arm_layout.addLayout(arm_btn_row)

        layout.addWidget(arm_box)

        # ----------------------------------------------------
        # FLIGHT MODES
        # ----------------------------------------------------
        mode_box = QGroupBox("FLIGHT MODES")
        mode_layout = QGridLayout(mode_box)
        mode_layout.setSpacing(6)

        mode_layout.addWidget(QLabel("Current Mode:"), 0, 0)
        self.current_mode_label = QLabel("UNKNOWN")
        self.current_mode_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.current_mode_label.setStyleSheet("color:#38bdf8;")
        mode_layout.addWidget(self.current_mode_label, 0, 1)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "LOITER",
            "POSHOLD",
            "GUIDED",
            "AUTO",
            "RTL",
            "LAND",
            "ALT_HOLD",
            "STABILIZE",
            "BRAKE",
        ])
        mode_layout.addWidget(self.mode_combo, 1, 0)

        self.btn_set_mode = QPushButton("Set Mode")
        self.btn_set_mode.setFixedHeight(28)
        self.btn_set_mode.clicked.connect(self._on_set_mode_clicked)
        mode_layout.addWidget(self.btn_set_mode, 1, 1)

        layout.addWidget(mode_box)

        # ----------------------------------------------------
        # ACTIONS / TAKEOFF / RTL / LAND
        # ----------------------------------------------------
        actions_box = QGroupBox("QUICK ACTIONS")
        act_layout = QVBoxLayout(actions_box)
        act_layout.setSpacing(8)

        # Takeoff row
        tk_row = QHBoxLayout()
        tk_row.addWidget(QLabel("Takeoff Alt (m):"))
        self.spin_takeoff_alt = QDoubleSpinBox()
        self.spin_takeoff_alt.setRange(1.0, 150.0)
        self.spin_takeoff_alt.setValue(5.0)
        self.spin_takeoff_alt.setSingleStep(1.0)
        tk_row.addWidget(self.spin_takeoff_alt)

        self.btn_takeoff = QPushButton("🚀 Takeoff")
        self.btn_takeoff.setFixedHeight(30)
        self.btn_takeoff.setStyleSheet("background:#0284c7; color:white; font-weight:bold; border-radius:4px;")
        self.btn_takeoff.clicked.connect(self._on_takeoff_clicked)
        tk_row.addWidget(self.btn_takeoff)
        act_layout.addLayout(tk_row)

        # RTL & Land
        quick_btns = QHBoxLayout()
        self.btn_rtl = QPushButton("🏠 Return to Launch (RTL)")
        self.btn_rtl.setFixedHeight(32)
        self.btn_rtl.setStyleSheet("background:#d97706; color:white; font-weight:bold; border-radius:4px;")
        self.btn_rtl.clicked.connect(self._on_rtl_clicked)
        quick_btns.addWidget(self.btn_rtl)

        self.btn_land = QPushButton("🛬 Land Now")
        self.btn_land.setFixedHeight(32)
        self.btn_land.setStyleSheet("background:#ea580c; color:white; font-weight:bold; border-radius:4px;")
        self.btn_land.clicked.connect(self._on_land_clicked)
        quick_btns.addWidget(self.btn_land)
        act_layout.addLayout(quick_btns)

        layout.addWidget(actions_box)
        layout.addStretch(1)

    def set_active_vehicle(self, key: Optional[tuple[str, int, int]]) -> None:
        self.selected_key = key

    def update_telemetry(self, state: Any) -> None:
        armed = bool(getattr(state, "armed", False))
        mode = getattr(state, "flight_mode", None) or getattr(state, "mode", "UNKNOWN")

        if armed != self._is_armed:
            self._is_armed = armed
            if self._is_armed:
                self.arm_status_label.setText("STATUS: ARMED")
                self.arm_status_label.setStyleSheet("color:#ef4444; font-weight:bold; background:rgba(239,68,68,0.15); border-radius:4px; padding:4px;")
            else:
                self.arm_status_label.setText("STATUS: DISARMED")
                self.arm_status_label.setStyleSheet("color:#aeb7c0; padding:4px;")

        if mode != self._current_mode:
            self._current_mode = str(mode)
            self.current_mode_label.setText(self._current_mode)

    def _get_target(self) -> tuple[int, int, Optional[str]]:
        if self.selected_key is None:
            return 1, 1, None
        transport, sysid, compid = self.selected_key
        return sysid, compid, transport

    def _on_arm_clicked(self) -> None:
        sysid, compid, transport = self._get_target()
        reply = QMessageBox.question(
            self,
            "Confirm ARM",
            f"Are you sure you want to ARM Drone ID {sysid}?\nMotors will begin spinning!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.connection_manager.arm_disarm(
                arm=True,
                force=False,
                target_system=sysid,
                target_component=compid,
                transport=transport,
            )

    def _on_disarm_clicked(self) -> None:
        sysid, compid, transport = self._get_target()
        reply = QMessageBox.warning(
            self,
            "Confirm DISARM",
            f"Are you sure you want to DISARM Drone ID {sysid}?\nIf airborne, the vehicle will DROP!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.connection_manager.arm_disarm(
                arm=False,
                force=True,
                target_system=sysid,
                target_component=compid,
                transport=transport,
            )

    def _on_set_mode_clicked(self) -> None:
        sysid, compid, transport = self._get_target()
        mode = self.mode_combo.currentText()
        self.connection_manager.set_mode(
            mode_name=mode,
            target_system=sysid,
            target_component=compid,
            transport=transport,
        )

    def _on_takeoff_clicked(self) -> None:
        sysid, compid, transport = self._get_target()
        alt = self.spin_takeoff_alt.value()
        reply = QMessageBox.question(
            self,
            "Confirm Auto Takeoff",
            f"Initiate automatic takeoff to altitude {alt:.1f} meters for Drone ID {sysid}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Set GUIDED mode first, then send TAKEOFF
            self.connection_manager.set_mode("GUIDED", sysid, compid, transport)
            self.connection_manager.takeoff(alt, sysid, compid, transport)

    def _on_rtl_clicked(self) -> None:
        sysid, compid, transport = self._get_target()
        self.connection_manager.return_to_launch(sysid, compid, transport)

    def _on_land_clicked(self) -> None:
        sysid, compid, transport = self._get_target()
        self.connection_manager.land(sysid, compid, transport)
