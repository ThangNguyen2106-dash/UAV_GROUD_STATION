from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from serial.tools import list_ports
except Exception:  # pragma: no cover - serial is optional at UI import time
    list_ports = None


from Rigel_GCS.core.telemetry_logger import TelemetryLogger
from Rigel_GCS.ui.controls.flight_control_panel import FlightControlPanel
from Rigel_GCS.ui.map.map_widget import MapWidget
from Rigel_GCS.ui.mission.mission_panel import MissionPanel
from Rigel_GCS.ui.vehicle_panel.vehicle_panel import VehiclePanel


class NoWheelSpinBox(QSpinBox):
    """Prevent accidental value changes when the mouse wheel is over a spin box."""

    def wheelEvent(self, event) -> None:
        # Ignore the wheel event instead of changing the value.
        event.ignore()


class ValueLabel(QLabel):
    """Small telemetry value label with a stable width."""

    def __init__(self, value: str = "--") -> None:
        super().__init__(value)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setMinimumWidth(105)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)


class MainWindow(QMainWindow):
    """RIGEL GCS main window.

    Layout intentionally follows a Mission-Planner-like concept:

        LEFT  = connection/device/telemetry information
        RIGHT = reserved for map + basic vehicle controls

    The right area is deliberately a placeholder so it can later be
    replaced by the mission map and command panels without redesigning
    the telemetry/device architecture.
    """

    POLL_MS = 250
    HUD_POLL_MS = 16

    def __init__(self, connection_manager) -> None:
        super().__init__()
        self.connection_manager = connection_manager
        self.selected_key: Optional[tuple[str, int, int]] = None
        self._updating_devices = False
        self.logger = TelemetryLogger()

        self.setWindowTitle("RIGEL Ground Station")
        self.resize(1400, 850)
        self.setMinimumSize(820, 520)

        self._build_ui()
        self._apply_style()
        self._refresh_serial_ports()

        # ============================================================
        # SLOW UI TIMER
        # ============================================================
        self.timer = QTimer(self)
        self.timer.setInterval(self.POLL_MS)
        self.timer.timeout.connect(self._refresh_runtime)
        self.timer.start()

        # ============================================================
        # REALTIME HUD TIMER (60 FPS)
        # ============================================================
        self.hud_timer = QTimer(self)
        self.hud_timer.setInterval(self.HUD_POLL_MS)   # 60 FPS
        self.hud_timer.timeout.connect(self._refresh_hud)
        self.hud_timer.start()

    # ============================================================
    # UI BUILD
    # ============================================================

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Top-level Tabs
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet("""
            QTabBar::tab {
                font-weight: bold;
                font-size: 13px;
                padding: 8px 24px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #0284c7;
                color: white;
                border-radius: 4px;
            }
            QTabBar::tab:!selected {
                background: #1e293b;
                color: #94a3b8;
                border-radius: 4px;
            }
        """)

        # ========================================================
        # TAB 1: 📊 DATA (FLIGHT DATA & LIVE MONITORING)
        # ========================================================
        tab_data = QWidget()
        data_layout = QHBoxLayout(tab_data)
        data_layout.setContentsMargins(0, 4, 0, 0)
        data_layout.setSpacing(8)

        data_splitter = QSplitter(Qt.Horizontal)
        data_splitter.setChildrenCollapsible(False)

        # Left Sidebar (Connection, Active Drone, HUD, Telemetry Table)
        sidebar = QWidget()
        sidebar.setMinimumWidth(285)
        sidebar.setMaximumWidth(420)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(7)

        side.addWidget(self._build_connection_box())
        side.addWidget(self._build_vehicle_selector())
        side.addWidget(self._build_hud_box())
        side.addWidget(self._build_telemetry_box())

        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setWidget(sidebar)
        data_splitter.addWidget(sidebar_scroll)

        # Center/Right of Tab 1: Live Flight Map + Quick Flight Controls
        data_center_splitter = QSplitter(Qt.Horizontal)
        data_center_splitter.setChildrenCollapsible(False)

        # Live Map (Read-only waypoint mode: enable_waypoint_click=False)
        self.data_map = MapWidget(enable_waypoint_click=False)
        data_center_splitter.addWidget(self.data_map)

        # Flight Controls Panel (Right column of Data tab)
        self.flight_controls = FlightControlPanel(self.connection_manager)
        self.flight_controls.setMinimumWidth(300)
        self.flight_controls.setMaximumWidth(380)
        data_center_splitter.addWidget(self.flight_controls)
        data_center_splitter.setSizes([850, 320])

        data_splitter.addWidget(data_center_splitter)
        data_splitter.setSizes([340, 1100])
        data_layout.addWidget(data_splitter)

        self.main_tabs.addTab(tab_data, "📊 DATA (FLIGHT DATA)")

        # ========================================================
        # TAB 2: 📍 MISSION (MISSION PLANNER & WAYPOINT EDITOR)
        # ========================================================
        tab_mission = QWidget()
        mission_layout = QHBoxLayout(tab_mission)
        mission_layout.setContentsMargins(0, 4, 0, 0)
        mission_layout.setSpacing(8)

        mission_splitter = QSplitter(Qt.Horizontal)
        mission_splitter.setChildrenCollapsible(False)

        # Mission Map (Interactive waypoint click mode: enable_waypoint_click=True)
        self.mission_map = MapWidget(enable_waypoint_click=True)
        mission_splitter.addWidget(self.mission_map)

        # Mission Planner Panel (Right side of Mission tab)
        self.mission_panel = MissionPanel(self.connection_manager)
        self.mission_panel.setMinimumWidth(380)
        self.mission_panel.setMaximumWidth(520)
        mission_splitter.addWidget(self.mission_panel)
        mission_splitter.setSizes([950, 450])

        mission_layout.addWidget(mission_splitter)
        self.main_tabs.addTab(tab_mission, "📍 MISSION (PLANNER)")

        main_layout.addWidget(self.main_tabs)

        # Connect Waypoint signals:
        # 1. Clicking on Mission Map adds a Waypoint in Mission Panel
        self.mission_map.waypoint_clicked.connect(self.mission_panel.add_waypoint)

        # 2. When waypoints change in Mission Panel: sync to BOTH Mission Map and Data Map!
        self.mission_panel.waypoints_changed.connect(self.mission_map.update_waypoints_display)
        self.mission_panel.waypoints_changed.connect(self.data_map.update_waypoints_display)

        self.workspace_status = QLabel("Ready")

    def _build_connection_box(self) -> QGroupBox:
        box = QGroupBox("LINK / CONNECTION")
        layout = QVBoxLayout(box)
        layout.setSpacing(6)

        row = QHBoxLayout()
        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["SERIAL", "UDP"])
        self.transport_combo.currentTextChanged.connect(self._on_transport_changed)
        row.addWidget(QLabel("Transport"))
        row.addWidget(self.transport_combo, 1)
        layout.addLayout(row)

        self.serial_widget = QWidget()
        serial_layout = QGridLayout(self.serial_widget)
        serial_layout.setContentsMargins(0, 0, 0, 0)
        serial_layout.addWidget(QLabel("COM"), 0, 0)
        self.com_combo = QComboBox()
        self.com_combo.setEditable(True)
        serial_layout.addWidget(self.com_combo, 0, 1)
        serial_layout.addWidget(QLabel("Baud"), 1, 0)
        self.baud_spin = NoWheelSpinBox()
        self.baud_spin.setRange(1200, 2000000)
        self.baud_spin.setValue(115200)
        serial_layout.addWidget(self.baud_spin, 1, 1)
        self.refresh_com_button = QPushButton("Refresh")
        self.refresh_com_button.clicked.connect(self._refresh_serial_ports)
        serial_layout.addWidget(self.refresh_com_button, 2, 0, 1, 2)
        layout.addWidget(self.serial_widget)

        self.udp_widget = QWidget()
        udp_layout = QGridLayout(self.udp_widget)
        udp_layout.setContentsMargins(0, 0, 0, 0)
        udp_layout.addWidget(QLabel("RX host"), 0, 0)
        self.udp_rx_host = QLineEdit("0.0.0.0")
        udp_layout.addWidget(self.udp_rx_host, 0, 1)
        udp_layout.addWidget(QLabel("RX port"), 1, 0)
        self.udp_rx_port = NoWheelSpinBox()
        self.udp_rx_port.setRange(1, 65535)
        self.udp_rx_port.setValue(14550)
        udp_layout.addWidget(self.udp_rx_port, 1, 1)
        udp_layout.addWidget(QLabel("TX host"), 2, 0)
        self.udp_tx_host = QLineEdit("127.0.0.1")
        udp_layout.addWidget(self.udp_tx_host, 2, 1)
        udp_layout.addWidget(QLabel("TX port"), 3, 0)
        self.udp_tx_port = NoWheelSpinBox()
        self.udp_tx_port.setRange(1, 65535)
        self.udp_tx_port.setValue(14560)
        udp_layout.addWidget(self.udp_tx_port, 3, 1)
        layout.addWidget(self.udp_widget)
        self.udp_widget.hide()

        buttons = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.clicked.connect(self._disconnect)
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.disconnect_button)
        layout.addLayout(buttons)

        self.connection_status = QLabel("DISCONNECTED")
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.connection_status)
        return box

    def _build_hud_box(self) -> QGroupBox:
        box = QGroupBox("VEHICLE HUD")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.hud = VehiclePanel()
        self.hud.setMinimumWidth(250)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.hud)
        return box

    def _build_vehicle_selector(self) -> QGroupBox:
        box = QGroupBox("ACTIVE DRONE")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.device_combo = QComboBox()
        self.device_combo.addItem("No drone detected", None)
        self.device_combo.currentIndexChanged.connect(self._on_device_combo_changed)
        layout.addWidget(self.device_combo)
        return box

    def _build_telemetry_box(self) -> QGroupBox:
        box = QGroupBox("SELECTED VEHICLE")
        layout = QVBoxLayout(box)
        layout.setSpacing(3)

        self.selected_title = QLabel("No vehicle selected")
        self.selected_title.setObjectName("selectedTitle")
        layout.addWidget(self.selected_title)

        self.selected_link = QLabel("--")
        self.selected_link.setObjectName("selectedLink")
        layout.addWidget(self.selected_link)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(3)
        self.telemetry_values: dict[str, ValueLabel] = {}

        sections = [
            ("POSITION", [
                ("Latitude", "latitude", "{}", "deg"),
                ("Longitude", "longitude", "{}", "deg"),
                ("Altitude", "altitude", "{}", "m"),
                ("Rel. Alt", "relative_altitude", "{}", "m"),
                ("Ground Speed", "ground_speed", "{}", "m/s"),
                ("Heading", "heading", "{}", "deg"),
            ]),
            ("GPS", [
                ("Fix", "fix_type", "{}", ""),
                ("Satellites", "satellites_visible", "{}", ""),
            ]),
            ("ATTITUDE", [
                ("Roll", "roll", "{}", "rad"),
                ("Pitch", "pitch", "{}", "rad"),
                ("Yaw", "yaw", "{}", "rad"),
            ]),
            ("BATTERY", [
                ("Voltage", "voltage_battery", "{}", "V"),
                ("Current", "current_battery", "{}", "A"),
                ("Battery", "battery_remaining", "{}", "%"),
            ]),
            ("SYSTEM", [
                ("Armed", "armed", "{}", ""),
                ("Mode", "custom_mode", "{}", ""),
                ("MAV type", "mav_type", "{}", ""),
                ("Autopilot", "autopilot", "{}", ""),
            ]),
        ]

        row = 0
        for section_name, fields in sections:
            label = QLabel(section_name)
            label.setObjectName("telemetrySection")
            grid.addWidget(label, row, 0, 1, 3)
            row += 1
            for title, attr, _fmt, unit in fields:
                grid.addWidget(QLabel(title), row, 0)
                value = ValueLabel()
                self.telemetry_values[attr] = value
                grid.addWidget(value, row, 1)
                grid.addWidget(QLabel(unit), row, 2)
                row += 1

        layout.addLayout(grid)

        self.last_update_label = QLabel("Last telemetry: --")
        self.last_update_label.setObjectName("lastUpdate")
        layout.addWidget(self.last_update_label)
        return box

    # ============================================================
    # CONNECTION ACTIONS
    # ============================================================

    def _connect(self) -> None:
        try:
            if self.transport_combo.currentText() == "SERIAL":
                port = self.com_combo.currentText().strip()
                if not port:
                    raise ValueError("Please select a COM port.")
                self.connection_manager.connect_serial(
                    port,
                    self.baud_spin.value(),
                    wait=False,
                )
            else:
                self.connection_manager.connect_udp(
                    rx_host=self.udp_rx_host.text().strip(),
                    rx_port=self.udp_rx_port.value(),
                    tx_host=self.udp_tx_host.text().strip(),
                    tx_port=self.udp_tx_port.value(),
                    wait=False,
                )
        except Exception as exc:
            QMessageBox.critical(self, "Connection error", str(exc))

    def _disconnect(self) -> None:
        try:
            self.connection_manager.disconnect()
        except Exception as exc:
            QMessageBox.warning(self, "Disconnect error", str(exc))

    # ============================================================
    # RUNTIME REFRESH
    # ============================================================
    def _refresh_hud(self) -> None:
        if self.selected_key is None:
            return

        transport, sysid, compid = self.selected_key

        state = self.connection_manager.get_telemetry(
            sysid,
            compid,
            transport,
        )

        if state is None:
            return

        self.hud.update_telemetry(state)
        self.data_map.update_uav_telemetry(state)
        self.mission_map.update_uav_telemetry(state)
        self.flight_controls.update_telemetry(state)
        self.mission_panel.update_telemetry(state)
        self.logger.log_state(state)


    def _refresh_runtime(self) -> None:
        self._refresh_connection_status()
        self._refresh_devices()

    def _refresh_connection_status(self) -> None:
        state = getattr(self.connection_manager.state, "value", str(self.connection_manager.state))
        self.connection_status.setText(str(state).upper())

    def _refresh_devices(self) -> None:
        devices = self.connection_manager.get_devices()

        candidates = []
        for device in devices:
            transport = str(getattr(device, "transport", "UNKNOWN") or "UNKNOWN").upper()
            sysid = int(getattr(device, "sysid", 0))
            compid = int(getattr(device, "compid", 0))
            candidates.append((transport, sysid, compid))

        candidates.sort(key=lambda x: (x[1], x[0], x[2]))
        new_keys = [(x[0], x[1], x[2]) for x in candidates]

        old_keys = []
        for i in range(self.device_combo.count()):
            key = self.device_combo.itemData(i)
            if key is not None:
                old_keys.append(tuple(key))

        if new_keys != old_keys:
            current_key = self.selected_key
            self._updating_devices = True
            self.device_combo.clear()

            if not candidates:
                self.device_combo.addItem("No drone detected", None)
                self.selected_key = None
                self._clear_telemetry()
            else:
                for transport, sysid, compid in candidates:
                    key = (transport, sysid, compid)
                    item_text = f"Drone ID: {sysid}"
                    self.device_combo.addItem(item_text, key)

                # Keep current selection or default to index 0
                index_to_select = 0
                if current_key is not None:
                    for i in range(self.device_combo.count()):
                        if self.device_combo.itemData(i) == current_key:
                            index_to_select = i
                            break

                self.device_combo.setCurrentIndex(index_to_select)
                self.selected_key = self.device_combo.itemData(index_to_select)
                self._refresh_selected_telemetry()

            self._updating_devices = False

    def _refresh_selected_telemetry(self) -> None:
        if self.selected_key is None:
            self._clear_telemetry()
            return

        transport, sysid, compid = self.selected_key
        state = self.connection_manager.get_telemetry(sysid, compid, transport)
        device = self.connection_manager.get_device(sysid, compid, transport)
        if state is None:
            return

        self.selected_title.setText(f"Drone ID: {sysid}")
        self.hud.update_telemetry(state)
        self.flight_controls.set_active_vehicle(self.selected_key)
        self.mission_panel.set_active_vehicle(self.selected_key)
        self.flight_controls.update_telemetry(state)
        self.mission_panel.update_telemetry(state)
        self.data_map.update_uav_telemetry(state)
        self.mission_map.update_uav_telemetry(state)

        rx = getattr(state, "rx_endpoint", None) or getattr(device, "rx_endpoint", None) or "--"
        tx = getattr(state, "tx_endpoint", None) or getattr(device, "tx_endpoint", None) or "--"
        self.selected_link.setText(f"Port: {transport}   |   RX: {rx}")
        self.workspace_status.setText(f"Active vehicle: Drone ID {sysid}")

        for attr, label in self.telemetry_values.items():
            value = getattr(state, attr, None)
            label.setText(self._format_value(attr, value))

        last_update = getattr(state, "last_update", None)
        if last_update is None:
            self.last_update_label.setText("Last telemetry: --")
        else:
            # last_update is monotonic time; calculate age instead of displaying it.
            import time
            age = max(0.0, time.monotonic() - last_update)
            self.last_update_label.setText(f"Last telemetry: {age:.1f}s ago")

    def _clear_telemetry(self) -> None:
        self.selected_title.setText("No vehicle selected")
        self.selected_link.setText("--")
        self.workspace_status.setText("No active vehicle")
        self.flight_controls.set_active_vehicle(None)
        self.mission_panel.set_active_vehicle(None)
        for label in self.telemetry_values.values():
            label.setText("--")
        self.last_update_label.setText("Last telemetry: --")

    @staticmethod
    def _format_value(attr: str, value) -> str:
        if value is None:
            return "--"
        if attr == "armed":
            return "ARMED" if value else "DISARMED"
        if isinstance(value, float):
            if not math.isfinite(value):
                return "--"
            return f"{value:.6f}" if attr in ("latitude", "longitude") else f"{value:.2f}"
        return str(value)

    def _on_device_combo_changed(self, index: int) -> None:
        if self._updating_devices or index < 0:
            return
        key = self.device_combo.itemData(index)
        if key is not None:
            self.selected_key = tuple(key)
            self.flight_controls.set_active_vehicle(self.selected_key)
            self.mission_panel.set_active_vehicle(self.selected_key)
            self._refresh_selected_telemetry()
        else:
            self.selected_key = None
            self._clear_telemetry()

    # ============================================================
    # COM / TRANSPORT UI
    # ============================================================

    def _on_transport_changed(self, transport: str) -> None:
        is_serial = transport.upper() == "SERIAL"
        self.serial_widget.setVisible(is_serial)
        self.udp_widget.setVisible(not is_serial)

    def _refresh_serial_ports(self) -> None:
        current = self.com_combo.currentText()
        self.com_combo.clear()
        ports = []
        if list_ports is not None:
            try:
                ports = [p.device for p in list_ports.comports()]
            except Exception:
                ports = []
        self.com_combo.addItems(ports)
        if current:
            self.com_combo.setCurrentText(current)

    # ============================================================
    # WINDOW
    # ============================================================

    def closeEvent(self, event) -> None:
        try:
            self.logger.close()
            self.connection_manager.disconnect()
        except Exception:
            pass
        event.accept()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                font-weight: 600;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
            QListWidget {
                min-height: 70px;
            }
            QScrollArea {
                border: none;
            }
            QAbstractSpinBox {
                min-height: 26px;
            }
            QListWidget::item {
                padding: 7px;
            }
            QLabel#selectedTitle {
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#selectedLink, QLabel#lastUpdate, QLabel#workspaceHint {
                color: #6b7280;
            }
            QLabel#telemetrySection {
                font-weight: 700;
                margin-top: 5px;
            }
            QLabel#connectionStatus {
                font-weight: 700;
                padding: 4px;
            }
            QFrame#workspace {
                border: 1px solid #cfd4dc;
                border-radius: 4px;
            }
            QLabel#workspaceTitle {
                font-size: 18px;
                font-weight: 700;
                margin-top: 30px;
            }
            QLabel#workspaceStatus {
                font-weight: 600;
                margin-bottom: 30px;
            }
            """
        )
