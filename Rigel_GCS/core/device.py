"""
RIGEL GCS - MAVLink Device

Represents a discovered MAVLink vehicle/device.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MAVLinkDevice:

    sysid: int
    compid: int

    mav_type: Optional[int] = None
    autopilot: Optional[int] = None

    transport: Optional[str] = None

    rx_endpoint: Optional[str] = None
    tx_endpoint: Optional[str] = None

    connected: bool = False

    last_heartbeat: Optional[float] = None

    message_counts: dict = field(default_factory=dict)

    def update_heartbeat(self, message) -> None:

        self.mav_type = getattr(
            message,
            "type",
            self.mav_type,
        )

        self.autopilot = getattr(
            message,
            "autopilot",
            self.autopilot,
        )

        self.connected = True

        self.last_heartbeat = time.monotonic()

        self.increment_message(
            "HEARTBEAT"
        )

    def update_message(self, message) -> None:

        message_type = message.get_type()

        self.increment_message(
            message_type
        )

    def increment_message(
        self,
        message_type: str,
    ) -> None:

        self.message_counts[message_type] = (
            self.message_counts.get(
                message_type,
                0,
            ) + 1
        )

    def heartbeat_alive(
        self,
        timeout: float = 3.0,
    ) -> bool:

        if self.last_heartbeat is None:
            return False

        return (
            time.monotonic()
            - self.last_heartbeat
        ) <= timeout

    def disconnect(self) -> None:

        self.connected = False

    def info(self) -> dict:

        return {
            "sysid": self.sysid,
            "compid": self.compid,
            "mav_type": self.mav_type,
            "autopilot": self.autopilot,
            "transport": self.transport,
            "rx_endpoint": self.rx_endpoint,
            "tx_endpoint": self.tx_endpoint,
            "connected": self.connected,
            "heartbeat_alive":
                self.heartbeat_alive(),
            "message_counts":
                dict(self.message_counts),
        }