"""
RIGEL GCS
UDP Transport Layer

Responsible only for UDP transport.
MAVLink protocol handling belongs to MAVLinkSession.

Current simulator configuration:

    Simulator TX -> GCS RX
    127.0.0.1:14550

    GCS TX -> Simulator RX
    127.0.0.1:14560
"""

from __future__ import annotations

import socket
import threading
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class UDPConfig:
    """UDP transport configuration."""

    rx_host: str = "0.0.0.0"
    rx_port: int = 14550

    tx_host: str = "127.0.0.1"
    tx_port: int = 14551

    recv_buffer_size: int = 65535
    timeout: float = 0.5


class UDPTransport:
    """
    Low-level UDP transport.

    This class does NOT parse MAVLink.

    Responsibilities:
        - Create RX socket
        - Create TX socket
        - Receive raw bytes
        - Send raw bytes
        - Track peer address
        - Start/stop receive thread
    """

    def __init__(
        self,
        config: Optional[UDPConfig] = None,
        on_data: Optional[Callable[[bytes, tuple], None]] = None,
    ):
        self.config = config or UDPConfig()

        self.on_data = on_data

        self._rx_socket: Optional[socket.socket] = None
        self._tx_socket: Optional[socket.socket] = None

        self._rx_thread: Optional[threading.Thread] = None
        self._running = False

        self._last_rx_address: Optional[tuple] = None

        self._rx_packets = 0
        self._tx_packets = 0

        self._rx_bytes = 0
        self._tx_bytes = 0

        self._lock = threading.Lock()

    # ==========================================================
    # PROPERTIES
    # ==========================================================

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_rx_address(self) -> Optional[tuple]:
        return self._last_rx_address

    @property
    def rx_packets(self) -> int:
        return self._rx_packets

    @property
    def tx_packets(self) -> int:
        return self._tx_packets

    @property
    def rx_bytes(self) -> int:
        return self._rx_bytes

    @property
    def tx_bytes(self) -> int:
        return self._tx_bytes

    # ==========================================================
    # START
    # ==========================================================

    def start(self) -> None:
        """Start UDP RX/TX transport."""

        if self._running:
            print("[UDP] Transport already running")
            return

        print(
            f"[UDP] Starting transport | "
            f"RX={self.config.rx_host}:{self.config.rx_port} "
            f"TX={self.config.tx_host}:{self.config.tx_port}"
        )

        self._create_rx_socket()
        self._create_tx_socket()

        self._running = True

        self._rx_thread = threading.Thread(
            target=self._receive_loop,
            name="RIGEL-UDP-RX",
            daemon=True,
        )

        self._rx_thread.start()

        print("[UDP] Transport started")

    # ==========================================================
    # SOCKET CREATION
    # ==========================================================

    def _create_rx_socket(self) -> None:
        """Create UDP receive socket."""
        self._rx_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        self._rx_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        # On Windows: disable SIO_UDP_CONNRESET so ICMP Port Unreachable does not crash recvfrom with WinError 10054
        if hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self._rx_socket.ioctl(socket.SIO_UDP_CONNRESET, False)
            except Exception:
                pass

        self._rx_socket.settimeout(
            self.config.timeout
        )

        self._rx_socket.bind(
            (
                self.config.rx_host,
                self.config.rx_port,
            )
        )

        print(
            f"[UDP RX] Bound to "
            f"{self.config.rx_host}:{self.config.rx_port}"
        )

    def _create_tx_socket(self) -> None:
        """Create UDP transmit socket."""
        self._tx_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        if hasattr(socket, "SIO_UDP_CONNRESET"):
            try:
                self._tx_socket.ioctl(socket.SIO_UDP_CONNRESET, False)
            except Exception:
                pass

        print(
            f"[UDP TX] Ready -> "
            f"{self.config.tx_host}:{self.config.tx_port}"
        )

    # ==========================================================
    # RECEIVE
    # ==========================================================

    def _receive_loop(self) -> None:
        """Background UDP receive loop."""
        print("[UDP RX] Receive thread started")

        while self._running:
            if self._rx_socket is None:
                break

            try:
                data, address = self._rx_socket.recvfrom(
                    self.config.recv_buffer_size
                )
            except socket.timeout:
                continue
            except ConnectionResetError:
                # Windows 10054 ICMP port unreachable is expected in UDP when simulator shifts ports - ignore and keep receiving!
                continue
            except OSError as exc:
                if not self._running:
                    break
                # Do not kill thread on transient OS errors
                continue
            except Exception as exc:
                if not self._running:
                    break
                print(f"[UDP RX ERROR] {exc}")
                continue

            if not data:
                continue

            with self._lock:
                self._last_rx_address = address
                self._rx_packets += 1
                self._rx_bytes += len(data)

            if self.on_data is not None:
                try:
                    self.on_data(data, address)
                except Exception as exc:
                    print(f"[UDP CALLBACK ERROR] {exc}")

    # ==========================================================
    # SEND
    # ==========================================================

    def send(
        self,
        data: bytes,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ) -> bool:
        """
        Send raw UDP bytes.
        Uses the primary bound RX socket or TX socket to ensure NAT and return-path compatibility with simulators.
        """
        if not self._running:
            return False

        sock = self._rx_socket or self._tx_socket
        if sock is None:
            return False

        if not isinstance(data, bytes):
            raise TypeError("UDPTransport.send() requires bytes")

        success = False

        # 1. If we have the exact peer address from incoming packets, send directly through the same bound socket!
        if host is None and port is None and self._last_rx_address is not None:
            try:
                sent = sock.sendto(data, self._last_rx_address)
                if sent == len(data):
                    success = True
            except OSError:
                pass

        # 2. Also send to configured TX endpoint
        target_host = host or self.config.tx_host
        target_port = port or self.config.tx_port

        if (target_host, target_port) != self._last_rx_address:
            try:
                sent = sock.sendto(data, (target_host, target_port))
                if sent == len(data):
                    success = True
            except OSError:
                pass

        if success:
            with self._lock:
                self._tx_packets += 1
                self._tx_bytes += len(data)

        return success

    # ==========================================================
    # STOP
    # ==========================================================

    def stop(self) -> None:
        """Stop UDP transport."""

        if not self._running:
            return

        print("[UDP] Stopping transport...")

        self._running = False

        if self._rx_socket is not None:

            try:
                self._rx_socket.close()

            except Exception:
                pass

            self._rx_socket = None

        if self._tx_socket is not None:

            try:
                self._tx_socket.close()

            except Exception:
                pass

            self._tx_socket = None

        if (
            self._rx_thread is not None
            and self._rx_thread.is_alive()
            and threading.current_thread()
            != self._rx_thread
        ):
            self._rx_thread.join(timeout=1.0)

        self._rx_thread = None

        print("[UDP] Transport stopped")

    # ==========================================================
    # STATISTICS
    # ==========================================================

    def statistics(self) -> dict:

        with self._lock:

            return {
                "running": self._running,
                "rx_packets": self._rx_packets,
                "tx_packets": self._tx_packets,
                "rx_bytes": self._rx_bytes,
                "tx_bytes": self._tx_bytes,
                "last_rx_address": self._last_rx_address,
            }

    # ==========================================================
    # CONTEXT MANAGER
    # ==========================================================

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()