import threading
from typing import Callable, Optional

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

try:
    from pymavlink import mavutil
except ImportError:
    mavutil = None

from .Telemetry_Parser import TelemetryParser
from .Telemetry_Data import TelemetryData


class TelemetryManager:
    """Owns the serial/MAVLink telemetry connection.

    Threading rule:
        Serial/MAVLink reading happens in a worker thread.
        UI callbacks are therefore never executed from the serial thread
        unless the caller explicitly marshals them with Tk.after().
    """

    DEFAULT_BAUDRATES = (
        9600,
        19200,
        38400,
        57600,
        115200,
        230400,
        460800,
        921600,
    )

    def __init__(
        self,
        on_data: Optional[Callable[[TelemetryData], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.on_data = on_data or (lambda data: None)
        self.on_status = on_status or (lambda status: None)
        self.on_error = on_error or (lambda error: None)

        self.port: Optional[str] = None
        self.baudrate: int = 57600

        self._connection = None
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._parser = TelemetryParser()
        self._connected = False

    # =========================================================
    # PORT DISCOVERY
    # =========================================================

    @staticmethod
    def list_ports():
        """Return available serial ports as dictionaries."""
        if list_ports is None:
            return []

        result = []
        for port in list_ports.comports():
            result.append({
                "device": port.device,
                "description": port.description or port.device,
                "hwid": port.hwid or "",
            })

        return result

    @classmethod
    def port_names(cls):
        return [item["device"] for item in cls.list_ports()]

    @classmethod
    def baudrates(cls):
        return cls.DEFAULT_BAUDRATES

    # =========================================================
    # CONNECTION
    # =========================================================

    def connect(self, port: str, baudrate: int) -> bool:
        if not port:
            self.on_error("Chưa chọn COM PORT.")
            return False

        try:
            baudrate = int(baudrate)
        except (TypeError, ValueError):
            self.on_error("Baudrate không hợp lệ.")
            return False

        self.disconnect()

        if serial is None:
            self.on_error(
                "Thiếu pyserial. Cài bằng: pip install pyserial"
            )
            return False

        if mavutil is None:
            self.on_error(
                "Thiếu pymavlink. Cài bằng: pip install pymavlink"
            )
            return False

        try:
            # Explicit serial device + baudrate. No UDP/TCP auto-detection.
            connection = mavutil.mavlink_connection(
                port,
                baud=baudrate,
                autoreconnect=True,
                source_system=255,
                source_component=190,
            )

            self._connection = connection
            self.port = port
            self.baudrate = baudrate
            self._parser = TelemetryParser()

            self._stop_event.clear()
            self._connected = True

            self._thread = threading.Thread(
                target=self._receive_loop,
                name="RIGEL-Telemetry",
                daemon=True,
            )
            self._thread.start()

            self.on_status(
                f"CONNECTED: {port} @ {baudrate}"
            )
            return True

        except Exception as exc:
            self._connection = None
            self._connected = False
            self.on_error(
                f"Không thể mở {port} @ {baudrate}: {exc}"
            )
            return False

    def disconnect(self):
        self._stop_event.set()

        thread = self._thread
        self._thread = None

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

        connection = self._connection
        self._connection = None
        self._connected = False

        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

        if self.port:
            self.on_status(f"DISCONNECTED: {self.port}")

    def is_connected(self) -> bool:
        return self._connected and self._connection is not None

    # =========================================================
    # RECEIVE
    # =========================================================

    def _receive_loop(self):
        while not self._stop_event.is_set():
            connection = self._connection
            if connection is None:
                break

            try:
                message = connection.recv_match(
                    blocking=True,
                    timeout=1.0,
                )

                if message is None:
                    continue

                data = self._parser.feed(message)
                self.on_data(data)

            except Exception as exc:
                if self._stop_event.is_set():
                    break

                self._connected = False
                self.on_error(
                    f"Telemetry receive error: {exc}"
                )
                break

        self._connected = False

    def close(self):
        self.disconnect()
