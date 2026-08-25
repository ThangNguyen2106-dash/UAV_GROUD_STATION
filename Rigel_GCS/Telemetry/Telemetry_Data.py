from dataclasses import dataclass, field
from time import time
from typing import Optional


@dataclass
class TelemetryData:
    """Latest normalized UAV telemetry state.

    Values are intentionally protocol-independent so the UI does not need
    to know about MAVLink message names or serial transport details.
    """

    timestamp: float = field(default_factory=time)

    # Vehicle state
    system_id: Optional[int] = None
    component_id: Optional[int] = None
    armed: Optional[bool] = None
    flight_mode: Optional[str] = None

    # Position
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    relative_altitude_m: Optional[float] = None
    heading_deg: Optional[float] = None

    # Motion / attitude
    ground_speed_mps: Optional[float] = None
    air_speed_mps: Optional[float] = None
    climb_rate_mps: Optional[float] = None
    pitch_deg: Optional[float] = None
    roll_deg: Optional[float] = None
    yaw_deg: Optional[float] = None

    # GPS
    satellites: Optional[int] = None
    fix_type: Optional[int] = None
    hdop: Optional[float] = None
    vdop: Optional[float] = None

    # Battery
    battery_voltage_v: Optional[float] = None
    battery_current_a: Optional[float] = None
    battery_remaining_pct: Optional[float] = None

    # Radio link
    radio_rssi: Optional[int] = None
    radio_remrssi: Optional[int] = None
    radio_noise: Optional[int] = None
    radio_remnoise: Optional[int] = None

    # Protocol diagnostics
    messages_received: int = 0
    last_message: Optional[str] = None
    last_message_timestamp: Optional[float] = None

    def touch(self, message_name: str):
        now = time()
        self.timestamp = now
        self.last_message = message_name
        self.last_message_timestamp = now
        self.messages_received += 1

    def copy(self):
        return TelemetryData(**self.__dict__)
