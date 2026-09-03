import socket
import time
from dataclasses import dataclass


@dataclass
class DiscoveredDevice:
    sysid: int
    compid: int
    mav_type: int
    autopilot: int
    address: tuple
    detected_at: float


class UDPDiscovery:
    """
    UDP MAVLink discovery.

    Discovery chỉ có nhiệm vụ:
        - nhận MAVLink
        - phát hiện HEARTBEAT
        - xác định SYSID / COMPID
        - xác định remote UDP endpoint
    """

    def __init__(
        self,
        host="0.0.0.0",
        port=14550,
        timeout=0.5,
    ):

        self.host = host
        self.port = port
        self.timeout = timeout

        self.socket = None

        self.running = False

        self.devices = {}

        self.on_device = None

        # MAVLink parser
        from pymavlink import mavutil

        self.mavlink = mavutil.mavlink.MAVLink(
            None
        )

    # =========================================================
    # START
    # =========================================================

    def start(self):

        if self.running:
            return

        print("=" * 60)
        print("[DISCOVERY] Starting UDP discovery")
        print("=" * 60)

        print(
            f"[DISCOVERY] Listening on "
            f"{self.host}:{self.port}"
        )

        self.socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        self.socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        self.socket.bind(
            (
                self.host,
                self.port,
            )
        )

        self.socket.settimeout(
            self.timeout
        )

        self.running = True

        print(
            f"[DISCOVERY] UDP listener ready"
        )

    # =========================================================
    # POLL
    # =========================================================

    def poll(self):

        if not self.running:
            return

        try:

            data, address = self.socket.recvfrom(
                65535
            )

            self._feed_data(
                data,
                address,
            )

        except socket.timeout:

            return

        except OSError as exc:

            if self.running:

                print(
                    f"[DISCOVERY SOCKET ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

        except Exception as exc:

            print(
                f"[DISCOVERY ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

    # =========================================================
    # MAVLINK PARSER
    # =========================================================

    def _feed_data(
        self,
        data,
        address,
    ):

        for byte in data:

            try:

                message = self.mavlink.parse_char(
                    bytes([byte])
                )

                if message is None:
                    continue

                self._process_message(
                    message,
                    address,
                )

            except Exception:

                # Một byte lỗi không được làm
                # chết discovery engine.
                continue

    # =========================================================
    # PROCESS MESSAGE
    # =========================================================

    def _process_message(
        self,
        message,
        address,
    ):

        if message.get_type() != "HEARTBEAT":
            return

        sysid = message.get_srcSystem()

        compid = message.get_srcComponent()

        if sysid is None:
            return

        if compid is None:
            compid = 0

        key = (
            sysid,
            compid,
        )

        # -----------------------------------------------------
        # NEW DEVICE
        # -----------------------------------------------------

        if key not in self.devices:

            device = DiscoveredDevice(
                sysid=sysid,
                compid=compid,
                mav_type=message.type,
                autopilot=message.autopilot,
                address=address,
                detected_at=time.time(),
            )

            self.devices[key] = device

            print()
            print("=" * 60)
            print("[DISCOVERY] DEVICE DETECTED")
            print("=" * 60)

            print(
                f"SYSID     : {sysid}"
            )

            print(
                f"COMPID    : {compid}"
            )

            print(
                f"MAV_TYPE  : {message.type}"
            )

            print(
                f"AUTOPILOT : {message.autopilot}"
            )

            print(
                f"ADDRESS   : {address[0]}:{address[1]}"
            )

            if self.on_device:

                self.on_device(
                    device
                )

        else:

            # -------------------------------------------------
            # UPDATE PEER ADDRESS
            # -------------------------------------------------

            device = self.devices[key]

            device.address = address

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

        if not self.running:
            return

        print(
            "[DISCOVERY] Stopping UDP discovery..."
        )

        self.running = False

        if self.socket is not None:

            try:
                self.socket.close()

            except Exception:
                pass

        self.socket = None

        print(
            "[DISCOVERY] Discovery stopped"
        )