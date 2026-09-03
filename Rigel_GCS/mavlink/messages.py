"""
RIGEL GCS - MAVLink Message Models

Responsibilities
----------------
* Provide transport-independent message data models.
* Keep SYSID/COMPID and MAVLink protocol version.
* Convert normalized dictionaries into strongly structured objects.
* Keep this layer independent from Serial/UDP/Core/UI.

This module does NOT:
* open connections;
* parse raw MAVLink bytes;
* send commands;
* manage missions;
* contain UI code.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# ============================================================================
# BASE MESSAGE
# ============================================================================

@dataclass
class MAVLinkMessageData:
    """
    Base representation of one normalized MAVLink message.

    message_type is automatically defined by each specialized message model.
    """

    sysid: Optional[int] = None
    compid: Optional[int] = None
    protocol_version: Optional[int] = None

    # Not part of __init__ because subclasses define their own type.
    message_type: str = field(
        default="UNKNOWN",
        init=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation."""
        return asdict(self)


# ============================================================================
# HEARTBEAT
# ============================================================================

@dataclass
class HeartbeatMessage(MAVLinkMessageData):
    """Normalized HEARTBEAT message."""

    message_type: str = field(
        default="HEARTBEAT",
        init=False,
    )

    mav_type: Optional[int] = None
    autopilot: Optional[int] = None
    base_mode: Optional[int] = None
    custom_mode: Optional[int] = None
    system_status: Optional[int] = None

    @property
    def armed(self) -> bool:
        """
        Return True when MAV_MODE_FLAG_SAFETY_ARMED is set.

        MAVLink:
            MAV_MODE_FLAG_SAFETY_ARMED = 128 = 0x80
        """
        if self.base_mode is None:
            return False

        try:
            return bool(int(self.base_mode) & 0x80)
        except (TypeError, ValueError):
            return False

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result["armed"] = self.armed

        return result


# ============================================================================
# GLOBAL_POSITION_INT
# ============================================================================

@dataclass
class GlobalPositionMessage(MAVLinkMessageData):
    """Normalized GLOBAL_POSITION_INT."""

    message_type: str = field(
        default="GLOBAL_POSITION_INT",
        init=False,
    )

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    relative_altitude: Optional[float] = None

    velocity_x: Optional[float] = None
    velocity_y: Optional[float] = None
    velocity_z: Optional[float] = None

    heading: Optional[float] = None

    @property
    def ground_speed(self) -> Optional[float]:
        """Calculate horizontal ground speed from vx and vy."""

        if self.velocity_x is None or self.velocity_y is None:
            return None

        try:
            vx = float(self.velocity_x)
            vy = float(self.velocity_y)

            return (vx ** 2 + vy ** 2) ** 0.5

        except (TypeError, ValueError):
            return None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude,
                "relative_altitude": self.relative_altitude,
                "velocity_x": self.velocity_x,
                "velocity_y": self.velocity_y,
                "velocity_z": self.velocity_z,
                "heading": self.heading,
                "ground_speed": self.ground_speed,
            }
        )

        return result


# ============================================================================
# GPS_RAW_INT
# ============================================================================

@dataclass
class GPSRawMessage(MAVLinkMessageData):
    """Normalized GPS_RAW_INT."""

    message_type: str = field(
        default="GPS_RAW_INT",
        init=False,
    )

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None

    fix_type: Optional[int] = None
    satellites_visible: Optional[int] = None

    @property
    def has_fix(self) -> bool:
        """Return True when GPS fix type is at least 2D fix."""

        if self.fix_type is None:
            return False

        try:
            return int(self.fix_type) >= 2

        except (TypeError, ValueError):
            return False

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude,
                "fix_type": self.fix_type,
                "satellites_visible": self.satellites_visible,
                "has_fix": self.has_fix,
            }
        )

        return result


# ============================================================================
# ATTITUDE
# ============================================================================

@dataclass
class AttitudeMessage(MAVLinkMessageData):
    """Normalized ATTITUDE."""

    message_type: str = field(
        default="ATTITUDE",
        init=False,
    )

    roll: Optional[float] = None
    pitch: Optional[float] = None
    yaw: Optional[float] = None

    roll_speed: Optional[float] = None
    pitch_speed: Optional[float] = None
    yaw_speed: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "roll": self.roll,
                "pitch": self.pitch,
                "yaw": self.yaw,
                "roll_speed": self.roll_speed,
                "pitch_speed": self.pitch_speed,
                "yaw_speed": self.yaw_speed,
            }
        )

        return result


# ============================================================================
# SYS_STATUS
# ============================================================================

@dataclass
class SystemStatusMessage(MAVLinkMessageData):
    """Normalized SYS_STATUS."""

    message_type: str = field(
        default="SYS_STATUS",
        init=False,
    )

    voltage_battery: Optional[float] = None
    current_battery: Optional[float] = None
    battery_remaining: Optional[int] = None
    load: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "voltage_battery": self.voltage_battery,
                "current_battery": self.current_battery,
                "battery_remaining": self.battery_remaining,
                "load": self.load,
            }
        )

        return result


# ============================================================================
# BATTERY_STATUS
# ============================================================================

@dataclass
class BatteryStatusMessage(MAVLinkMessageData):
    """Normalized BATTERY_STATUS."""

    message_type: str = field(
        default="BATTERY_STATUS",
        init=False,
    )

    battery_id: Optional[int] = None
    battery_remaining: Optional[int] = None
    current_consumed: Optional[int] = None
    energy_consumed: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "battery_id": self.battery_id,
                "battery_remaining": self.battery_remaining,
                "current_consumed": self.current_consumed,
                "energy_consumed": self.energy_consumed,
            }
        )

        return result


# ============================================================================
# VFR_HUD
# ============================================================================

@dataclass
class VFRHUDMessage(MAVLinkMessageData):
    """Normalized VFR_HUD."""

    message_type: str = field(
        default="VFR_HUD",
        init=False,
    )

    airspeed: Optional[float] = None
    groundspeed: Optional[float] = None
    heading: Optional[int] = None
    throttle: Optional[int] = None
    altitude: Optional[float] = None
    climb: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "airspeed": self.airspeed,
                "groundspeed": self.groundspeed,
                "heading": self.heading,
                "throttle": self.throttle,
                "altitude": self.altitude,
                "climb": self.climb,
            }
        )

        return result


# ============================================================================
# HOME_POSITION
# ============================================================================

@dataclass
class HomePositionMessage(MAVLinkMessageData):
    """Normalized HOME_POSITION."""

    message_type: str = field(
        default="HOME_POSITION",
        init=False,
    )

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None

    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude,
                "x": self.x,
                "y": self.y,
                "z": self.z,
            }
        )

        return result


# ============================================================================
# STATUSTEXT
# ============================================================================

@dataclass
class StatusTextMessage(MAVLinkMessageData):
    """Normalized STATUSTEXT."""

    message_type: str = field(
        default="STATUSTEXT",
        init=False,
    )

    severity: Optional[int] = None
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()

        result.update(
            {
                "severity": self.severity,
                "text": self.text,
            }
        )

        return result


# ============================================================================
# MESSAGE FACTORY
# ============================================================================

_MESSAGE_TYPES: dict[str, type[MAVLinkMessageData]] = {
    "HEARTBEAT": HeartbeatMessage,
    "GLOBAL_POSITION_INT": GlobalPositionMessage,
    "GPS_RAW_INT": GPSRawMessage,
    "ATTITUDE": AttitudeMessage,
    "SYS_STATUS": SystemStatusMessage,
    "BATTERY_STATUS": BatteryStatusMessage,
    "VFR_HUD": VFRHUDMessage,
    "HOME_POSITION": HomePositionMessage,
    "STATUSTEXT": StatusTextMessage,
}


def message_from_dict(
    data: dict[str, Any],
) -> MAVLinkMessageData:
    """
    Create the appropriate message model from a normalized dictionary.

    Example
    -------
    {
        "message_type": "HEARTBEAT",
        "sysid": 1,
        "compid": 1,
        "protocol_version": 2,
        "mav_type": 2,
        "autopilot": 3
    }
    """

    if not isinstance(data, dict):
        raise TypeError("data must be a dictionary")

    message_type = data.get("message_type")

    if not message_type:
        raise ValueError(
            "Missing 'message_type' in message data"
        )

    message_type = str(message_type).upper()

    cls = _MESSAGE_TYPES.get(message_type)

    # ----------------------------------------------------------------------
    # Unknown MAVLink message
    # ----------------------------------------------------------------------

    if cls is None:
        result = MAVLinkMessageData(
            sysid=data.get("sysid"),
            compid=data.get("compid"),
            protocol_version=data.get("protocol_version"),
        )

        result.message_type = message_type

        return result

    # ----------------------------------------------------------------------
    # Common fields
    # ----------------------------------------------------------------------

    common = {
        "sysid": data.get("sysid"),
        "compid": data.get("compid"),
        "protocol_version": data.get("protocol_version"),
    }

    # ----------------------------------------------------------------------
    # Specialized fields
    # ----------------------------------------------------------------------

    ignored_fields = {
        "message_type",
        "sysid",
        "compid",
        "protocol_version",

        # Computed properties
        "armed",
        "ground_speed",
        "has_fix",
    }

    fields = {
        key: value
        for key, value in data.items()
        if key not in ignored_fields
    }

    return cls(
        **common,
        **fields,
    )


# ============================================================================
# MAVLINK OBJECT CONVERSION
# ============================================================================

def message_from_mavlink(
    message: Any,
) -> MAVLinkMessageData:
    """
    Convert a MAVLink object or normalized dictionary into a message model.

    The import of normalize_message() is intentionally lazy to avoid
    circular imports between mavlink.py and messages.py.
    """

    # ----------------------------------------------------------------------
    # Already normalized dictionary
    # ----------------------------------------------------------------------

    if isinstance(message, dict):
        return message_from_dict(message)

    # ----------------------------------------------------------------------
    # MAVLinkMessage object from mavlink.py
    # ----------------------------------------------------------------------

    if hasattr(message, "raw") and hasattr(
        message,
        "message_type",
    ):
        from .mavlink import normalize_message

        normalized = normalize_message(message)

        return message_from_dict(normalized)

    raise TypeError(
        "message must be MAVLinkMessage or dict"
    )


# ============================================================================
# PUBLIC API
# ============================================================================

__all__ = [
    "MAVLinkMessageData",
    "HeartbeatMessage",
    "GlobalPositionMessage",
    "GPSRawMessage",
    "AttitudeMessage",
    "SystemStatusMessage",
    "BatteryStatusMessage",
    "VFRHUDMessage",
    "HomePositionMessage",
    "StatusTextMessage",
    "message_from_dict",
    "message_from_mavlink",
]