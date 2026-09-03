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
    ):
        self.source_system = source_system
        self.source_component = source_component
        self.dialect = dialect

        self.on_message = on_message
        self.on_heartbeat = on_heartbeat

        # MAVLink parser.
        #
        # We use mavlink.MAVLink directly because transport
        # is already handled by UDPTransport / SerialTransport.
        mavlink_class = mavutil.mavlink.MAVLink

        self._parser = mavlink_class(
            self._mavlink_output
        )

        self.target_system: Optional[int] = None
        self.target_component: Optional[int] = None

        self.last_heartbeat_time: Optional[float] = None

        self.message_count = 0
        self.byte_count = 0

        self._message_types = defaultdict(int)

        self._last_message = None

        self._connected = False

    # ==========================================================
    # MAVLINK OUTPUT
    # ==========================================================

    def _mavlink_output(self, data: bytes) -> None:
        """
        Dummy output callback required by MAVLink object.

        MAVLinkSession is currently RX-focused.
        TX will be implemented in a later step.
        """

    # ==========================================================
    # RECEIVE
    # ==========================================================

    def feed_bytes(self, data: bytes) -> int:
        """
        Feed raw MAVLink bytes into the parser.

        Returns:
            Number of MAVLink messages parsed.
        """

        if not data:
            return 0

        if not isinstance(data, bytes):
            raise TypeError(
                "MAVLinkSession.feed_bytes() requires bytes"
            )

        self.byte_count += len(data)

        parsed = 0

        for byte in data:

            try:
                message = self._parser.parse_char(
                    bytes([byte])
                )

            except Exception as exc:
                print(
                    f"[MAVLINK PARSE ERROR] {exc}"
                )
                continue

            if message is None:
                continue

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

        if self.last_heartbeat_time is None:
            return None

        return (
            time.monotonic()
            - self.last_heartbeat_time
        )

    def heartbeat_alive(
        self,
        timeout: float = 3.0,
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