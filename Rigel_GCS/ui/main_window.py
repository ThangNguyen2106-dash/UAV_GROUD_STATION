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
from Rigel_GCS.ui.flight_data.camera_feed import CameraFeedWidget
from Rigel_GCS.ui.flight_data.safety_banner import SafetyBannerWidget
from Rigel_GCS.ui.flight_data.status_console import StatusConsoleWidget
from Rigel_GCS.ui.flight_data.telemetry_cards import TelemetryCardsWidget
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

    Layout Architecture:
        TOPBAR: Brand logo + Navigation Tabs + Inline Link/Connection Controls + Active Drone Selector
        TAB 1 (FLIGHT DATA):
            - LEFT: Real-time 60 FPS HUD + Safety Alert Banner + FPV / Camera Feed Slot
            - CENTER: Tactical Map + Real-time MAVLink Status Console
            - RIGHT: Cockpit Telemetry Cards (Battery, GPS, Dynamics) + Vehicle State & Health
        TAB 2 (MISSION PLANNER):
            - LEFT: Interactive Mission Map (Waypoint click creation)
            - RIGHT: Mission / Waypoint Editor & Waypoint Upload/Download Panel
    """

    POLL_MS = 250
    HUD_POLL_MS = 16

    def __init__(self, connection_manager) -> None:
        super().__init__()
        self.connection_manager = connection_manager
        self.selected_key: Optional[tuple[str, int, int]] = None
        self._updating_devices = False
        self.logger = TelemetryLogger()

        self.setWindowTitle("RIGEL Ground Station - UAV Cockpit")
        self.resize(1440, 880)
        self.setMinimumSize(960, 600)

        self._build_ui()
        self._apply_style()
        self._refresh_serial_ports()

        # Connect live MAVLink message hook (for STATUSTEXT console)
        self.connection_manager.on_message = self._on_mavlink_message_received

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

        # 1. Main Stacked Tabs
        self.main_tabs = QTabWidget()
        self.main_tabs.tabBar().hide()  # Navigation controlled via TopBar buttons
        self.main_tabs.setStyleSheet("QTabWidget::pane { border: 0; background: transparent; }")

        # 2. Sleek Top Bar with Navigation, Connection, and Active Drone
        topbar = self._build_topbar()
        main_layout.addWidget(topbar)
        main_layout.addWidget(self.main_tabs)

        # ========================================================
        # TAB 1: 📊 DATA (FLIGHT DATA & LIVE MONITORING)
        # ========================================================
        tab_data = QWidget()
        data_layout = QHBoxLayout(tab_data)
        data_layout.setContentsMargins(0, 2, 0, 0)
        data_layout.setSpacing(8)

        data_splitter = QSplitter(Qt.Horizontal)
        data_splitter.setChildrenCollapsible(False)

        # Left Sidebar (Vehicle HUD + Safety Banner + Camera Feed)
        sidebar = QWidget()
        sidebar.setMinimumWidth(290)
        sidebar.setMaximumWidth(380)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(8)

        # Primary Flight Display / HUD
        side.addWidget(self._build_hud_box())

        # Safety Alert Banner
        self.safety_banner = SafetyBannerWidget()
        side.addWidget(self.safety_banner)

        # Dedicated FPV / Camera Video Feed Slot
        self.camera_feed = CameraFeedWidget()
        side.addWidget(self.camera_feed)
        side.addStretch(1)

        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_scroll.setWidget(sidebar)
        data_splitter.addWidget(sidebar_scroll)

        # Center/Right of Tab 1: Map + Status Console (Center) and Cockpit Cards + Status (Right)
        data_center_splitter = QSplitter(Qt.Horizontal)
        data_center_splitter.setChildrenCollapsible(False)

        # Center Column: Tactical Map (Top) + MAVLink Status Console (Bottom)
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)

        self.data_map = MapWidget(enable_waypoint_click=False)
        center_layout.addWidget(self.data_map, 1)

        self.status_console = StatusConsoleWidget()
        center_layout.addWidget(self.status_console)

        data_center_splitter.addWidget(center_container)

        # Right Column: Cockpit Telemetry Cards (Top) + Vehicle Safety Status Panel (Bottom)
        right_sidebar = QWidget()
        right_sidebar.setMinimumWidth(290)
        right_sidebar.setMaximumWidth(360)
        right_layout = QVBoxLayout(right_sidebar)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.telemetry_cards = TelemetryCardsWidget()
        right_layout.addWidget(self.telemetry_cards)

        self.flight_controls = FlightControlPanel(self.connection_manager)
        right_layout.addWidget(self.flight_controls)
        right_layout.addStretch(1)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setWidget(right_sidebar)

        data_center_splitter.addWidget(right_scroll)
        data_center_splitter.setSizes([850, 310])

        data_splitter.addWidget(data_center_splitter)
        data_splitter.setSizes([320, 1120])
        data_layout.addWidget(data_splitter)

        self.main_tabs.addTab(tab_data, "FLIGHT DATA")

        # ========================================================
        # TAB 2: 📍 MISSION (MISSION PLANNER & WAYPOINT EDITOR)
        # ========================================================
        tab_mission = QWidget()
        mission_layout = QHBoxLayout(tab_mission)
        mission_layout.setContentsMargins(0, 2, 0, 0)
        mission_layout.setSpacing(8)

        mission_splitter = QSplitter(Qt.Horizontal)
        mission_splitter.setChildrenCollapsible(False)

        # Mission Map (Interactive waypoint click mode: enable_waypoint_click=True)
        self.mission_map = MapWidget(enable_waypoint_click=True)
        mission_splitter.addWidget(self.mission_map)

        # Mission Planner Panel (Right side of Mission tab)
        self.mission_panel = MissionPanel(self.connection_manager)
        self.mission_panel.setMinimumWidth(360)
        self.mission_panel.setMaximumWidth(480)
        mission_splitter.addWidget(self.mission_panel)
        mission_splitter.setSizes([960, 440])

        mission_layout.addWidget(mission_splitter)
        self.main_tabs.addTab(tab_mission, "📍 MISSION (PLANNER)")

        # Connect Waypoint signals:
        # 1. Clicking on Mission Map adds a Waypoint in Mission Panel
        self.mission_map.waypoint_clicked.connect(self.mission_panel.add_waypoint)

        # 2. When waypoints change in Mission Panel: sync to BOTH Mission Map and Data Map!
        self.mission_panel.waypoints_changed.connect(self.mission_map.update_waypoints_display)
        self.mission_panel.waypoints_changed.connect(self.data_map.update_waypoints_display)

        self.workspace_status = QLabel("Ready")

    def _build_topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setStyleSheet("""
            QFrame#topBar {
                background: #0b1329;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 2px 4px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        # 1. Logo / Title
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(6)
        logo_icon = QLabel("🚀")
        logo_icon.setFont(QFont("Segoe UI", 12))
        brand_title = QLabel("RIGEL GCS")
        brand_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        brand_title.setStyleSheet("color: #38bdf8; letter-spacing: 1px;")
        brand_layout.addWidget(logo_icon)
        brand_layout.addWidget(brand_title)
        layout.addLayout(brand_layout)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color: #334155;")
        layout.addWidget(sep1)

        # 2. Main Tab Switcher Buttons
        self.btn_tab_data = QPushButton("📊 FLIGHT DATA")
        self.btn_tab_mission = QPushButton("📍 MISSION PLANNER")
        for btn in (self.btn_tab_data, self.btn_tab_mission):
            btn.setFixedHeight(28)
            btn.setCursor(Qt.PointingHandCursor)

        self.btn_tab_data.clicked.connect(lambda: self._switch_main_tab(0))
        self.btn_tab_mission.clicked.connect(lambda: self._switch_main_tab(1))

        tab_btn_layout = QHBoxLayout()
        tab_btn_layout.setSpacing(4)
        tab_btn_layout.addWidget(self.btn_tab_data)
        tab_btn_layout.addWidget(self.btn_tab_mission)
        layout.addLayout(tab_btn_layout)

        layout.addStretch(1)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: #334155;")
        layout.addWidget(sep2)

        # 3. Inline Connection Controls
        link_container = QWidget()
        link_layout = QHBoxLayout(link_container)
        link_layout.setContentsMargins(0, 0, 0, 0)
        link_layout.setSpacing(6)

        link_lbl = QLabel("LINK:")
        link_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        link_lbl.setStyleSheet("color: #64748b;")
        link_layout.addWidget(link_lbl)

        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["UDP", "SERIAL"])
        self.transport_combo.setFixedHeight(26)
        self.transport_combo.currentTextChanged.connect(self._on_transport_changed)
        link_layout.addWidget(self.transport_combo)

        # UDP parameters widget
        self.udp_widget = QWidget()
        udp_l = QHBoxLayout(self.udp_widget)
        udp_l.setContentsMargins(0, 0, 0, 0)
        udp_l.setSpacing(4)

        lbl_rx = QLabel("RX:")
        lbl_rx.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.udp_rx_port = NoWheelSpinBox()
        self.udp_rx_port.setRange(1, 65535)
        self.udp_rx_port.setValue(14550)
        self.udp_rx_port.setFixedHeight(26)
        self.udp_rx_port.setToolTip("GCS Listening (RX) Port")
        self.udp_rx_host = QLineEdit("0.0.0.0")

        lbl_tx = QLabel("TX:")
        lbl_tx.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.udp_tx_host = QLineEdit("127.0.0.1")
        self.udp_tx_host.setFixedWidth(85)
        self.udp_tx_host.setFixedHeight(26)
        self.udp_tx_host.setToolTip("Target Drone TX Host")

        self.udp_tx_port = NoWheelSpinBox()
        self.udp_tx_port.setRange(1, 65535)
        self.udp_tx_port.setValue(14551)
        self.udp_tx_port.setFixedHeight(26)
        self.udp_tx_port.setToolTip("Target Drone TX Port")

        udp_l.addWidget(lbl_rx)
        udp_l.addWidget(self.udp_rx_port)
        udp_l.addWidget(lbl_tx)
        udp_l.addWidget(self.udp_tx_host)
        udp_l.addWidget(self.udp_tx_port)
        link_layout.addWidget(self.udp_widget)

        # Serial parameters widget
        self.serial_widget = QWidget()
        ser_l = QHBoxLayout(self.serial_widget)
        ser_l.setContentsMargins(0, 0, 0, 0)
        ser_l.setSpacing(4)

        self.com_combo = QComboBox()
        self.com_combo.setEditable(True)
        self.com_combo.setFixedWidth(85)
        self.com_combo.setFixedHeight(26)

        self.refresh_com_button = QPushButton("🔄")
        self.refresh_com_button.setFixedSize(26, 26)
        self.refresh_com_button.setToolTip("Refresh COM Ports")
        self.refresh_com_button.clicked.connect(self._refresh_serial_ports)

        self.baud_spin = NoWheelSpinBox()
        self.baud_spin.setRange(1200, 2000000)
        self.baud_spin.setValue(115200)
        self.baud_spin.setFixedHeight(26)
        self.baud_spin.setToolTip("Baudrate")

        ser_l.addWidget(self.com_combo)
        ser_l.addWidget(self.refresh_com_button)
        ser_l.addWidget(self.baud_spin)
        link_layout.addWidget(self.serial_widget)
        self.serial_widget.hide()

        # Connect / Disconnect Buttons
        self.connect_button = QPushButton("⚡ Connect")
        self.connect_button.setFixedHeight(26)
        self.connect_button.setStyleSheet("""
            QPushButton {
                background: #059669;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background: #10b981;
            }
        """)
        self.connect_button.clicked.connect(self._connect)
        link_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setFixedHeight(26)
        self.disconnect_button.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #cbd5e1;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: #ef4444;
                color: white;
                border-color: #ef4444;
            }
        """)
        self.disconnect_button.clicked.connect(self._disconnect)
        link_layout.addWidget(self.disconnect_button)

        self.connection_status = QLabel("● DISCONNECTED")
        self.connection_status.setObjectName("connectionStatus")
        self.connection_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.connection_status.setStyleSheet("color: #ef4444; padding: 0 4px;")
        link_layout.addWidget(self.connection_status)

        layout.addWidget(link_container)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("color: #334155;")
        layout.addWidget(sep3)

        # 4. Active Drone Selector
        drone_container = QWidget()
        d_layout = QHBoxLayout(drone_container)
        d_layout.setContentsMargins(0, 0, 0, 0)
        d_layout.setSpacing(4)

        d_lbl = QLabel("🛸 DRONE:")
        d_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        d_lbl.setStyleSheet("color: #64748b;")
        d_layout.addWidget(d_lbl)

        self.device_combo = QComboBox()
        self.device_combo.setFixedHeight(26)
        self.device_combo.setMinimumWidth(125)
        self.device_combo.addItem("No drone detected", None)
        self.device_combo.currentIndexChanged.connect(self._on_device_combo_changed)
        d_layout.addWidget(self.device_combo)

        layout.addWidget(drone_container)

        self._switch_main_tab(0)
        return bar

    def _switch_main_tab(self, index: int) -> None:
        self.main_tabs.setCurrentIndex(index)
        if index == 0:
            self.btn_tab_data.setStyleSheet("""
                QPushButton {
                    background: #0284c7;
                    color: white;
                    font-weight: bold;
                    border: 1px solid #38bdf8;
                    border-radius: 4px;
                    padding: 0 14px;
                }
            """)
            self.btn_tab_mission.setStyleSheet("""
                QPushButton {
                    background: #1e293b;
                    color: #94a3b8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 0 14px;
                }
                QPushButton:hover {
                    background: #334155;
                    color: #e2e8f0;
                }
            """)
        else:
            self.btn_tab_data.setStyleSheet("""
                QPushButton {
                    background: #1e293b;
                    color: #94a3b8;
                    border: 1px solid #334155;
                    border-radius: 4px;
                    padding: 0 14px;
                }
                QPushButton:hover {
                    background: #334155;
                    color: #e2e8f0;
                }
            """)
            self.btn_tab_mission.setStyleSheet("""
                QPushButton {
                    background: #0284c7;
                    color: white;
                    font-weight: bold;
                    border: 1px solid #38bdf8;
                    border-radius: 4px;
                    padding: 0 14px;
                }
            """)

    def _build_hud_box(self) -> QGroupBox:
        box = QGroupBox("PRIMARY FLIGHT DISPLAY (HUD)")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.hud = VehiclePanel()
        self.hud.setMinimumWidth(250)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.hud)
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
        self.telemetry_cards.update_telemetry(state)
        self.safety_banner.update_state(state)
        self.mission_panel.update_telemetry(state)
        self.logger.log_state(state)

    def _refresh_runtime(self) -> None:
        self._refresh_connection_status()
        self._refresh_devices()

    def _refresh_connection_status(self) -> None:
        raw_state = getattr(self.connection_manager.state, "value", str(self.connection_manager.state))
        state_str = str(raw_state).upper()
        if "CONNECTED" in state_str and "DIS" not in state_str:
            self.connection_status.setText(f"● {state_str}")
            self.connection_status.setStyleSheet("color: #10b981; font-weight: bold;")
        elif "CONNECTING" in state_str or "LISTEN" in state_str:
            self.connection_status.setText(f"● {state_str}")
            self.connection_status.setStyleSheet("color: #f59e0b; font-weight: bold;")
        else:
            self.connection_status.setText(f"● {state_str}")
            self.connection_status.setStyleSheet("color: #ef4444; font-weight: bold;")

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
        if state is None:
            return

        self.hud.update_telemetry(state)
        self.flight_controls.set_active_vehicle(self.selected_key)
        self.mission_panel.set_active_vehicle(self.selected_key)
        self.flight_controls.update_telemetry(state)
        self.telemetry_cards.update_telemetry(state)
        self.safety_banner.update_state(state)
        self.mission_panel.update_telemetry(state)
        self.data_map.update_uav_telemetry(state)
        self.mission_map.update_uav_telemetry(state)

    def _on_mavlink_message_received(self, message, device=None) -> None:
        try:
            msg_type = message.get_type()
            if msg_type == "STATUSTEXT":
                text = getattr(message, "text", "")
                if isinstance(text, bytes):
                    text = text.decode("utf-8", errors="ignore")
                elif not isinstance(text, str):
                    text = str(text)
                severity = getattr(message, "severity", 6)
                self.status_console.add_message(text, severity)
        except Exception:
            pass

    def _clear_telemetry(self) -> None:
        self.flight_controls.set_active_vehicle(None)
        self.mission_panel.set_active_vehicle(None)
        self.telemetry_cards.update_telemetry(None)
        self.safety_banner.update_state(None)

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
            QMainWindow {
                background: #020617;
                color: #e2e8f0;
                font-family: Segoe UI, -apple-system, sans-serif;
                font-size: 12px;
            }
            QWidget {
                color: #e2e8f0;
                font-family: Segoe UI, -apple-system, sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                background: #090e1f;
                border: 1px solid #1e293b;
                border-radius: 6px;
                font-weight: 700;
                font-size: 11px;
                color: #38bdf8;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                background: #090e1f;
            }
            QComboBox, QSpinBox, QLineEdit {
                background: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 2px 6px;
                selection-background-color: #0284c7;
            }
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
                border-color: #0284c7;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox QAbstractItemView {
                background: #0f172a;
                color: #f1f5f9;
                border: 1px solid #334155;
                selection-background-color: #0284c7;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: #090e1f;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #334155;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #0284c7;
            }
            """
        )
