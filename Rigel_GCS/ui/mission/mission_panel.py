from __future__ import annotations

from typing import Any, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class MissionPanel(QFrame):
    """Waypoint editor and mission planner for UAV autonomous flights."""

    waypoints_changed = Signal(list)  # Emits list of waypoint dicts: [{'lat', 'lon', 'alt', 'index', 'cmd'}]

    def __init__(self, connection_manager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.connection_manager = connection_manager
        self.selected_key: Optional[tuple[str, int, int]] = None

        self._waypoints: List[dict] = []
        self._current_uav_lat = 21.028511
        self._current_uav_lon = 105.804817
        self._current_uav_alt = 20.0

        self.setObjectName("MissionPanel")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        title = QLabel("MISSION & WAYPOINT PLANNER")
        title.setStyleSheet("font-weight:bold; color:#38bdf8; font-size:12px;")
        layout.addWidget(title)

        # Default Alt Selector
        alt_row = QHBoxLayout()
        alt_row.addWidget(QLabel("Default Alt (m):"))
        self.spin_default_alt = QDoubleSpinBox()
        self.spin_default_alt.setRange(2.0, 500.0)
        self.spin_default_alt.setValue(25.0)
        alt_row.addWidget(self.spin_default_alt)
        alt_row.addStretch(1)
        layout.addLayout(alt_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["WP #", "Command", "Lat / Lon", "Alt (m)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # Action Button Row 1 (Add/Remove)
        btn_row1 = QHBoxLayout()
        self.btn_add = QPushButton("➕ Add WP")
        self.btn_add.clicked.connect(self._add_current_pos_wp)
        btn_row1.addWidget(self.btn_add)

        self.btn_remove = QPushButton("➖ Remove")
        self.btn_remove.clicked.connect(self._remove_selected_wp)
        btn_row1.addWidget(self.btn_remove)

        self.btn_clear = QPushButton("🧹 Clear All")
        self.btn_clear.clicked.connect(self.clear_mission)
        btn_row1.addWidget(self.btn_clear)
        layout.addLayout(btn_row1)

        # Action Button Row 2 (Upload/Download)
        btn_row2 = QHBoxLayout()
        self.btn_upload = QPushButton("📤 Upload to UAV")
        self.btn_upload.setStyleSheet("background:#0284c7; color:white; font-weight:bold; height:28px;")
        self.btn_upload.clicked.connect(self._upload_mission)
        btn_row2.addWidget(self.btn_upload)

        self.btn_download = QPushButton("📥 Download from UAV")
        self.btn_download.setStyleSheet("background:#059669; color:white; font-weight:bold; height:28px;")
        self.btn_download.clicked.connect(self._download_mission)
        btn_row2.addWidget(self.btn_download)
        layout.addLayout(btn_row2)

    def set_active_vehicle(self, key: Optional[tuple[str, int, int]]) -> None:
        self.selected_key = key

    def update_telemetry(self, state: Any) -> None:
        lat = getattr(state, "latitude", None)
        lon = getattr(state, "longitude", None)
        alt = getattr(state, "altitude", None) or getattr(state, "relative_altitude", None)

        if lat is not None and lon is not None and lat != 0.0:
            self._current_uav_lat = float(lat)
            self._current_uav_lon = float(lon)
        if alt is not None:
            self._current_uav_alt = max(5.0, float(alt))

    def add_waypoint(self, lat: float, lon: float, alt: Optional[float] = None, cmd: str = "WAYPOINT") -> None:
        """Add a waypoint at given coordinates."""
        altitude = alt if alt is not None else self.spin_default_alt.value()
        wp = {
            "index": len(self._waypoints) + 1,
            "cmd": cmd,
            "lat": float(lat),
            "lon": float(lon),
            "alt": float(altitude),
        }
        self._waypoints.append(wp)
        self._refresh_table()
        self.waypoints_changed.emit(self._waypoints)

    def clear_mission(self) -> None:
        """Clear all waypoints."""
        self._waypoints.clear()
        self._refresh_table()
        self.waypoints_changed.emit(self._waypoints)

    def _add_current_pos_wp(self) -> None:
        self.add_waypoint(self._current_uav_lat, self._current_uav_lon, self.spin_default_alt.value())

    def _remove_selected_wp(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._waypoints):
            self._waypoints.pop(row)
            # Re-index
            for i, wp in enumerate(self._waypoints):
                wp["index"] = i + 1
            self._refresh_table()
            self.waypoints_changed.emit(self._waypoints)

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self._waypoints))
        for row, wp in enumerate(self._waypoints):
            self.table.setItem(row, 0, QTableWidgetItem(f"WP {wp['index']}"))
            self.table.setItem(row, 1, QTableWidgetItem(wp["cmd"]))
            self.table.setItem(row, 2, QTableWidgetItem(f"{wp['lat']:.6f}, {wp['lon']:.6f}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{wp['alt']:.1f}"))

    def _upload_mission(self) -> None:
        if not self._waypoints:
            QMessageBox.information(self, "Upload Mission", "No waypoints in the mission list.")
            return

        sysid, compid = 1, 1
        transport = None
        if self.selected_key:
            transport, sysid, compid = self.selected_key

        # Send MISSION_COUNT (Message ID 44)
        try:
            # Using command long or mission protocol
            print(f"[MISSION] Uploading {len(self._waypoints)} waypoints to SYSID={sysid}...")
            # Send MAVLink mission count
            with self.connection_manager._lock:
                links = list(self.connection_manager._links.values())

            if not links:
                QMessageBox.warning(self, "Upload Error", "No active vehicle connection.")
                return

            link = links[0]
            count_msg = link.session._parser.mission_count_encode(
                int(sysid),
                int(compid),
                len(self._waypoints),
            )
            link.session.send_message(count_msg)

            # Send each waypoint item
            for i, wp in enumerate(self._waypoints):
                item_msg = link.session._parser.mission_item_int_encode(
                    int(sysid),
                    int(compid),
                    int(i),
                    0,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                    16,  # MAV_CMD_NAV_WAYPOINT
                    1 if i == 0 else 0,  # current
                    1,  # autocontinue
                    0.0, 0.0, 0.0, 0.0,  # params 1-4
                    int(wp["lat"] * 1e7),
                    int(wp["lon"] * 1e7),
                    float(wp["alt"]),
                )
                link.session.send_message(item_msg)

            QMessageBox.information(
                self,
                "Mission Upload",
                f"Successfully transmitted {len(self._waypoints)} waypoints to Drone ID {sysid}!",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Upload Mission Error", str(exc))

    def _download_mission(self) -> None:
        sysid, compid = 1, 1
        if self.selected_key:
            _, sysid, compid = self.selected_key

        try:
            with self.connection_manager._lock:
                links = list(self.connection_manager._links.values())

            if not links:
                QMessageBox.warning(self, "Download Error", "No active vehicle connection.")
                return

            link = links[0]
            req_msg = link.session._parser.mission_request_list_encode(
                int(sysid),
                int(compid),
            )
            link.session.send_message(req_msg)
            print(f"[MISSION] Requested mission list from SYSID={sysid}")
            QMessageBox.information(
                self,
                "Mission Request",
                f"Requested mission from Drone ID {sysid}. Receiving waypoints...",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Download Mission Error", str(exc))
