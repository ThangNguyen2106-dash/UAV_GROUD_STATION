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


from Rigel_GCS.core.geo_fence import check_airspace


class MissionPanel(QFrame):
    """Waypoint editor and mission planner for UAV autonomous flights with NFZ protection."""

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

        # Controls & Table
        alt_layout = QHBoxLayout()
        alt_layout.addWidget(QLabel("Default Alt (m):"))
        self.spin_default_alt = QDoubleSpinBox()
        self.spin_default_alt.setRange(2.0, 500.0)
        self.spin_default_alt.setValue(25.0)
        self.spin_default_alt.setSingleStep(5.0)
        alt_layout.addWidget(self.spin_default_alt)
        layout.addLayout(alt_layout)

        # Waypoint Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["WP #", "Type", "Lat, Lon", "Alt (m)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("background:#090d14; border:1px solid #1e293b; gridline-color:#1e293b;")
        layout.addWidget(self.table)

        # Button row
        btn_layout = QHBoxLayout()
        self.btn_add_pos = QPushButton("📍 Add Current Pos")
        self.btn_add_pos.clicked.connect(self._add_current_pos_wp)
        btn_layout.addWidget(self.btn_add_pos)

        self.btn_delete_wp = QPushButton("🗑️ Delete WP")
        self.btn_delete_wp.clicked.connect(self._remove_selected_wp)
        btn_layout.addWidget(self.btn_delete_wp)

        self.btn_clear = QPushButton("🧹 Clear All")
        self.btn_clear.clicked.connect(self.clear_mission)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        # Upload / Download Buttons
        transfer_layout = QHBoxLayout()
        self.btn_upload = QPushButton("⬆️ Upload to UAV")
        self.btn_upload.setStyleSheet("background:#0284c7; color:white; font-weight:bold; padding:6px;")
        self.btn_upload.clicked.connect(self._upload_mission)
        transfer_layout.addWidget(self.btn_upload)

        self.btn_download = QPushButton("⬇️ Read from UAV")
        self.btn_download.clicked.connect(self._download_mission)
        transfer_layout.addWidget(self.btn_download)
        layout.addLayout(transfer_layout)

    def set_active_vehicle(self, key: Optional[tuple[str, int, int]]) -> None:
        self.selected_key = key

    def update_telemetry(self, state: Any) -> None:
        self.update_uav_telemetry(state)

    def update_uav_telemetry(self, state: Any) -> None:
        if state is None:
            return
        lat = getattr(state, "latitude", None)
        lon = getattr(state, "longitude", None)
        alt = getattr(state, "relative_altitude", None) or getattr(state, "altitude", None)
        if lat is not None and lon is not None and (float(lat) != 0.0 or float(lon) != 0.0):
            self._current_uav_lat = float(lat)
            self._current_uav_lon = float(lon)
        if alt is not None:
            self._current_uav_alt = max(5.0, float(alt))


    def add_waypoint(self, lat: float, lon: float, alt: Optional[float] = None, cmd: str = "WAYPOINT") -> None:
        """Add a waypoint at given coordinates with airspace checking."""
        res = check_airspace(lat, lon)
        if res.is_inside_prohibited and res.nearest_zone:
            reply = QMessageBox.warning(
                self,
                "⛔ CẢNH BÁO VÙNG CẤM BAY (NFZ)",
                f"Tọa độ ({lat:.6f}, {lon:.6f}) nằm trong VÙNG CẤM BAY của:\n\n"
                f"• {res.nearest_zone.name} ({res.nearest_zone.code})\n"
                f"• Khoảng cách: {res.distance_to_nearest_m:.0f}m (Bán kính cấm: {res.nearest_zone.prohibited_radius_m:.0f}m)\n\n"
                f"Bạn có chắc chắn vẫn muốn thêm điểm này vào kế hoạch bay?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

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
            
            coord_item = QTableWidgetItem(f"{wp['lat']:.6f}, {wp['lon']:.6f}")
            # Highlight if inside NFZ
            res = check_airspace(wp["lat"], wp["lon"])
            if res.is_inside_prohibited:
                coord_item.setForeground(Qt.GlobalColor.red)
                coord_item.setToolTip(f"⛔ Vùng cấm: {res.nearest_zone.name if res.nearest_zone else ''}")
            self.table.setItem(row, 2, coord_item)

            self.table.setItem(row, 3, QTableWidgetItem(f"{wp['alt']:.1f}"))

    def _upload_mission(self) -> None:
        if not self._waypoints:
            QMessageBox.information(self, "Upload Mission", "No waypoints in the mission list.")
            return

        # Pre-upload safety verification: Check for any prohibited NFZ breaches
        for wp in self._waypoints:
            res = check_airspace(wp["lat"], wp["lon"])
            if res.is_inside_prohibited and res.nearest_zone:
                reply = QMessageBox.critical(
                    self,
                    "🚨 VI PHẠM VÙNG CẤM BAY (NFZ VIOLATION)",
                    f"Điểm WP #{wp['index']} ({wp['lat']:.6f}, {wp['lon']:.6f}) vi phạm VÙNG CẤM BAY:\n\n"
                    f"• {res.nearest_zone.name}\n"
                    f"• Bán kính cấm: {res.nearest_zone.prohibited_radius_m:.0f}m\n\n"
                    f"Cảnh báo: Bay vào vùng cấm có thể bị bắn hạ hoặc xử phạt theo quy định quản lý không phận.\n"
                    f"Bạn có muốn hủy bỏ tải lên để sửa đổi tọa độ?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    return
                break

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
