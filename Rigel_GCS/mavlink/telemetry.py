"""
RIGEL GCS - MAVLink Telemetry Manager
=====================================

Transport-agnostic telemetry aggregation layer.

Device identity:
    (transport, sysid, compid)

Examples:
    UDP:1:1
    SERIAL:1:1
    UDP:2:1
    SERIAL:2:1

TelemetryManager does not open sockets or serial ports.
It only receives MAVLink messages and maintains the latest
telemetry state for each vehicle.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import threading
import time
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
)

from .messages import (
    MAVLinkMessageData,
    message_from_dict,
    message_from_mavlink,
)


# ============================================================
# TYPE DEFINITIONS
# ============================================================

TelemetryKey = Tuple[str, int, int]

TelemetryCallback = Callable[
    ["TelemetryState", MAVLinkMessageData],
    None,
]


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_int(
    value: Any,
    default: Optional[int] = None,
) -> Optional[int]:
    """
    Safely convert a value to int.
    """
    try:
        if value is None:
            return default

        return int(value)

    except (TypeError, ValueError):
        return default


def _safe_float(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:
    """
    Safely convert a value to finite float.
    """
    try:
        if value is None:
            return default

        result = float(value)

        if not math.isfinite(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


def _clean_text(
    value: Any,
) -> Optional[str]:
    """
    Convert MAVLink text fields safely to string.
    """
    if value is None:
        return None

    if isinstance(value, bytes):
        value = value.split(
            b"\x00",
            1,
        )[0]

        return value.decode(
            "utf-8",
            errors="replace",
        )

    return str(value).rstrip(
        "\x00"
    )


def _get_attr(
    message: Any,
    *names: str,
    default: Any = None,
) -> Any:
    """
    Get the first existing attribute from message.
    """
    for name in names:

        if hasattr(message, name):
            return getattr(
                message,
                name,
            )

    return default


# ============================================================
# MAVLINK SOURCE ID
# ============================================================

def _source_ids(
    message: Any,
) -> Tuple[
    Optional[int],
    Optional[int],
]:
    """
    Extract SYSID / COMPID from a MAVLink message.

    Priority:
        1. get_srcSystem()
        2. get_srcComponent()
        3. sysid / compid attributes
    """

    sysid = None
    compid = None

    # --------------------------------------------------------
    # SYSID
    # --------------------------------------------------------

    try:

        getter = getattr(
            message,
            "get_srcSystem",
            None,
        )

        if callable(getter):
            sysid = getter()

    except Exception:
        pass

    # --------------------------------------------------------
    # COMPID
    # --------------------------------------------------------

    try:

        getter = getattr(
            message,
            "get_srcComponent",
            None,
        )

        if callable(getter):
            compid = getter()

    except Exception:
        pass

    sysid = _safe_int(
        sysid
    )

    compid = _safe_int(
        compid
    )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if sysid is None:

        sysid = _safe_int(
            _get_attr(
                message,
                "sysid",
            )
        )

    if compid is None:

        compid = _safe_int(
            _get_attr(
                message,
                "compid",
            )
        )

    return (
        sysid,
        compid,
    )


# ============================================================
# MESSAGE TYPE
# ============================================================

def _message_type(
    message: Any,
) -> str:
    """
    Detect MAVLink message type.
    """

    # --------------------------------------------------------
    # RIGEL MESSAGE MODEL
    # --------------------------------------------------------

    if isinstance(
        message,
        MAVLinkMessageData,
    ):

        return str(
            message.message_type
        ).upper()

    # --------------------------------------------------------
    # DICTIONARY
    # --------------------------------------------------------

    if isinstance(
        message,
        Mapping,
    ):

        return str(
            message.get(
                "message_type"
            )
            or message.get(
                "type"
            )
            or message.get(
                "name"
            )
            or "UNKNOWN"
        ).upper()

    # --------------------------------------------------------
    # PY MAVLINK
    # --------------------------------------------------------

    try:

        getter = getattr(
            message,
            "get_type",
            None,
        )

        if callable(getter):

            return str(
                getter()
            ).upper()

    except Exception:
        pass

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return str(
        _get_attr(
            message,
            "message_type",
            default="UNKNOWN",
        )
    ).upper()


# ============================================================
# PY MAVLINK -> RIGEL MESSAGE MODEL
# ============================================================

def _normalize_pymavlink_message(
    message: Any,
    transport: Optional[str] = None,
) -> MAVLinkMessageData:
    """
    Convert a pymavlink message into the RIGEL
    MAVLinkMessageData model.
    """

    msg_type = _message_type(
        message
    )

    sysid, compid = _source_ids(
        message
    )

    protocol_version = _safe_int(
        _get_attr(
            message,
            "_wire_version",
            "protocol_version",
        )
    )

    common = {
        "sysid": sysid,
        "compid": compid,
        "protocol_version": protocol_version,
    }

    # ========================================================
    # HEARTBEAT
    # ========================================================

    if msg_type == "HEARTBEAT":

        return message_from_dict({

            "message_type": "HEARTBEAT",

            **common,

            "mav_type": _safe_int(
                _get_attr(
                    message,
                    "type",
                )
            ),

            "autopilot": _safe_int(
                _get_attr(
                    message,
                    "autopilot",
                )
            ),

            "base_mode": _safe_int(
                _get_attr(
                    message,
                    "base_mode",
                )
            ),

            "custom_mode": _safe_int(
                _get_attr(
                    message,
                    "custom_mode",
                )
            ),

            "system_status": _safe_int(
                _get_attr(
                    message,
                    "system_status",
                )
            ),
        })

    # ========================================================
    # GPS_RAW_INT
    # ========================================================

    if msg_type == "GPS_RAW_INT":

        lat = _safe_float(
            _get_attr(
                message,
                "lat",
            )
        )

        lon = _safe_float(
            _get_attr(
                message,
                "lon",
            )
        )

        alt = _safe_float(
            _get_attr(
                message,
                "alt",
            )
        )

        satellites = _safe_int(
            _get_attr(
                message,
                "satellites_visible",
            )
        )

        return message_from_dict({

            "message_type": "GPS_RAW_INT",

            **common,

            "latitude": (
                None
                if lat is None
                else lat * 1e-7
            ),

            "longitude": (
                None
                if lon is None
                else lon * 1e-7
            ),

            "altitude": (
                None
                if alt is None
                else alt / 1000.0
            ),

            "fix_type": _safe_int(
                _get_attr(
                    message,
                    "fix_type",
                )
            ),

            # IMPORTANT:
            # GPSRawMessage uses satellites_visible
            "satellites_visible": satellites,
        })

    # ========================================================
    # GLOBAL_POSITION_INT
    # ========================================================

    if msg_type == "GLOBAL_POSITION_INT":

        lat = _safe_float(
            _get_attr(
                message,
                "lat",
            )
        )

        lon = _safe_float(
            _get_attr(
                message,
                "lon",
            )
        )

        alt = _safe_float(
            _get_attr(
                message,
                "alt",
            )
        )

        relative_alt = _safe_float(
            _get_attr(
                message,
                "relative_alt",
            )
        )

        vx = _safe_float(
            _get_attr(
                message,
                "vx",
            )
        )

        vy = _safe_float(
            _get_attr(
                message,
                "vy",
            )
        )

        vz = _safe_float(
            _get_attr(
                message,
                "vz",
            )
        )

        heading = _safe_float(
            _get_attr(
                message,
                "hdg",
            )
        )

        return message_from_dict({

            "message_type":
                "GLOBAL_POSITION_INT",

            **common,

            "latitude": (
                None
                if lat is None
                else lat * 1e-7
            ),

            "longitude": (
                None
                if lon is None
                else lon * 1e-7
            ),

            "altitude": (
                None
                if alt is None
                else alt / 1000.0
            ),

            "relative_altitude": (
                None
                if relative_alt is None
                else relative_alt / 1000.0
            ),

            "velocity_x": (
                None
                if vx is None
                else vx / 100.0
            ),

            "velocity_y": (
                None
                if vy is None
                else vy / 100.0
            ),

            "velocity_z": (
                None
                if vz is None
                else vz / 100.0
            ),

            "heading": (
                None
                if heading is None
                else heading / 100.0
            ),
        })

    # ========================================================
    # ATTITUDE
    # ========================================================

    if msg_type == "ATTITUDE":

        return message_from_dict({

            "message_type":
                "ATTITUDE",

            **common,

            "roll": _safe_float(
                _get_attr(
                    message,
                    "roll",
                )
            ),

            "pitch": _safe_float(
                _get_attr(
                    message,
                    "pitch",
                )
            ),

            "yaw": _safe_float(
                _get_attr(
                    message,
                    "yaw",
                )
            ),

            "roll_speed": _safe_float(
                _get_attr(
                    message,
                    "rollspeed",
                )
            ),

            "pitch_speed": _safe_float(
                _get_attr(
                    message,
                    "pitchspeed",
                )
            ),

            "yaw_speed": _safe_float(
                _get_attr(
                    message,
                    "yawspeed",
                )
            ),
        })

    # ========================================================
    # SYS_STATUS
    # ========================================================

    if msg_type == "SYS_STATUS":

        voltage = _safe_float(
            _get_attr(
                message,
                "voltage_battery",
            )
        )

        current = _safe_float(
            _get_attr(
                message,
                "current_battery",
            )
        )

        load = _safe_float(
            _get_attr(
                message,
                "load",
            )
        )

        return message_from_dict({

            "message_type":
                "SYS_STATUS",

            **common,

            "voltage_battery": (
                None
                if voltage is None
                else voltage / 1000.0
            ),

            "current_battery": (
                None
                if current is None
                else current / 100.0
            ),

            "battery_remaining":
                _safe_int(
                    _get_attr(
                        message,
                        "battery_remaining",
                    )
                ),

            "load": (
                None
                if load is None
                else load / 10.0
            ),
        })

    # ========================================================
    # BATTERY_STATUS
    # ========================================================

    if msg_type == "BATTERY_STATUS":

        return message_from_dict({

            "message_type":
                "BATTERY_STATUS",

            **common,

            "battery_id": _safe_int(
                _get_attr(
                    message,
                    "id",
                )
            ),

            # IMPORTANT:
            # BatteryStatusMessage uses battery_remaining
            "battery_remaining":
                _safe_int(
                    _get_attr(
                        message,
                        "battery_remaining",
                    )
                ),

            "current_consumed":
                _safe_int(
                    _get_attr(
                        message,
                        "current_consumed",
                    )
                ),

            "energy_consumed":
                _safe_int(
                    _get_attr(
                        message,
                        "energy_consumed",
                    )
                ),
        })

    # ========================================================
    # VFR_HUD
    # ========================================================

    if msg_type == "VFR_HUD":

        return message_from_dict({

            "message_type":
                "VFR_HUD",

            **common,

            "airspeed": _safe_float(
                _get_attr(
                    message,
                    "airspeed",
                )
            ),

            "groundspeed": _safe_float(
                _get_attr(
                    message,
                    "groundspeed",
                )
            ),

            "heading": _safe_float(
                _get_attr(
                    message,
                    "heading",
                )
            ),

            "throttle": _safe_int(
                _get_attr(
                    message,
                    "throttle",
                )
            ),

            "altitude": _safe_float(
                _get_attr(
                    message,
                    "alt",
                )
            ),

            "climb": _safe_float(
                _get_attr(
                    message,
                    "climb",
                )
            ),
        })

    # ========================================================
    # HOME_POSITION
    # ========================================================

    if msg_type == "HOME_POSITION":

        lat = _safe_float(
            _get_attr(
                message,
                "latitude",
                "lat",
            )
        )

        lon = _safe_float(
            _get_attr(
                message,
                "longitude",
                "lon",
            )
        )

        alt = _safe_float(
            _get_attr(
                message,
                "altitude",
                "alt",
            )
        )

        return message_from_dict({

            "message_type":
                "HOME_POSITION",

            **common,

            "latitude": (
                None
                if lat is None
                else lat * 1e-7
            ),

            "longitude": (
                None
                if lon is None
                else lon * 1e-7
            ),

            "altitude": (
                None
                if alt is None
                else alt / 1000.0
            ),

            "x": _safe_float(
                _get_attr(
                    message,
                    "x",
                )
            ),

            "y": _safe_float(
                _get_attr(
                    message,
                    "y",
                )
            ),

            "z": _safe_float(
                _get_attr(
                    message,
                    "z",
                )
            ),
        })

    # ========================================================
    # STATUSTEXT
    # ========================================================

    if msg_type == "STATUSTEXT":

        return message_from_dict({

            "message_type":
                "STATUSTEXT",

            **common,

            "severity": _safe_int(
                _get_attr(
                    message,
                    "severity",
                )
            ),

            "text": _clean_text(
                _get_attr(
                    message,
                    "text",
                )
            ),
        })

    # ========================================================
    # UNKNOWN MESSAGE
    # ========================================================

    return message_from_dict({

        "message_type": msg_type,

        **common,
    })


# ============================================================
# PUBLIC NORMALIZER
# ============================================================

def normalize_telemetry_message(
    message: Any,
    transport: Optional[str] = None,
) -> MAVLinkMessageData:
    """
    Normalize any supported MAVLink message into
    MAVLinkMessageData.
    """

    # --------------------------------------------------------
    # Already normalized
    # --------------------------------------------------------

    if isinstance(
        message,
        MAVLinkMessageData,
    ):
        return message

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(
        message,
        Mapping,
    ):

        return message_from_dict(
            dict(message)
        )

    # --------------------------------------------------------
    # RIGEL custom MAVLinkMessage
    # --------------------------------------------------------

    if (
        hasattr(message, "raw")
        and hasattr(message, "message_type")
    ):

        try:

            return message_from_mavlink(
                message
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # pymavlink
    # --------------------------------------------------------

    return _normalize_pymavlink_message(
        message,
        transport=transport,
    )


# ============================================================
# TELEMETRY STATE
# ============================================================

@dataclass
class TelemetryState:

    # ========================================================
    # IDENTITY
    # ========================================================

    sysid: int
    compid: int

    transport: str = "UNKNOWN"

    rx_endpoint: Optional[str] = None
    tx_endpoint: Optional[str] = None

    # ========================================================
    # CONNECTION
    # ========================================================

    connected: bool = False

    last_update: Optional[float] = None

    last_heartbeat: Optional[float] = None

    # ========================================================
    # HEARTBEAT
    # ========================================================

    mav_type: Optional[int] = None

    autopilot: Optional[int] = None

    base_mode: Optional[int] = None

    custom_mode: Optional[int] = None

    system_status: Optional[int] = None

    armed: Optional[bool] = None

    # ========================================================
    # GPS
    # ========================================================

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    gps_altitude: Optional[float] = None

    fix_type: Optional[int] = None

    satellites_visible: Optional[int] = None

    gps_has_fix: Optional[bool] = None

    # ========================================================
    # POSITION
    # ========================================================

    altitude: Optional[float] = None

    relative_altitude: Optional[float] = None

    velocity_x: Optional[float] = None

    velocity_y: Optional[float] = None

    velocity_z: Optional[float] = None

    ground_speed: Optional[float] = None

    heading: Optional[float] = None

    # ========================================================
    # ATTITUDE
    # ========================================================

    roll: Optional[float] = None

    pitch: Optional[float] = None

    yaw: Optional[float] = None

    roll_speed: Optional[float] = None

    pitch_speed: Optional[float] = None

    yaw_speed: Optional[float] = None

    # ========================================================
    # SYSTEM STATUS
    # ========================================================

    voltage_battery: Optional[float] = None

    current_battery: Optional[float] = None

    battery_remaining: Optional[int] = None

    load: Optional[float] = None

    # ========================================================
    # BATTERY STATUS
    # ========================================================

    battery_id: Optional[int] = None

    battery_status_remaining: Optional[int] = None

    current_consumed: Optional[int] = None

    energy_consumed: Optional[int] = None

    # ========================================================
    # VFR HUD
    # ========================================================

    airspeed: Optional[float] = None

    vfr_groundspeed: Optional[float] = None

    vfr_heading: Optional[float] = None

    throttle: Optional[float] = None

    vfr_altitude: Optional[float] = None

    climb: Optional[float] = None

    # ========================================================
    # HOME
    # ========================================================

    home_latitude: Optional[float] = None

    home_longitude: Optional[float] = None

    home_altitude: Optional[float] = None

    home_x: Optional[float] = None

    home_y: Optional[float] = None

    home_z: Optional[float] = None

    # ========================================================
    # STATUS TEXT
    # ========================================================

    status_severity: Optional[int] = None

    status_text: Optional[str] = None

    # ========================================================
    # DIAGNOSTICS
    # ========================================================

    last_message_type: Optional[str] = None

    message_counts: Dict[str, int] = field(
        default_factory=dict
    )

    # ========================================================
    # PROPERTIES
    # ========================================================

    @property
    def device_id(self) -> str:
        """
        Transport-aware device ID.

        Examples:
            UDP:1:1
            SERIAL:1:1
        """

        return (
            f"{str(self.transport).upper()}:"
            f"{self.sysid}:"
            f"{self.compid}"
        )

    @property
    def heartbeat_alive(self) -> bool:
        """
        Return True if heartbeat was received recently.
        """

        if self.last_heartbeat is None:
            return False

        return (
            time.monotonic()
            - self.last_heartbeat
        ) <= 3.0

    @property
    def groundspeed(
        self,
    ) -> Optional[float]:
        """
        Compatibility alias for VFR_HUD groundspeed.

        VFR_HUD:
            vfr_groundspeed

        GLOBAL_POSITION_INT:
            ground_speed
        """

        if self.vfr_groundspeed is not None:
            return self.vfr_groundspeed

        return self.ground_speed

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        message: MAVLinkMessageData,
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Update latest telemetry state from a normalized
        MAVLink message.
        """

        now = (
            time.monotonic()
            if timestamp is None
            else timestamp
        )

        msg_type = str(
            message.message_type
        ).upper()

        # ----------------------------------------------------
        # GENERAL
        # ----------------------------------------------------

        self.last_update = now

        self.last_message_type = msg_type

        self.connected = True

        self.message_counts[msg_type] = (
            self.message_counts.get(
                msg_type,
                0,
            )
            + 1
        )

        # ====================================================
        # HEARTBEAT
        # ====================================================

        if msg_type == "HEARTBEAT":

            self.mav_type = getattr(
                message,
                "mav_type",
                self.mav_type,
            )

            self.autopilot = getattr(
                message,
                "autopilot",
                self.autopilot,
            )

            self.base_mode = getattr(
                message,
                "base_mode",
                self.base_mode,
            )

            self.custom_mode = getattr(
                message,
                "custom_mode",
                self.custom_mode,
            )

            self.system_status = getattr(
                message,
                "system_status",
                self.system_status,
            )

            armed = getattr(
                message,
                "armed",
                None,
            )

            if armed is not None:
                self.armed = bool(
                    armed
                )

            self.last_heartbeat = now

        # ====================================================
        # GPS_RAW_INT
        # ====================================================

        elif msg_type == "GPS_RAW_INT":

            self.latitude = getattr(
                message,
                "latitude",
                self.latitude,
            )

            self.longitude = getattr(
                message,
                "longitude",
                self.longitude,
            )

            self.gps_altitude = getattr(
                message,
                "altitude",
                self.gps_altitude,
            )

            self.fix_type = getattr(
                message,
                "fix_type",
                self.fix_type,
            )

            # IMPORTANT:
            # GPSRawMessage uses satellites_visible.
            self.satellites_visible = getattr(
                message,
                "satellites_visible",
                self.satellites_visible,
            )

            if self.fix_type is not None:

                self.gps_has_fix = (
                    self.fix_type >= 2
                )

            else:

                self.gps_has_fix = None

        # ====================================================
        # GLOBAL_POSITION_INT
        # ====================================================

        elif msg_type == "GLOBAL_POSITION_INT":

            self.latitude = getattr(
                message,
                "latitude",
                self.latitude,
            )

            self.longitude = getattr(
                message,
                "longitude",
                self.longitude,
            )

            self.altitude = getattr(
                message,
                "altitude",
                self.altitude,
            )

            self.relative_altitude = getattr(
                message,
                "relative_altitude",
                self.relative_altitude,
            )

            self.velocity_x = getattr(
                message,
                "velocity_x",
                self.velocity_x,
            )

            self.velocity_y = getattr(
                message,
                "velocity_y",
                self.velocity_y,
            )

            self.velocity_z = getattr(
                message,
                "velocity_z",
                self.velocity_z,
            )

            self.heading = getattr(
                message,
                "heading",
                self.heading,
            )

            if (
                self.velocity_x is not None
                and self.velocity_y is not None
            ):

                self.ground_speed = math.sqrt(
                    self.velocity_x ** 2
                    + self.velocity_y ** 2
                )

        # ====================================================
        # ATTITUDE
        # ====================================================

        elif msg_type == "ATTITUDE":

            self.roll = getattr(
                message,
                "roll",
                self.roll,
            )

            self.pitch = getattr(
                message,
                "pitch",
                self.pitch,
            )

            self.yaw = getattr(
                message,
                "yaw",
                self.yaw,
            )

            self.roll_speed = getattr(
                message,
                "roll_speed",
                self.roll_speed,
            )

            self.pitch_speed = getattr(
                message,
                "pitch_speed",
                self.pitch_speed,
            )

            self.yaw_speed = getattr(
                message,
                "yaw_speed",
                self.yaw_speed,
            )

        # ====================================================
        # SYS_STATUS
        # ====================================================

        elif msg_type == "SYS_STATUS":

            self.voltage_battery = getattr(
                message,
                "voltage_battery",
                self.voltage_battery,
            )

            self.current_battery = getattr(
                message,
                "current_battery",
                self.current_battery,
            )

            self.battery_remaining = getattr(
                message,
                "battery_remaining",
                self.battery_remaining,
            )

            self.load = getattr(
                message,
                "load",
                self.load,
            )

        # ====================================================
        # BATTERY_STATUS
        # ====================================================

        elif msg_type == "BATTERY_STATUS":

            self.battery_id = getattr(
                message,
                "battery_id",
                self.battery_id,
            )

            remaining = getattr(
                message,
                "battery_remaining",
                None,
            )

            if remaining is not None:

                self.battery_status_remaining = (
                    remaining
                )

                if remaining >= 0:

                    self.battery_remaining = (
                        remaining
                    )

            self.current_consumed = getattr(
                message,
                "current_consumed",
                self.current_consumed,
            )

            self.energy_consumed = getattr(
                message,
                "energy_consumed",
                self.energy_consumed,
            )

        # ====================================================
        # VFR_HUD
        # ====================================================

        elif msg_type == "VFR_HUD":

            self.airspeed = getattr(
                message,
                "airspeed",
                self.airspeed,
            )

            self.vfr_groundspeed = getattr(
                message,
                "groundspeed",
                self.vfr_groundspeed,
            )

            self.vfr_heading = getattr(
                message,
                "heading",
                self.vfr_heading,
            )

            self.throttle = getattr(
                message,
                "throttle",
                self.throttle,
            )

            self.vfr_altitude = getattr(
                message,
                "altitude",
                self.vfr_altitude,
            )

            self.climb = getattr(
                message,
                "climb",
                self.climb,
            )

            # ------------------------------------------------
            # Update generic telemetry fields when available.
            # ------------------------------------------------

            if (
                self.vfr_groundspeed is not None
            ):

                self.ground_speed = (
                    self.vfr_groundspeed
                )

            if (
                self.vfr_heading is not None
            ):

                self.heading = (
                    self.vfr_heading
                )

            if (
                self.vfr_altitude is not None
            ):

                self.altitude = (
                    self.vfr_altitude
                )

        # ====================================================
        # HOME_POSITION
        # ====================================================

        elif msg_type == "HOME_POSITION":

            self.home_latitude = getattr(
                message,
                "latitude",
                self.home_latitude,
            )

            self.home_longitude = getattr(
                message,
                "longitude",
                self.home_longitude,
            )

            self.home_altitude = getattr(
                message,
                "altitude",
                self.home_altitude,
            )

            self.home_x = getattr(
                message,
                "x",
                self.home_x,
            )

            self.home_y = getattr(
                message,
                "y",
                self.home_y,
            )

            self.home_z = getattr(
                message,
                "z",
                self.home_z,
            )

        # ====================================================
        # STATUSTEXT
        # ====================================================

        elif msg_type == "STATUSTEXT":

            self.status_severity = getattr(
                message,
                "severity",
                self.status_severity,
            )

            self.status_text = getattr(
                message,
                "text",
                self.status_text,
            )

    # ========================================================
    # DISCONNECT
    # ========================================================

    def disconnect(self) -> None:
        """
        Mark telemetry state as disconnected.
        """

        self.connected = False

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        """
        Convert telemetry state to dictionary.
        """

        data = asdict(
            self
        )

        data["device_id"] = (
            self.device_id
        )

        data["heartbeat_alive"] = (
            self.heartbeat_alive
        )

        # Properties are not included by asdict(),
        # therefore expose compatibility fields explicitly.
        data["groundspeed"] = (
            self.groundspeed
        )

        return data

    def snapshot(
        self,
    ) -> Dict[str, Any]:
        """
        Return telemetry snapshot.
        """

        return self.to_dict()


# ============================================================
# TELEMETRY MANAGER
# ============================================================

class TelemetryManager:
    """
    Thread-safe manager for multiple MAVLink vehicles.
    """

    def __init__(
        self,
        on_update: Optional[
            TelemetryCallback
        ] = None,
        heartbeat_timeout: float = 3.0,
    ) -> None:

        self.on_update = on_update

        self.heartbeat_timeout = float(
            heartbeat_timeout
        )

        self._states: Dict[
            TelemetryKey,
            TelemetryState,
        ] = {}

        self._lock = threading.RLock()

    # ========================================================
    # KEY
    # ========================================================

    @staticmethod
    def make_key(
        sysid: int,
        compid: int,
        transport: Optional[str] = None,
    ) -> TelemetryKey:

        return (
            str(
                transport or "UNKNOWN"
            ).upper(),

            int(sysid),

            int(compid),
        )

    @staticmethod
    def make_device_id(
        sysid: int,
        compid: int,
        transport: Optional[str] = None,
    ) -> str:

        return (
            f"{str(transport or 'UNKNOWN').upper()}:"
            f"{int(sysid)}:"
            f"{int(compid)}"
        )

    # ========================================================
    # CREATE / GET
    # ========================================================

    def get_or_create(
        self,
        sysid: int,
        compid: int,
        transport: Optional[str] = None,
        rx_endpoint: Optional[str] = None,
        tx_endpoint: Optional[str] = None,
    ) -> TelemetryState:

        key = self.make_key(
            sysid,
            compid,
            transport,
        )

        with self._lock:

            state = self._states.get(
                key
            )

            if state is None:

                state = TelemetryState(

                    sysid=int(
                        sysid
                    ),

                    compid=int(
                        compid
                    ),

                    transport=str(
                        transport or "UNKNOWN"
                    ).upper(),

                    rx_endpoint=rx_endpoint,

                    tx_endpoint=tx_endpoint,
                )

                self._states[key] = state

            else:

                if rx_endpoint is not None:

                    state.rx_endpoint = (
                        rx_endpoint
                    )

                if tx_endpoint is not None:

                    state.tx_endpoint = (
                        tx_endpoint
                    )

            return state

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        message: Any,
        device: Any = None,
        transport: Optional[str] = None,
        sysid: Optional[int] = None,
        compid: Optional[int] = None,
        rx_endpoint: Optional[str] = None,
        tx_endpoint: Optional[str] = None,
    ) -> TelemetryState:

        # ====================================================
        # DEVICE METADATA
        # ====================================================

        if device is not None:

            if sysid is None:

                sysid = _safe_int(
                    getattr(
                        device,
                        "sysid",
                        None,
                    )
                )

            if compid is None:

                compid = _safe_int(
                    getattr(
                        device,
                        "compid",
                        None,
                    )
                )

            if transport is None:

                transport = getattr(
                    device,
                    "transport",
                    None,
                )

            if rx_endpoint is None:

                rx_endpoint = getattr(
                    device,
                    "rx_endpoint",
                    None,
                )

            if tx_endpoint is None:

                tx_endpoint = getattr(
                    device,
                    "tx_endpoint",
                    None,
                )

        # ====================================================
        # NORMALIZE MESSAGE
        # ====================================================

        normalized = (
            normalize_telemetry_message(
                message,
                transport=transport,
            )
        )

        # ====================================================
        # SOURCE ID
        # ====================================================

        if sysid is None:

            sysid = normalized.sysid

        if compid is None:

            compid = normalized.compid

        if sysid is None or compid is None:

            raise ValueError(
                "Telemetry update requires "
                "SYSID and COMPID."
            )

        # ====================================================
        # GET STATE
        # ====================================================

        state = self.get_or_create(

            sysid=int(
                sysid
            ),

            compid=int(
                compid
            ),

            transport=transport,

            rx_endpoint=rx_endpoint,

            tx_endpoint=tx_endpoint,
        )

        # ====================================================
        # FORCE IDENTITY
        # ====================================================

        normalized.sysid = int(
            sysid
        )

        normalized.compid = int(
            compid
        )

        if transport is not None:

            state.transport = str(
                transport
            ).upper()

        # ====================================================
        # UPDATE
        # ====================================================

        with self._lock:

            state.update(
                normalized
            )

            callback = self.on_update

        # ====================================================
        # CALLBACK
        # ====================================================

        if callback is not None:

            try:

                callback(
                    state,
                    normalized,
                )

            except Exception as exc:

                print(
                    "[TELEMETRY CALLBACK ERROR]",
                    exc,
                )

        return state

    # ========================================================
    # GET
    # ========================================================

    def get(
        self,
        sysid: int,
        compid: int,
        transport: Optional[str] = None,
    ) -> Optional[TelemetryState]:

        key = self.make_key(
            sysid,
            compid,
            transport,
        )

        with self._lock:

            return self._states.get(
                key
            )

    # ========================================================
    # GET BY DEVICE ID
    # ========================================================

    def get_by_id(
        self,
        device_id: str,
    ) -> Optional[TelemetryState]:

        target = str(
            device_id
        ).upper()

        with self._lock:

            for state in (
                self._states.values()
            ):

                if (
                    state.device_id.upper()
                    == target
                ):

                    return state

        return None

    # ========================================================
    # ALL
    # ========================================================

    def all(
        self,
    ) -> List[TelemetryState]:

        with self._lock:

            return list(
                self._states.values()
            )

    # ========================================================
    # SNAPSHOT
    # ========================================================

    def snapshot(
        self,
    ) -> Dict[
        str,
        Dict[str, Any],
    ]:

        with self._lock:

            return {
                state.device_id:
                    state.snapshot()
                for state
                in self._states.values()
            }

    # ========================================================
    # INFO
    # ========================================================

    def info(
        self,
    ) -> Dict[str, Any]:

        return {
            "count": self.count(),
            "devices": self.snapshot(),
        }

    # ========================================================
    # COUNT
    # ========================================================

    def count(
        self,
    ) -> int:

        with self._lock:

            return len(
                self._states
            )

    # ========================================================
    # DISCONNECT
    # ========================================================

    def mark_disconnected(
        self,
        sysid: int,
        compid: int,
        transport: Optional[str] = None,
    ) -> bool:

        state = self.get(
            sysid,
            compid,
            transport,
        )

        if state is None:

            return False

        with self._lock:

            state.disconnect()

        return True

    # ========================================================
    # REMOVE
    # ========================================================

    def remove(
        self,
        sysid: int,
        compid: int,
        transport: Optional[str] = None,
    ) -> Optional[TelemetryState]:

        key = self.make_key(
            sysid,
            compid,
            transport,
        )

        with self._lock:

            return self._states.pop(
                key,
                None,
            )

    # ========================================================
    # REMOVE BY ID
    # ========================================================

    def remove_by_id(
        self,
        device_id: str,
    ) -> Optional[TelemetryState]:

        target = str(
            device_id
        ).upper()

        with self._lock:

            for key, state in list(
                self._states.items()
            ):

                if (
                    state.device_id.upper()
                    == target
                ):

                    return self._states.pop(
                        key
                    )

        return None

    # ========================================================
    # CLEAR
    # ========================================================

    def clear(
        self,
    ) -> None:

        with self._lock:

            self._states.clear()

    # ========================================================
    # CONNECTED DEVICES
    # ========================================================

    def connected_devices(
        self,
    ) -> List[TelemetryState]:

        with self._lock:

            return [
                state
                for state
                in self._states.values()
                if (
                    state.heartbeat_alive
                )
            ]

    # ========================================================
    # DEVICE IDS
    # ========================================================

    def device_ids(
        self,
    ) -> List[str]:

        with self._lock:

            return [
                state.device_id
                for state
                in self._states.values()
            ]


# ============================================================
# PUBLIC API
# ============================================================

__all__ = [
    "TelemetryKey",
    "TelemetryState",
    "TelemetryManager",
    "normalize_telemetry_message",
]