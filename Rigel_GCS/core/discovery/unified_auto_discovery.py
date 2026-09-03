from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional
import threading
import time

from ..device import MAVLinkDevice
from ..device_registry import DeviceRegistry
from .udp_discovery import UDPDiscovery
from .serial_discovery import SerialDiscovery


@dataclass
class DiscoveryResult:
    """
    Kết quả discovery tổng hợp.
    """
    devices: List[MAVLinkDevice] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    @property
    def count(self) -> int:
        return len(self.devices)

    @property
    def elapsed(self) -> float:
        end = self.finished_at or time.time()
        return end - self.started_at


class UnifiedAutoDiscovery:
    """
    Unified Auto Discovery cho RIGEL GCS.

    Hiện tại:
        - UDP
        - Serial

    Sau này có thể mở rộng:
        - TCP
        - Telemetry Radio
        - 4G/5G
    """

    def __init__(
        self,
        udp_host: str = "0.0.0.0",
        udp_port: int = 14550,
        serial_baudrates=(115200, 57600, 921600),
        serial_timeout: float = 2.0,
    ):
        self.udp_host = udp_host
        self.udp_port = udp_port

        self.serial_baudrates = serial_baudrates
        self.serial_timeout = serial_timeout

        self.registry = DeviceRegistry()

        self.udp_discovery = UDPDiscovery(
            host=self.udp_host,
            port=self.udp_port,
        )

        self.serial_discovery = SerialDiscovery(
            baudrates=self.serial_baudrates,
            heartbeat_timeout=self.serial_timeout,
        )

        self.on_device: Optional[Callable[[MAVLinkDevice], None]] = None

        self._lock = threading.Lock()
        self._running = False

    # =========================================================
    # CALLBACK
    # =========================================================
    def _on_udp_device(self, device):
        """
        Nhận thiết bị từ UDP Discovery.
        """

        mav_device = self.registry.get_or_create(
            device.sysid,
            device.compid,
            transport="UDP",
            rx_endpoint=f"{self.udp_host}:{self.udp_port}",
            tx_endpoint=f"{device.address[0]}:{device.address[1]}",
        )

        # Cập nhật thông tin thiết bị sau khi registry tạo object
        mav_device.mav_type = device.mav_type
        mav_device.autopilot = device.autopilot
        mav_device.rx_endpoint = f"{self.udp_host}:{self.udp_port}"
        mav_device.tx_endpoint = (
            f"{device.address[0]}:{device.address[1]}"
        )

        mav_device.connected = True
        mav_device.last_heartbeat = time.monotonic()

        if self.on_device:
            self.on_device(mav_device)

    def _on_serial_device(self, device):
        """
        Nhận thiết bị từ Serial Discovery.
        """

        mav_device = self.registry.get_or_create(
            device.sysid,
            device.compid,
            transport="SERIAL",
            rx_endpoint=device.port,
            tx_endpoint=f"{device.port}@{device.baudrate}",
        )

        # Cập nhật thông tin thiết bị
        mav_device.mav_type = device.mav_type
        mav_device.autopilot = device.autopilot
        mav_device.rx_endpoint = device.port
        mav_device.tx_endpoint = (
            f"{device.port}@{device.baudrate}"
        )

        mav_device.connected = True
        mav_device.last_heartbeat = time.monotonic()

        if self.on_device:
            self.on_device(mav_device)

    # =========================================================
    # DISCOVERY
    # =========================================================

    def discover_udp(self, timeout: float = 3.0):
        """
        Discovery UDP trong một khoảng thời gian.
        """

        self.udp_discovery.on_device = self._on_udp_device

        self.udp_discovery.start()

        deadline = time.time() + timeout

        try:
            while time.time() < deadline:
                # UDPDiscovery is poll-driven; without polling no UDP
                # packet is consumed and therefore no vehicle is detected.
                self.udp_discovery.poll()
                time.sleep(0.005)
        finally:
            self.udp_discovery.stop()

    def discover_serial(self):
        """
        Discovery toàn bộ COM port.
        """

        self.serial_discovery.on_device = self._on_serial_device

        self.serial_discovery.discover()

    def discover(
        self,
        udp: bool = True,
        serial: bool = True,
        udp_timeout: float = 3.0,
    ) -> DiscoveryResult:
        """
        API chính.

        Ví dụ:

            result = discovery.discover()

        hoặc:

            result = discovery.discover(
                udp=True,
                serial=False,
            )
        """

        with self._lock:
            if self._running:
                raise RuntimeError(
                    "Unified Auto Discovery is already running"
                )

            self._running = True

        result = DiscoveryResult()

        try:
            print()
            print("=" * 60)
            print("       RIGEL GCS - UNIFIED AUTO DISCOVERY")
            print("=" * 60)

            # -------------------------------------------------
            # UDP
            # -------------------------------------------------

            if udp:
                print()
                print("[AUTO] Starting UDP discovery...")
                self.discover_udp(timeout=udp_timeout)
                print("[AUTO] UDP discovery finished")

            # -------------------------------------------------
            # SERIAL
            # -------------------------------------------------

            if serial:
                print()
                print("[AUTO] Starting Serial discovery...")
                self.discover_serial()
                print("[AUTO] Serial discovery finished")

            # -------------------------------------------------
            # RESULT
            # -------------------------------------------------

            result.devices = self.registry.all()
            result.finished_at = time.time()

            print()
            print("=" * 60)
            print("       UNIFIED DISCOVERY RESULT")
            print("=" * 60)

            if not result.devices:
                print("[AUTO] No MAVLink devices detected")
            else:
                for index, device in enumerate(result.devices, start=1):
                    print()
                    print(f"[DEVICE {index}]")
                    print(f"SYSID      : {device.sysid}")
                    print(f"COMPID     : {device.compid}")
                    print(f"MAV_TYPE   : {device.mav_type}")
                    print(f"AUTOPILOT  : {device.autopilot}")
                    print(f"TRANSPORT  : {device.transport}")
                    print(f"RX         : {device.rx_endpoint}")
                    print(f"TX         : {device.tx_endpoint}")
                    print(f"CONNECTED  : {device.connected}")

            print()
            print(f"[AUTO] Devices found : {result.count}")
            print(f"[AUTO] Elapsed        : {result.elapsed:.2f}s")

            return result

        finally:
            with self._lock:
                self._running = False

    # =========================================================
    # DEVICE ACCESS
    # =========================================================

    def get_devices(self):
        return self.registry.all()

    def get_device(self, sysid: int, compid: int, transport: str | None = None):
        return self.registry.get(sysid, compid, transport)

    def device_count(self) -> int:
        return self.registry.count()

    def clear(self):
        self.registry.clear()

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):
        self.udp_discovery.stop()
        self.serial_discovery.stop()

        with self._lock:
            self._running = False