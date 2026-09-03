"""
RIGEL GCS - MAVLink Protocol Layer

Responsibilities
----------------
* Parse MAVLink 1.0 and MAVLink 2.0 frames received as raw bytes.
* Preserve source SYSID/COMPID from the MAVLink frame.
* Report the wire protocol version of each parsed message.
* Wrap parsed pymavlink messages in a small, transport-independent object.
* Normalize common telemetry/status messages into Python dictionaries.

This module does NOT:
* open Serial/UDP connections;
* perform discovery;
* manage connections;
* send commands, parameters, or missions;
* contain UI code.

Connection/transport ownership remains in ``core/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable, Optional

from pymavlink import mavutil


MAVLINK_V1_STX = 0xFE
MAVLINK_V2_STX = 0xFD


@dataclass(frozen=True)
class MAVLinkMessage:
    """Transport-independent wrapper around one pymavlink message."""

    raw: Any
    message_type: str
    sysid: Optional[int]
    compid: Optional[int]
    protocol_version: Optional[int]

    def to_dict(self) -> dict[str, Any]:
        """Return pymavlink's dictionary representation when available."""
        try:
            return dict(self.raw.to_dict())
        except Exception:
            return {}


class MAVLinkEngine:
    """MAVLink 1.0/2.0 byte-stream parser and message wrapper."""

    def __init__(
        self,
        dialect: str = "ardupilotmega",
        source_system: int = 255,
        source_component: int = 190,
        on_message: Optional[Callable[[MAVLinkMessage], None]] = None,
    ) -> None:
        self.dialect = str(dialect)
        self.source_system = int(source_system)
        self.source_component = int(source_component)
        self.on_message = on_message

        self._dialect_module = self._load_dialect(self.dialect)
        self._parser = self._create_parser()

        # Statistics
        self.message_count = 0
        self.byte_count = 0

        self.protocol_counts: dict[int, int] = {
            1: 0,
            2: 0,
        }

        self.message_counts: dict[str, int] = {}

        # Last parsed message
        self.last_message: Optional[MAVLinkMessage] = None

        # Last target/source identity
        self.target_system: Optional[int] = None
        self.target_component: Optional[int] = None

        # Last wire protocol version
        self._wire_version: Optional[int] = None

        # Protocol version of the frame currently being parsed.
        #
        # This is important because a MAVLink frame can be fragmented
        # across multiple feed_bytes() calls.
        self._current_frame_protocol: Optional[int] = None

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    def _create_parser(self) -> Any:
        parser = self._dialect_module.MAVLink(self._mavlink_output)
        self._configure_parser(parser)
        return parser

    def _mavlink_output(self, data: bytes) -> None:
        """Parser output hook.

        RX parsing does not transmit anything.
        """
        return None

    @staticmethod
    def _load_dialect(dialect: str) -> Any:
        """Load the requested pymavlink MAVLink 2 dialect."""
        try:
            return import_module(
                f"pymavlink.dialects.v20.{dialect}"
            )
        except (ImportError, ModuleNotFoundError) as exc:
            if dialect == "ardupilotmega":
                return mavutil.mavlink

            raise ValueError(
                f"Unsupported pymavlink dialect: {dialect!r}"
            ) from exc

    @staticmethod
    def _configure_parser(parser: Any) -> None:
        try:
            parser.robust_parsing = True
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Protocol detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_protocol_version(
        data: bytes | bytearray,
    ) -> Optional[int]:
        """Detect the first MAVLink frame marker in raw bytes.

        MAVLink 1:
            0xFE

        MAVLink 2:
            0xFD
        """
        if not data:
            return None

        for byte in bytes(data):
            if byte == MAVLINK_V1_STX:
                return 1

            if byte == MAVLINK_V2_STX:
                return 2

        return None

    @staticmethod
    def _source_ids(
        message: Any,
    ) -> tuple[Optional[int], Optional[int]]:
        try:
            sysid = message.get_srcSystem()
        except Exception:
            sysid = None

        try:
            compid = message.get_srcComponent()
        except Exception:
            compid = None

        return sysid, compid

    # ------------------------------------------------------------------
    # Feed parser
    # ------------------------------------------------------------------

    def feed_bytes(
        self,
        data: bytes | bytearray,
    ) -> int:
        """Feed raw MAVLink bytes.

        The parser is stateful and supports fragmented frames.

        Returns:
            Number of complete MAVLink messages parsed.
        """

        if not data:
            return 0

        if not isinstance(data, (bytes, bytearray)):
            raise TypeError(
                "data must be bytes or bytearray"
            )

        payload = bytes(data)

        self.byte_count += len(payload)

        parsed = 0

        for byte in payload:

            # ----------------------------------------------------------
            # Detect beginning of a new MAVLink frame
            # ----------------------------------------------------------

            if byte == MAVLINK_V1_STX:
                self._current_frame_protocol = 1

            elif byte == MAVLINK_V2_STX:
                self._current_frame_protocol = 2

            # ----------------------------------------------------------
            # Feed byte to pymavlink
            # ----------------------------------------------------------

            try:
                message = self._parser.parse_char(
                    bytes((byte,))
                )

            except Exception as exc:
                print(
                    f"[MAVLINK PARSER ERROR] {exc}"
                )
                continue

            # No complete message yet
            if message is None:
                continue

            # ----------------------------------------------------------
            # Complete frame
            # ----------------------------------------------------------

            parsed += 1

            protocol_version = (
                self._current_frame_protocol
            )

            self._handle_message(
                message,
                protocol_version=protocol_version,
            )

            # Frame completed.
            #
            # Do not carry protocol version into the next frame.
            self._current_frame_protocol = None

        return parsed

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    def _handle_message(
        self,
        message: Any,
        protocol_version: Optional[int] = None,
    ) -> MAVLinkMessage:

        message_type = message.get_type()

        sysid, compid = self._source_ids(
            message
        )

        # --------------------------------------------------------------
        # Fallback:
        #
        # In case _handle_message() is called directly by another
        # internal component, try the pymavlink header.
        # --------------------------------------------------------------

        if protocol_version not in (1, 2):

            try:
                header = getattr(
                    message,
                    "_header",
                    None,
                )

                magic = getattr(
                    header,
                    "magic",
                    None,
                )

                if magic == MAVLINK_V1_STX:
                    protocol_version = 1

                elif magic == MAVLINK_V2_STX:
                    protocol_version = 2

            except Exception:
                protocol_version = None

        # --------------------------------------------------------------
        # Statistics
        # --------------------------------------------------------------

        if protocol_version in (1, 2):

            self.protocol_counts[
                protocol_version
            ] += 1

            self._wire_version = protocol_version

        # --------------------------------------------------------------
        # Wrapper
        # --------------------------------------------------------------

        wrapped = MAVLinkMessage(
            raw=message,
            message_type=message_type,
            sysid=sysid,
            compid=compid,
            protocol_version=protocol_version,
        )

        # --------------------------------------------------------------
        # Message statistics
        # --------------------------------------------------------------

        self.message_count += 1

        self.message_counts[
            message_type
        ] = (
            self.message_counts.get(
                message_type,
                0,
            )
            + 1
        )

        self.last_message = wrapped

        # --------------------------------------------------------------
        # HEARTBEAT identity
        # --------------------------------------------------------------

        if message_type == "HEARTBEAT":

            self.target_system = sysid

            self.target_component = compid

        # --------------------------------------------------------------
        # Callback
        # --------------------------------------------------------------

        if self.on_message is not None:

            try:
                self.on_message(
                    wrapped
                )

            except Exception as exc:

                print(
                    "[MAVLINK CALLBACK ERROR] "
                    f"{exc}"
                )

        return wrapped

    # ------------------------------------------------------------------
    # Public information
    # ------------------------------------------------------------------

    def get_protocol_version(
        self,
    ) -> Optional[int]:
        """Return protocol version of last parsed message."""
        return self._wire_version

    def get_statistics(self) -> dict[str, Any]:
        return {
            "dialect": self.dialect,

            "message_count":
                self.message_count,

            "byte_count":
                self.byte_count,

            "protocol_counts":
                dict(self.protocol_counts),

            "message_counts":
                dict(self.message_counts),

            "target_system":
                self.target_system,

            "target_component":
                self.target_component,

            "last_protocol_version":
                self._wire_version,
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset parser state and statistics."""

        self._parser = self._create_parser()

        self.message_count = 0
        self.byte_count = 0

        self.protocol_counts = {
            1: 0,
            2: 0,
        }

        self.message_counts = {}

        self.last_message = None

        self.target_system = None
        self.target_component = None

        self._wire_version = None

        self._current_frame_protocol = None

# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _scaled(value: Any, factor: float) -> Optional[float]:
    """Scale a numeric MAVLink field without raising on missing values."""
    if value is None:
        return None
    try:
        return float(value) / factor
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_message(message: MAVLinkMessage) -> dict[str, Any]:
    """Normalize common MAVLink messages into GCS-friendly dictionaries.

    Coordinates are degrees; GLOBAL_POSITION_INT altitude fields are meters;
    velocity fields are m/s; ATTITUDE angles are radians; battery voltage is V.
    ``None`` is returned when an optional/unavailable field cannot be decoded.
    """
    raw = message.raw

    result: dict[str, Any] = {
        "message_type": message.message_type,
        "sysid": message.sysid,
        "compid": message.compid,
        "protocol_version": message.protocol_version,
    }

    if message.message_type == "HEARTBEAT":
        result.update({
            "mav_type": getattr(raw, "type", None),
            "autopilot": getattr(raw, "autopilot", None),
            "base_mode": getattr(raw, "base_mode", None),
            "custom_mode": getattr(raw, "custom_mode", None),
            "system_status": getattr(raw, "system_status", None),
        })

    elif message.message_type == "GLOBAL_POSITION_INT":
        hdg = _int_or_none(getattr(raw, "hdg", None))
        result.update({
            "latitude": _scaled(getattr(raw, "lat", None), 1e7),
            "longitude": _scaled(getattr(raw, "lon", None), 1e7),
            "altitude": _scaled(getattr(raw, "alt", None), 1000.0),
            "relative_altitude": _scaled(
                getattr(raw, "relative_alt", None), 1000.0
            ),
            "velocity_x": _scaled(getattr(raw, "vx", None), 100.0),
            "velocity_y": _scaled(getattr(raw, "vy", None), 100.0),
            "velocity_z": _scaled(getattr(raw, "vz", None), 100.0),
            "heading": None if hdg in (None, 65535) else hdg / 100.0,
        })

    elif message.message_type == "GPS_RAW_INT":
        result.update({
            "latitude": _scaled(getattr(raw, "lat", None), 1e7),
            "longitude": _scaled(getattr(raw, "lon", None), 1e7),
            "altitude": _scaled(getattr(raw, "alt", None), 1000.0),
            "fix_type": getattr(raw, "fix_type", None),
            "satellites_visible": getattr(raw, "satellites_visible", None),
        })

    elif message.message_type == "ATTITUDE":
        result.update({
            "roll": getattr(raw, "roll", None),
            "pitch": getattr(raw, "pitch", None),
            "yaw": getattr(raw, "yaw", None),
            "roll_speed": getattr(raw, "rollspeed", None),
            "pitch_speed": getattr(raw, "pitchspeed", None),
            "yaw_speed": getattr(raw, "yawspeed", None),
        })

    elif message.message_type == "SYS_STATUS":
        voltage = _int_or_none(getattr(raw, "voltage_battery", None))
        current = _int_or_none(getattr(raw, "current_battery", None))
        result.update({
            "voltage_battery": (
                None if voltage in (None, 65535) else voltage / 1000.0
            ),
            "current_battery": (
                None if current is None or current < 0 else current / 100.0
            ),
            "battery_remaining": getattr(raw, "battery_remaining", None),
            "load": getattr(raw, "load", None),
        })

    elif message.message_type == "BATTERY_STATUS":
        result.update({
            "battery_id": getattr(raw, "id", None),
            "battery_remaining": getattr(raw, "battery_remaining", None),
            "current_consumed": getattr(raw, "current_consumed", None),
            "energy_consumed": getattr(raw, "energy_consumed", None),
        })

    elif message.message_type == "PARAM_VALUE":
        result.update({
            "param_id": getattr(raw, "param_id", None),
            "param_value": getattr(raw, "param_value", None),
            "param_type": getattr(raw, "param_type", None),
            "param_count": getattr(raw, "param_count", None),
            "param_index": getattr(raw, "param_index", None),
        })

    return result


__all__ = [
    "MAVLINK_V1_STX",
    "MAVLINK_V2_STX",
    "MAVLinkMessage",
    "MAVLinkEngine",
    "normalize_message",
]
