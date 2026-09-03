import time
from dataclasses import dataclass

import serial
from serial.tools import list_ports
from pymavlink import mavutil


@dataclass
class SerialDevice:
    sysid: int
    compid: int
    mav_type: int
    autopilot: int
    port: str
    baudrate: int
    detected_at: float


class SerialDiscovery:
    """
    Phát hiện thiết bị MAVLink qua Serial.

    Không gửi ARM / TAKEOFF / LAND.
    Chỉ chờ HEARTBEAT.
    """

    DEFAULT_BAUDRATES = (
        115200,
        57600,
        921600,
    )

    def __init__(
        self,
        baudrates=None,
        heartbeat_timeout=2.0,
    ):

        self.baudrates = (
            tuple(baudrates)
            if baudrates is not None
            else self.DEFAULT_BAUDRATES
        )

        self.heartbeat_timeout = heartbeat_timeout

        self.devices = {}

        self.running = False

        self.on_device = None

    # =========================================================
    # LIST PORTS
    # =========================================================

    def list_serial_ports(self):

        ports = list_ports.comports()

        return sorted(
            ports,
            key=lambda p: p.device,
        )

    # =========================================================
    # DISCOVER
    # =========================================================

    def discover(self):

        print("=" * 60)
        print("[SERIAL DISCOVERY] START")
        print("=" * 60)

        ports = self.list_serial_ports()

        if not ports:

            print(
                "[SERIAL DISCOVERY] "
                "No serial ports found"
            )

            return []

        print(
            f"[SERIAL DISCOVERY] "
            f"Found {len(ports)} serial port(s)"
        )

        for port_info in ports:

            port = port_info.device

            print()
            print(
                f"[SERIAL] Port: {port}"
            )

            print(
                f"[SERIAL] Description: "
                f"{port_info.description}"
            )

            for baudrate in self.baudrates:

                print(
                    f"[SERIAL] Testing "
                    f"{port} @ {baudrate}"
                )

                device = self._probe_port(
                    port,
                    baudrate,
                )

                if device is None:

                    continue

                key = (
                    device.sysid,
                    device.compid,
                )

                if key in self.devices:

                    continue

                self.devices[key] = device

                print()
                print("=" * 60)
                print("[SERIAL DISCOVERY] DEVICE DETECTED")
                print("=" * 60)

                print(
                    f"SYSID     : {device.sysid}"
                )

                print(
                    f"COMPID    : {device.compid}"
                )

                print(
                    f"MAV_TYPE  : {device.mav_type}"
                )

                print(
                    f"AUTOPILOT : {device.autopilot}"
                )

                print(
                    f"PORT      : {device.port}"
                )

                print(
                    f"BAUDRATE  : {device.baudrate}"
                )

                if self.on_device:

                    self.on_device(
                        device
                    )

                # Đã tìm thấy MAVLink device
                # trên port này.
                break

        return self.get_devices()

    # =========================================================
    # PROBE PORT
    # =========================================================

    def _probe_port(
        self,
        port,
        baudrate,
    ):

        connection = None

        try:

            connection = mavutil.mavlink_connection(
                port,
                baud=baudrate,
                source_system=255,
                source_component=190,
            )

            print(
                f"[SERIAL] Waiting HEARTBEAT "
                f"{port}@{baudrate}"
            )

            heartbeat = (
                connection.wait_heartbeat(
                    timeout=self.heartbeat_timeout
                )
            )

            if heartbeat is None:

                print(
                    "[SERIAL] "
                    "No HEARTBEAT"
                )

                return None

            # =========================================================
            # MAVLINK SOURCE ID
            # =========================================================

            # Lấy ID trực tiếp từ HEARTBEAT.
            # Không sử dụng connection.target_component vì
            # target_component có thể chưa được pymavlink thiết lập.

            try:
                sysid = heartbeat.get_srcSystem()
            except Exception:
                sysid = None

            try:
                compid = heartbeat.get_srcComponent()
            except Exception:
                compid = None

            if sysid is None:
                return None

            if compid is None:
                return None

            return SerialDevice(
                sysid=sysid,
                compid=compid,
                mav_type=heartbeat.type,
                autopilot=heartbeat.autopilot,
                port=port,
                baudrate=baudrate,
                detected_at=time.time(),
            )

        except (
            serial.SerialException,
            OSError,
        ) as exc:

            print(
                f"[SERIAL] "
                f"{port}@{baudrate} "
                f"unavailable: {exc}"
            )

            return None

        except Exception as exc:

            print(
                f"[SERIAL] "
                f"{port}@{baudrate} "
                f"error: "
                f"{type(exc).__name__}: {exc}"
            )

            return None

        finally:

            if connection is not None:

                try:
                    connection.close()

                except Exception:
                    pass

    # =========================================================
    # DEVICES
    # =========================================================

    def get_devices(self):

        return list(
            self.devices.values()
        )

    def get_device(
        self,
        sysid,
        compid,
    ):

        return self.devices.get(
            (
                sysid,
                compid,
            )
        )

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        self.running = False

        print(
            "[SERIAL DISCOVERY] Stopped"
        )