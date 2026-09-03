import time
import threading

from .discovery.udp_discovery import UDPDiscovery
from .device_registry import DeviceRegistry


class AutoDiscoveryManager:
    """
    Quản lý quá trình AUTO DISCOVERY.

    Hiện tại:
        UDP discovery

    Sau này:
        UDP
        SERIAL
        RADIO
        TCP
        4G/5G
    """

    def __init__(
        self,
        registry=None,
        udp_host="0.0.0.0",
        udp_port=14550,
    ):

        self.registry = (
            registry
            if registry is not None
            else DeviceRegistry()
        )

        self.udp_host = udp_host
        self.udp_port = udp_port

        self.udp_discovery = None

        self.running = False

        self.thread = None

        self.on_device = None

    # =========================================================
    # START
    # =========================================================

    def start(self):

        if self.running:

            print(
                "[AUTO DISCOVERY] Already running"
            )

            return

        print("=" * 60)
        print("[AUTO DISCOVERY] START")
        print("=" * 60)

        self.udp_discovery = UDPDiscovery(
            host=self.udp_host,
            port=self.udp_port,
        )

        self.udp_discovery.on_device = (
            self._on_udp_device
        )

        self.udp_discovery.start()

        self.running = True

        self.thread = threading.Thread(
            target=self._worker,
            name="AutoDiscovery",
            daemon=True,
        )

        self.thread.start()

        print(
            "[AUTO DISCOVERY] Running"
        )

    # =========================================================
    # WORKER
    # =========================================================

    def _worker(self):

        while self.running:

            try:

                if self.udp_discovery is not None:

                    self.udp_discovery.poll()

            except Exception as exc:

                print(
                    f"[AUTO DISCOVERY ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )

            time.sleep(0.01)

    # =========================================================
    # UDP DEVICE
    # =========================================================

    def _on_udp_device(
        self,
        discovered_device,
    ):

        device = self.registry.get_or_create(
            sysid=discovered_device.sysid,
            compid=discovered_device.compid,

            transport="UDP",

            rx_endpoint=(
                f"{self.udp_host}:{self.udp_port}"
            ),

            tx_endpoint=(
                f"{discovered_device.address[0]}:"
                f"{discovered_device.address[1]}"
                if discovered_device.address
                else None
            ),
        )

        device.mav_type = (
            discovered_device.mav_type
        )

        device.autopilot = (
            discovered_device.autopilot
        )

        device.connected = True

        device.last_heartbeat = time.monotonic()

        print()
        print(
            "[AUTO DISCOVERY] Device registered"
        )

        print(
            f"SYSID={device.sysid}"
        )

        print(
            f"COMPID={device.compid}"
        )

        print(
            f"TRANSPORT={device.transport}"
        )

        print(
            f"RX={device.rx_endpoint}"
        )

        print(
            f"TX={device.tx_endpoint}"
        )

        if self.on_device:

            self.on_device(
                device
            )

    # =========================================================
    # DEVICES
    # =========================================================

    def get_devices(self):

        return self.registry.all()

    def get_device(
        self,
        sysid,
        compid,
    ):

        return self.registry.get(
            sysid,
            compid,
        )

    def device_count(self):

        return self.registry.count()

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        if not self.running:

            return

        print(
            "[AUTO DISCOVERY] Stopping..."
        )

        self.running = False

        if self.udp_discovery is not None:

            self.udp_discovery.stop()

        if self.thread is not None:

            self.thread.join(
                timeout=2.0
            )

        self.thread = None

        self.udp_discovery = None

        print(
            "[AUTO DISCOVERY] Stopped"
        )