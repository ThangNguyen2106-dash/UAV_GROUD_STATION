from typing import Optional

from .Telemetry_Data import TelemetryData


class TelemetryParser:
    """Convert MAVLink messages into the protocol-independent TelemetryData."""

    def __init__(self):
        self.data = TelemetryData()

    @staticmethod
    def _mode_name(message) -> Optional[str]:
        try:
            # pymavlink exposes mode_string() on many dialect connections.
            return message.mode_string()
        except Exception:
            return None

    @staticmethod
    def _armed(base_mode) -> bool:
        try:
            from pymavlink import mavutil
            return bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        except Exception:
            return False

    def feed(self, message) -> TelemetryData:
        name = message.get_type()
        self.data.touch(name)

        # Ignore MAVLink bad-data / unknown messages.
        if name in ("BAD_DATA", "UNKNOWN"):
            return self.data.copy()

        if name == "HEARTBEAT":
            self.data.system_id = getattr(message, "_header", None).srcSystem
            self.data.component_id = getattr(message, "_header", None).srcComponent
            self.data.armed = self._armed(message.base_mode)

            mode = self._mode_name(message)
            if mode:
                self.data.flight_mode = mode

        elif name == "GLOBAL_POSITION_INT":
            self.data.latitude = message.lat / 1e7
            self.data.longitude = message.lon / 1e7
            self.data.altitude_m = message.alt / 1000.0
            self.data.relative_altitude_m = message.relative_alt / 1000.0
            self.data.ground_speed_mps = (
                (message.vx ** 2 + message.vy ** 2) ** 0.5 / 100.0
            )
            self.data.climb_rate_mps = -message.vz / 100.0

            if getattr(message, "hdg", 65535) != 65535:
                self.data.heading_deg = message.hdg / 100.0

        elif name == "ATTITUDE":
            self.data.roll_deg = message.roll * 57.29577951308232
            self.data.pitch_deg = message.pitch * 57.29577951308232
            self.data.yaw_deg = message.yaw * 57.29577951308232

            if self.data.yaw_deg < 0:
                self.data.yaw_deg += 360.0

        elif name == "VFR_HUD":
            self.data.air_speed_mps = getattr(message, "airspeed", None)
            self.data.ground_speed_mps = getattr(message, "groundspeed", None)
            self.data.heading_deg = getattr(message, "heading", None)
            self.data.climb_rate_mps = getattr(message, "climb", None)
            self.data.altitude_m = getattr(message, "alt", None)

        elif name == "GPS_RAW_INT":
            self.data.fix_type = getattr(message, "fix_type", None)
            self.data.satellites = getattr(message, "satellites_visible", None)

            hdop = getattr(message, "eph", None)
            vdop = getattr(message, "epv", None)

            self.data.hdop = hdop / 100.0 if hdop is not None else None
            self.data.vdop = vdop / 100.0 if vdop is not None else None

        elif name == "SYS_STATUS":
            voltage = getattr(message, "voltage_battery", 65535)
            current = getattr(message, "current_battery", -1)
            remaining = getattr(message, "battery_remaining", -1)

            if voltage != 65535:
                self.data.battery_voltage_v = voltage / 1000.0

            if current >= 0:
                self.data.battery_current_a = current / 100.0

            if remaining >= 0:
                self.data.battery_remaining_pct = float(remaining)

        elif name == "BATTERY_STATUS":
            voltage = getattr(message, "voltages", [65535])[0]
            current = getattr(message, "current_battery", -1)
            remaining = getattr(message, "battery_remaining", -1)

            if voltage != 65535:
                self.data.battery_voltage_v = voltage / 1000.0

            if current >= 0:
                self.data.battery_current_a = current / 100.0

            if remaining >= 0:
                self.data.battery_remaining_pct = float(remaining)

        elif name == "RADIO_STATUS":
            self.data.radio_rssi = getattr(message, "rssi", None)
            self.data.radio_remrssi = getattr(message, "remrssi", None)
            self.data.radio_noise = getattr(message, "noise", None)
            self.data.radio_remnoise = getattr(message, "remnoise", None)

        return self.data.copy()
