"""
RIGEL GCS - MAVLink Session

Responsible for:
    - Parsing raw MAVLink bytes
    - Tracking target SYSID / COMPID
    - Detecting HEARTBEAT
    - Tracking received messages
    - Forwarding parsed messages to callback

This layer does NOT know about:
    - UI
    - Mission
    - Telemetry business logic
    - Flight commands
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable, Optional

from pymavlink import mavutil


class MAVLinkSession:
    """
    MAVLink protocol session.

    Raw bytes enter through feed_bytes().
    Parsed MAVLink messages are emitted through callbacks.
    """

    def __init__(
        self,
        source_system: int = 255,
        source_component: int = 190,
        dialect: str = "ardupilotmega",
        on_message: Optional[Callable] = None,
        on_heartbeat: Optional[Callable] = None,
        send_raw: Optional[Callable[[bytes], bool]] = None,
        request_telemetry: bool = True,
    ):
        self.source_system = source_system
        self.source_component = source_component
        self.dialect = dialect

        self.on_message = on_message
        self.on_heartbeat = on_heartbeat
        self.send_raw = send_raw
        self.request_telemetry_enabled = bool(request_telemetry)
        self._telemetry_requested_for = set()

        # MAVLink parser.
        #
        # We use mavlink.MAVLink directly because transport
        # is already handled by UDPTransport / SerialTransport.
        mavlink_class = mavutil.mavlink.MAVLink

        self._parser = mavlink_class(
            self._mavlink_output
        )
        self._parser.srcSystem = self.source_system
        self._parser.srcComponent = self.source_component

        self.target_system: Optional[int] = None
        self.target_component: Optional[int] = None

        self.last_heartbeat_time: Optional[float] = None

        self.message_count = 0
        self.byte_count = 0

        self._message_types = defaultdict(int)

        self._last_message = None

        self._connected = False

        self._telemetry_requested_for.clear()

    # ==========================================================
    # MAVLINK OUTPUT
    # ==========================================================

    def _mavlink_output(self, data: bytes) -> None:
        """Forward encoded MAVLink bytes to the active transport."""
        if self.send_raw is None:
            return
        try:
            self.send_raw(bytes(data))
        except Exception as exc:
            print(f"[MAVLINK TX ERROR] {type(exc).__name__}: {exc}")

    def send_message(self, message) -> bool:
        """Pack and transmit one pymavlink message."""
        if self.send_raw is None:
            return False
        try:
            packet = message.pack(self._parser)
            result = self.send_raw(packet)
            return True if result is None else bool(result)
        except Exception as exc:
            print(f"[MAVLINK TX ERROR] {type(exc).__name__}: {exc}")
            return False

    def send_gcs_heartbeat(self) -> bool:
        """Send a standard GCS Heartbeat (1 Hz) to notify simulator/autopilot that GCS is active."""
        try:
            hb = self._parser.heartbeat_encode(
                getattr(mavutil.mavlink, "MAV_TYPE_GCS", 6),
                getattr(mavutil.mavlink, "MAV_AUTOPILOT_INVALID", 8),
                0,
                0,
                getattr(mavutil.mavlink, "MAV_STATE_ACTIVE", 4),
            )
            return self.send_message(hb)
        except Exception as exc:
            print(f"[GCS HEARTBEAT TX ERROR] {exc}")
            return False

    def request_telemetry(self, target_system=None, target_component=None) -> int:
        """Request useful telemetry streams from a discovered vehicle."""
        if not self.request_telemetry_enabled or self.send_raw is None:
            return 0
        sysid = target_system if target_system is not None else self.target_system
        compid = target_component if target_component is not None else self.target_component
        if sysid is None or compid is None:
            return 0
        key = (int(sysid), int(compid))
        if key in self._telemetry_requested_for:
            return 0

        sent = 0

        # 1. Standard ArduPilot / APM Data Streams (REQUEST_DATA_STREAM)
        stream_requests = [
            (getattr(mavutil.mavlink, "MAV_DATA_STREAM_EXTRA1", 10), 30),           # ATTITUDE (30 Hz)
            (getattr(mavutil.mavlink, "MAV_DATA_STREAM_EXTRA2", 11), 15),           # VFR_HUD (15 Hz)
            (getattr(mavutil.mavlink, "MAV_DATA_STREAM_POSITION", 6), 15),          # GLOBAL_POSITION_INT (15 Hz)
            (getattr(mavutil.mavlink, "MAV_DATA_STREAM_EXTENDED_STATUS", 2), 2),    # SYS_STATUS, GPS_RAW (2 Hz)
            (getattr(mavutil.mavlink, "MAV_DATA_STREAM_RAW_SENSORS", 1), 2),        # IMU RAW (2 Hz)
            (getattr(mavutil.mavlink, "MAV_DATA_STREAM_ALL", 0), 15),               # ALL (15 Hz fallback)
        ]
        for stream_id, rate_hz in stream_requests:
            try:
                stream_msg = self._parser.request_data_stream_encode(
                    int(sysid),
                    int(compid),
                    int(stream_id),
                    int(rate_hz),
                    1,  # 1 = start stream
                )
                if self.send_message(stream_msg):
                    sent += 1
            except Exception as exc:
                print(f"[MAVLINK DATA STREAM ERROR] {exc}")

        # 2. Modern MAV_CMD_SET_MESSAGE_INTERVAL
        cmd = getattr(mavutil.mavlink, "MAV_CMD_SET_MESSAGE_INTERVAL", 511)
        requests = [
            (getattr(mavutil.mavlink, "MAVLINK_MSG_ID_GLOBAL_POSITION_INT", 33), 66666),   # 15 Hz
            (getattr(mavutil.mavlink, "MAVLINK_MSG_ID_GPS_RAW_INT", 24), 200000),           # 5 Hz
            (getattr(mavutil.mavlink, "MAVLINK_MSG_ID_ATTITUDE", 30), 33333),                # 30 Hz
            (getattr(mavutil.mavlink, "MAVLINK_MSG_ID_SYS_STATUS", 1), 500000),              # 2 Hz
            (getattr(mavutil.mavlink, "MAVLINK_MSG_ID_BATTERY_STATUS", 147), 500000),        # 2 Hz
            (getattr(mavutil.mavlink, "MAVLINK_MSG_ID_VFR_HUD", 74), 100000),                # 10 Hz
            (getattr(mavutil.mavlink, "MAVLINK_MSG_ID_HOME_POSITION", 242), 1000000),        # 1 Hz
        ]
        for msg_id, interval_us in requests:
            try:
                message = self._parser.command_long_encode(
                    int(sysid), int(compid), int(cmd), 0,
                    float(msg_id), float(interval_us), 0, 0, 0, 0, 0
                )
                if self.send_message(message):
                    sent += 1
            except Exception as exc:
                print(f"[MAVLINK TX REQUEST ERROR] {exc}")

        if sent:
            self._telemetry_requested_for.add(key)
            print(f"[MAVLINK TX] Requested telemetry from SYSID={sysid} COMPID={compid} ({sent} streams requested)")
        return sent

    # ==========================================================
    # RECEIVE
    # ==========================================================

    def feed_bytes(self, data: bytes) -> int:
        """
        Feed raw MAVLink bytes into the parser using optimized buffer parsing.

        Returns:
            Number of MAVLink messages parsed.
        """
        if not data:
            return 0

        if not isinstance(data, bytes):
            raise TypeError("MAVLinkSession.feed_bytes() requires bytes")

        self.byte_count += len(data)
        parsed = 0

        try:
            messages = self._parser.parse_buffer(data)
        except Exception as exc:
            print(f"[MAVLINK PARSE ERROR] {exc}")
            messages = None

        if messages:
            for message in messages:
                parsed += 1
                self._handle_message(message)

        return parsed

    # ==========================================================
    # MESSAGE HANDLER
    # ==========================================================

    def _handle_message(self, message) -> None:

        self.message_count += 1

        message_type = message.get_type()

        self._message_types[message_type] += 1

        self._last_message = message

        # ------------------------------------------------------
        # MAVLink source identity
        # ------------------------------------------------------

        try:
            sysid = message.get_srcSystem()
            compid = message.get_srcComponent()

        except Exception:
            sysid = None
            compid = None

        if sysid is not None and sysid > 0:
            self.last_message_time = time.monotonic()
            if self.target_system is None:
                self.target_system = sysid
                self.target_component = compid

        # ------------------------------------------------------
        # HEARTBEAT
        # ------------------------------------------------------

        if message_type == "HEARTBEAT":

            self.target_system = sysid
            self.target_component = compid

            self.last_heartbeat_time = time.monotonic()

            self._connected = True

            print(
                "[MAVLINK] HEARTBEAT "
                f"SYSID={sysid} "
                f"COMPID={compid}"
            )

            print(
                "[MAVLINK] "
                f"MAV_TYPE={getattr(message, 'type', None)} "
                f"AUTOPILOT={getattr(message, 'autopilot', None)} "
                f"BASE_MODE={getattr(message, 'base_mode', None)} "
                f"CUSTOM_MODE={getattr(message, 'custom_mode', None)}"
            )

            if self.on_heartbeat is not None:

                try:
                    self.on_heartbeat(message)

                except Exception as exc:
                    print(
                        f"[HEARTBEAT CALLBACK ERROR] {exc}"
                    )

            if self.request_telemetry_enabled:
                self.request_telemetry(sysid, compid)

        # ------------------------------------------------------
        # GENERAL CALLBACK
        # ------------------------------------------------------

        if self.on_message is not None:

            try:
                self.on_message(message)

            except Exception as exc:
                print(
                    f"[MAVLINK CALLBACK ERROR] {exc}"
                )

    # ==========================================================
    # CONNECTION STATE
    # ==========================================================

    @property
    def connected(self) -> bool:
        return self._connected

    # ==========================================================
    # HEARTBEAT
    # ==========================================================

    @property
    def seconds_since_heartbeat(self) -> Optional[float]:
        t_hb = self.last_heartbeat_time
        t_msg = getattr(self, "last_message_time", None)
        valid = [t for t in (t_hb, t_msg) if t is not None]
        if not valid:
            return None
        return time.monotonic() - max(valid)

    def heartbeat_alive(
        self,
        timeout: float = 6.0,
    ) -> bool:

        elapsed = self.seconds_since_heartbeat

        if elapsed is None:
            return False

        return elapsed <= timeout

    # ==========================================================
    # STATISTICS
    # ==========================================================

    def statistics(self) -> dict:

        return {
            "connected": self.connected,
            "target_system": self.target_system,
            "target_component": self.target_component,
            "message_count": self.message_count,
            "byte_count": self.byte_count,
            "last_heartbeat_time": self.last_heartbeat_time,
            "seconds_since_heartbeat":
                self.seconds_since_heartbeat,
            "message_types":
                dict(self._message_types),
        }

    # ==========================================================
    # MESSAGE COUNTER
    # ==========================================================

    def get_message_count(
        self,
        message_type: str,
    ) -> int:

        return self._message_types.get(
            message_type,
            0,
        )

    # ==========================================================
    # RESET
    # ==========================================================

    def reset(self) -> None:

        self.target_system = None
        self.target_component = None

        self.last_heartbeat_time = None

        self.message_count = 0
        self.byte_count = 0

        self._message_types.clear()

        self._last_message = None

        self._connected = False