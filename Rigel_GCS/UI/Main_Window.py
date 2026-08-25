import tkinter as tk
from tkinter import messagebox
import math

from .Styles import Colors, setup_styles
from .Header import Header
from .Flight_HUD import FlightHUD
from .Map_Container import MapContainer
from .Waypoint_Panel import WaypointPanel
from .Command_Panel import CommandPanel
from .Telemetry_Panel import TelemetryPanel
from .Video_Panel import VideoPanel
from .Log_Panel import LogPanel

from Rigel_GCS.Telemetry.Telemetry_Data import TelemetryData


class MainWindow:
    """
    RIGEL UI layer.

    Nguyên tắc:
        UI = hiển thị + tương tác người dùng.

    UI KHÔNG chứa:
        - Map engine
        - Map provider
        - GPS conversion
        - MAVLink
        - Telemetry receiver
        - Flight controller
        - Camera processing
        - AI processing
        - Module hardware

    Các thành phần bên ngoài sẽ kết nối qua callback / mount.
    """

    def __init__(self, root):
        self.root = root

        self.root.title(
            "RIGEL Ground Control Station v1.0 - "
            "[Trạm Điều Khiển Bay Mặt Đất]"
        )
        self.root.geometry("1440x820")
        self.root.minsize(1100, 700)
        self.root.configure(bg=Colors.BG)

        setup_styles(root)

        # UI state only.
        self.flight_mode = "DISARMED"
        self.is_armed = False

        # Demo display data only.
        self.demo_alt = 0.0
        self.demo_speed = 0.0
        self.demo_heading = 120.0
        self.demo_pitch = 0.0
        self.demo_roll = 0.0

        # Mission/photo automation state.
        self._reached_waypoints = set()
        self.waypoint_arrival_radius_m = 5.0
        self.last_drone_lat = None
        self.last_drone_lon = None

        self._build_header()
        self._build_layout()
        self._bind_events()

        # Real telemetry module is mounted by main.py.
        self.telemetry_manager = None
        self._telemetry_last_error = None

        self.log("RIGEL GCS UI initialized.")
        self.log("MAP INTERFACE: waiting for external module.")
        self.log("VIDEO MODULE: waiting for external module.")
        self.log("TELEMETRY: waiting for external source.")

        # Chỉ để test UI.
        self._demo_loop()

    # ============================================================
    # BUILD UI
    # ============================================================

    def _build_header(self):
        self.header = Header(self.root)

    def _build_layout(self):
        root_container = tk.Frame(self.root, bg=Colors.BG)
        root_container.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        # --------------------------------------------------------
        # LEFT
        # --------------------------------------------------------
        left = tk.Frame(
            root_container,
            bg=Colors.CARD,
            width=285,
            bd=1,
            relief="solid",
        )
        left.pack(side="left", fill="y", padx=(4, 3))
        left.pack_propagate(False)

        self.hud = FlightHUD(left)
        self.hud.frame.pack(fill="x")

        # Camera cố định ngay dưới trạng thái drone (Flight HUD).
        self.video_panel = VideoPanel(
            left,
            on_camera_change=self._on_camera_change,
        )

        self.telemetry_panel = TelemetryPanel(
            left,
            on_refresh_ports=self.refresh_telemetry_ports,
            on_connect=self.connect_telemetry,
            on_disconnect=self.disconnect_telemetry,
        )

        # --------------------------------------------------------
        # CENTER
        # --------------------------------------------------------
        center = tk.Frame(
            root_container,
            bg=Colors.CARD,
            bd=1,
            relief="solid",
        )
        center.pack(side="left", fill="both", expand=True, padx=4)

        self.map_container = MapContainer(center)
        self.map_container.frame.pack(fill="both", expand=True)

        # --------------------------------------------------------
        # RIGHT
        # --------------------------------------------------------
        right = tk.Frame(
            root_container,
            bg=Colors.CARD,
            width=255,
            bd=1,
            relief="solid",
        )
        right.pack(side="right", fill="y", padx=(3, 4))
        right.pack_propagate(False)

        self.waypoint_panel = WaypointPanel(
            right,
            on_delete=self._on_delete_waypoint,
            on_clear=self._on_clear_waypoints,
            on_select=self._on_select_waypoint,
            on_toggle_mode=self._toggle_waypoint_mode,
        )
        self.waypoint_panel.frame.pack(fill="x")

        self.command_panel = CommandPanel(
            right,
            on_command=self._on_command,
        )
        self.command_panel.frame.pack(fill="x")

        self.log_panel = LogPanel(right)
        self.log_panel.frame.pack(fill="both", expand=True)

    def _bind_events(self):
        self.root.bind(
            "<Delete>",
            self._on_delete_key,
        )

    def _on_delete_key(self, _event=None):
        """Delete key only edits the mission in SETUP mode."""
        if hasattr(self, "map_widget") and self.map_widget.is_waypoint_mode_enabled():
            self._on_delete_waypoint()
        return "break"

    # ============================================================
    # EXTERNAL MODULE MOUNTING
    # ============================================================

    def mount_map_interface(self, widget):
        """
        MAP_INTERFACE gọi hàm này để nhúng bản đồ vào UI.
        """
        self.map_widget = widget
        self.map_widget.set_waypoint_update_callback(self._on_waypoint_moved)
        self.map_widget.set_waypoint_edit_callback(self._can_edit_waypoint)
        self.map_widget.set_home_callback(self._on_home_changed)
        self.map_container.mount(widget)
        self.map_container.set_provider_status(
            "MAP INTERFACE: CONNECTED"
        )
        self.waypoint_panel.set_home_status(self.map_widget.get_home_point())
        self.log("MAP INTERFACE mounted.")

    def mount_video_module(self, widget):
        """
        Camera/Video module gọi hàm này để nhúng video.
        """
        self.video_panel.mount(widget)
        self.video_panel.set_status("VIDEO: CONNECTED")
        self.log("VIDEO MODULE mounted.")

    def mount_telemetry_module(self, manager):
        """Mount the real telemetry manager and start with a port scan."""
        self.telemetry_manager = manager
        self.refresh_telemetry_ports()
        self.log("TELEMETRY MODULE mounted.")

    def refresh_telemetry_ports(self):
        if self.telemetry_manager is None:
            return

        try:
            ports = self.telemetry_manager.port_names()
            self.telemetry_panel.set_ports(ports)
            self.log(
                "TELEMETRY: COM ports -> " +
                (", ".join(ports) if ports else "none")
            )
        except Exception as exc:
            self.log(f"TELEMETRY: port scan error: {exc}")

    def connect_telemetry(self, port, baudrate):
        if self.telemetry_manager is None:
            self.log("TELEMETRY: module chưa được mount.")
            return False

        ok = self.telemetry_manager.connect(port, baudrate)
        if not ok:
            return False

        self.telemetry_panel.set_connection_status(
            True,
            f"CONNECTED {port}",
        )
        self.set_telemetry_status(True)
        self.set_gcs_status("TELEMETRY CONNECTED")
        self.log(f"TELEMETRY: connected {port} @ {baudrate}")
        return True

    def disconnect_telemetry(self):
        if self.telemetry_manager is not None:
            self.telemetry_manager.disconnect()

        self.telemetry_panel.set_connection_status(False, "DISCONNECTED")
        self.set_telemetry_status(False)
        self.set_gcs_status("TELEMETRY OFFLINE")
        self.log("TELEMETRY: disconnected.")

    def _on_telemetry_data(self, data: TelemetryData):
        """UI-thread callback for normalized telemetry."""
        if data.latitude is not None and data.longitude is not None:
            self.update_drone_position(
                data.latitude,
                data.longitude,
            )

            if hasattr(self, "map_manager"):
                self.map_manager.update_uav(
                    data.latitude,
                    data.longitude,
                    data.relative_altitude_m or data.altitude_m or 0.0,
                    data.heading_deg or 0.0,
                )

        self.update_flight_state(
            altitude=data.relative_altitude_m
            if data.relative_altitude_m is not None
            else data.altitude_m,
            speed=data.ground_speed_mps,
            heading=data.heading_deg,
            pitch=data.pitch_deg,
            roll=data.roll_deg,
        )

        self.update_system_state(
            battery_pct=data.battery_remaining_pct,
            voltage=data.battery_voltage_v,
            satellites=data.satellites,
            fix_type=data.fix_type,
            signal_dbm=data.radio_rssi,
        )

        if data.armed is not None:
            self.is_armed = data.armed
            self.command_panel.set_armed(data.armed)

        if data.flight_mode:
            self.flight_mode = data.flight_mode
            self.header.set_mode(data.flight_mode)

        self.telemetry_panel.set_connection_status(
            True,
            f"DATA {data.last_message or ''}".strip(),
        )

    # ============================================================
    # UI CALLBACKS
    # ============================================================

    def _on_camera_change(self, camera_index):
        self.log(f"CAMERA UI: chọn Camera {camera_index}")

    def _on_command(self, command):
        """
        Hiện tại chỉ mô phỏng UI state.
        Sau này thay callback này bằng Controller.
        """
        if command == "ARM":
            if not self.is_armed:
                self.is_armed = True
                self.flight_mode = "ARMED"
                self.command_panel.set_armed(True)
                self.header.set_mode(self.flight_mode)
                self.log("COMMAND UI: ARM")
            else:
                if self.demo_alt > 1:
                    messagebox.showwarning(
                        "Safety",
                        "Không thể DISARM khi UAV đang ở trên không.",
                    )
                    return

                self.is_armed = False
                self.flight_mode = "DISARMED"
                self.command_panel.set_armed(False)
                self.header.set_mode(self.flight_mode)
                self.log("COMMAND UI: DISARM")

        elif command == "TAKEOFF":
            if not self.is_armed:
                messagebox.showwarning(
                    "Safety",
                    "UAV chưa ARM.",
                )
                return

            self.flight_mode = "TAKEOFF"
            self.header.set_mode(self.flight_mode)
            self.log("COMMAND UI: TAKEOFF")

        elif command == "RTL":
            if not self.is_armed:
                return

            self.flight_mode = "RTL"
            self.header.set_mode(self.flight_mode)
            self.log("COMMAND UI: RTL")

        elif command == "LAND":
            if not self.is_armed:
                return

            self.flight_mode = "LAND"
            self.header.set_mode(self.flight_mode)
            self.log("COMMAND UI: LAND")

        elif command == "PAUSE":
            if not self.is_armed:
                return

            self.flight_mode = "PAUSE"
            self.header.set_mode(self.flight_mode)
            self.log("COMMAND UI: PAUSE")

    def _on_home_changed(self, home):
        """Reflect the HOME point (placed/moved on the map) in the panel."""
        self.waypoint_panel.set_home_status(home)
        if home is not None:
            self.log(
                f"HOME: đặt tại {home['lat']:.6f}, {home['lon']:.6f}"
            )

    def _on_waypoint_moved(self, waypoint):
        """Refresh the waypoint table after a map drag."""
        self._reached_waypoints.discard(int(waypoint.get("index", 0)))
        self.update_waypoints(self.map_widget.get_waypoints())
        self.log(
            f"WAYPOINT: WP{waypoint.get('index')} moved to "
            f"{float(waypoint.get('lat', 0)):.6f}, "
            f"{float(waypoint.get('lon', 0)):.6f}"
        )

    def _can_edit_waypoint(self, index):
        """Safety gate: dragging a waypoint is only allowed in SETUP mode."""
        if not hasattr(self, "map_widget"):
            return False
        return self.map_widget.is_waypoint_mode_enabled()

    def _on_delete_waypoint(self):
        # Không cho sửa mission ngoài chế độ thiết lập.
        if not hasattr(self, "map_widget") or not self.map_widget.is_waypoint_mode_enabled():
            self.log("WAYPOINT: đang ở chế độ chỉ xem — hãy bật THIẾT LẬP đường bay để chỉnh sửa.")
            return

        if hasattr(self, "map_widget"):
            selected = self.waypoint_panel.tree.selection()
            if selected:
                index = self.waypoint_panel.tree.index(selected[0]) + 1
                if self.map_widget.remove_waypoint(index):
                    self._reached_waypoints.clear()
                    self.update_waypoints(self.map_widget.get_waypoints())
                    self.log(f"WAYPOINT: deleted WP{index}")
                    return
        self.log("WAYPOINT: no waypoint selected.")

    def _on_clear_waypoints(self):
        # Không cho sửa/xóa mission ngoài chế độ thiết lập.
        if not hasattr(self, "map_widget") or not self.map_widget.is_waypoint_mode_enabled():
            self.log("WAYPOINT: không thể xóa khi chưa vào chế độ THIẾT LẬP.")
            return

        if hasattr(self, "map_widget"):
            self.map_widget.clear_waypoints()
            self._reached_waypoints.clear()
            self.update_waypoints([])
        self.log("WAYPOINT: all waypoints cleared.")

    def _on_select_waypoint(self, index):
        self.log(
            f"UI: chọn waypoint index={index}."
        )

    def _toggle_waypoint_mode(self):
        """Toggle map click-to-add-waypoint mode."""
        if not hasattr(self, "map_widget"):
            self.log("WAYPOINT: map chưa được khởi tạo.")
            return False

        enabled = self.map_widget.toggle_waypoint_mode()
        self.waypoint_panel.set_waypoint_mode(enabled)

        if enabled:
            self.log("WAYPOINT: ON — Click trực tiếp lên bản đồ để chấm WP.")
        else:
            self.log("WAYPOINT: OFF — đã dừng chấm waypoint.")

        return enabled

    # ============================================================
    # CAMERA / MISSION PHOTO API
    # ============================================================

    def capture_camera_photo(self, filename=None):
        """Public API for a manual camera capture."""
        path = self.video_panel.capture_photo(filename=filename)
        if path:
            self.log(f"CAMERA: photo saved -> {path}")
        return path

    def update_drone_position(self, latitude, longitude):
        """Feed live UAV GPS position into the mission/photo system.

        When Auto WP is enabled, reaching each waypoint within
        ``waypoint_arrival_radius_m`` triggers exactly one photo.
        This is intentionally an input API so real MAVLink telemetry
        can call it later without changing the UI.
        """
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            return False

        self.last_drone_lat = lat
        self.last_drone_lon = lon

        if not hasattr(self, "map_widget"):
            return False

        if not self.video_panel.is_auto_capture_enabled():
            return False

        waypoints = self.map_widget.get_waypoints()
        if not waypoints:
            return False

        for position, wp in enumerate(waypoints, start=1):
            wp_index = int(wp.get("index", position))
            if wp_index in self._reached_waypoints:
                continue

            distance = self._distance_m(
                lat, lon,
                float(wp["lat"]), float(wp["lon"]),
            )

            if distance <= self.waypoint_arrival_radius_m:
                self._reached_waypoints.add(wp_index)
                filename = f"WP{wp_index}_{self._timestamp_for_filename()}"
                path = self.video_panel.capture_photo(filename=filename)
                if path:
                    self.log(
                        f"AUTO PHOTO: WP{wp_index} reached ({distance:.1f} m) -> {path}"
                    )
                else:
                    self.log(f"AUTO PHOTO: WP{wp_index} reached but camera capture failed.")
                return bool(path)

        return False

    @staticmethod
    def _timestamp_for_filename():
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    @staticmethod
    def _distance_m(lat1, lon1, lat2, lon2):
        """Haversine distance in meters."""
        radius = 6371000.0
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # ============================================================
    # DATA INPUT API
    # ============================================================

    def update_flight_state(
        self,
        altitude=None,
        speed=None,
        heading=None,
        pitch=None,
        roll=None,
    ):
        """
        API để Controller/Telemetry cập nhật dữ liệu hiển thị.
        """
        if altitude is not None:
            self.demo_alt = altitude
        if speed is not None:
            self.demo_speed = speed
        if heading is not None:
            self.demo_heading = heading
        if pitch is not None:
            self.demo_pitch = pitch
        if roll is not None:
            self.demo_roll = roll

        self.hud.update(
            self.demo_alt,
            self.demo_speed,
            self.demo_heading,
            self.demo_pitch,
            self.demo_roll,
        )

    def update_system_state(
        self,
        battery_pct=None,
        voltage=None,
        satellites=None,
        fix_type=None,
        signal_pct=None,
        signal_dbm=None,
    ):
        """
        API để Telemetry/Controller cập nhật panel hệ thống.
        """
        self.telemetry_panel.update(
            battery_pct=battery_pct,
            voltage=voltage,
            satellites=satellites,
            fix_type=fix_type,
            signal_pct=signal_pct,
            signal_dbm=signal_dbm,
        )

    def update_waypoints(self, waypoints, selected_index=None):
        """
        API để MAP_INTERFACE cập nhật danh sách waypoint cho UI.
        """
        self.waypoint_panel.set_waypoints(
            waypoints,
            selected_index,
        )

    def set_telemetry_status(self, online):
        self.header.set_telemetry(online)

    def set_gcs_status(self, status):
        self.header.set_gcs_status(status)

    # ============================================================
    # LOG
    # ============================================================

    def log(self, message):
        if hasattr(self, "log_panel"):
            self.log_panel.write(message)

    # ============================================================
    # DEMO UI ONLY
    # ============================================================

    def _demo_loop(self):
        """
        Demo để chạy UI độc lập.

        Có thể xóa hàm này khi Controller + Telemetry thật
        được kết nối.
        """
        if self.is_armed and self.flight_mode == "TAKEOFF":
            self.demo_alt = min(150.0, self.demo_alt + 1.5)
            self.demo_speed = 8.0

            if self.demo_alt >= 150:
                self.flight_mode = "AUTO_MISSION"
                self.header.set_mode(self.flight_mode)
                self.log("DEMO: TAKEOFF COMPLETE")

        elif self.is_armed and self.flight_mode == "AUTO_MISSION":
            self.demo_speed = 40.0
            self.demo_heading = (self.demo_heading + 0.5) % 360
            self.demo_pitch = -2.0
            self.demo_roll = 3.0

        elif self.is_armed and self.flight_mode == "RTL":
            self.demo_speed = 30.0
            self.demo_heading = (self.demo_heading + 0.8) % 360
            self.demo_pitch = -1.0
            self.demo_roll = 2.0

        elif self.is_armed and self.flight_mode == "LAND":
            self.demo_speed = 3.0
            self.demo_alt = max(0.0, self.demo_alt - 0.8)

            if self.demo_alt <= 0:
                self.demo_alt = 0
                self.demo_speed = 0
                self.is_armed = False
                self.flight_mode = "DISARMED"
                self.command_panel.set_armed(False)
                self.header.set_mode(self.flight_mode)
                self.log("DEMO: LAND COMPLETE")

        elif self.is_armed and self.flight_mode == "PAUSE":
            self.demo_speed = 0
            self.demo_pitch = 0
            self.demo_roll = 0

        self.update_flight_state(
            altitude=self.demo_alt,
            speed=self.demo_speed,
            heading=self.demo_heading,
            pitch=self.demo_pitch,
            roll=self.demo_roll,
        )

        self.root.after(50, self._demo_loop)