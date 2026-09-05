from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from .connection_state import ConnectionState
from .device_registry import DeviceRegistry
from .mavlink_session import MAVLinkSession
from .transports.udp_transport import UDPConfig, UDPTransport
from .transports.serial_transport import SerialTransport
from ..mavlink.telemetry import TelemetryManager


@dataclass
class _Link:
    key: tuple
    kind: str
    transport: object
    session: MAVLinkSession
    heartbeat_event: threading.Event = field(default_factory=threading.Event)
    thread: Optional[threading.Thread] = None
    monitor_thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    ready: bool = False
    target_devices: set = field(default_factory=set)


class ConnectionManager:
    """Multi-link MAVLink connection engine.

    A GCS must not be limited to one vehicle. One UDP link can receive
    multiple SYSID/COMPID vehicles, while Serial links are kept independently
    per COM port. Registry identity is (transport, SYSID, COMPID).
    """

    def __init__(self, heartbeat_timeout=3.0, link_lost_timeout=3.0):
        self.registry = DeviceRegistry()
        self.telemetry = TelemetryManager(heartbeat_timeout=heartbeat_timeout)
        self.heartbeat_timeout = heartbeat_timeout
        self.link_lost_timeout = link_lost_timeout
        self.state = ConnectionState.DISCONNECTED
        self.connected = False
        self.connection_type = None  # backward-compatible: last/primary link
        self.transport = None         # backward-compatible: last/primary link
        self.session = None           # backward-compatible: last/primary link

        self.on_state_changed: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_device: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        self._links = {}
        self._lock = threading.RLock()

        # Devices that have already triggered on_device callback.
        # Identity is transport-aware: (transport, sysid, compid)
        self._notified_devices = set()

    # ---------------------------------------------------------
    # State
    # ---------------------------------------------------------
    def _refresh_global_state(self):
        with self._lock:
            links = list(self._links.values())
            ready = any(link.ready for link in links)
            active = bool(links)
            self.connected = ready
            if ready:
                new_state = ConnectionState.READY
            elif active:
                new_state = ConnectionState.CONNECTING
            else:
                new_state = ConnectionState.DISCONNECTED
            changed = new_state != self.state
            self.state = new_state
        if changed:
            print(f"[CONNECTION STATE] {new_state.value}")
            if self.on_state_changed:
                try:
                    self.on_state_changed(new_state)
                except Exception as e:
                    print(f"[STATE CALLBACK ERROR] {e}")

    def _set_error(self, exc):
        print(f"[CONNECTION ERROR] {type(exc).__name__}: {exc}")
        if self.on_error:
            try:
                self.on_error(exc)
            except Exception:
                pass

    # ---------------------------------------------------------
    # Connect
    # ---------------------------------------------------------
    def connect_udp(self, rx_host='0.0.0.0', rx_port=14550,
                    tx_host='127.0.0.1', tx_port=14560,
                    heartbeat_timeout=None, wait=False):
        cfg = UDPConfig(rx_host=rx_host, rx_port=rx_port,
                        tx_host=tx_host, tx_port=tx_port)
        key = ('UDP', cfg.rx_host, int(cfg.rx_port), cfg.tx_host, int(cfg.tx_port))
        return self._start_link('UDP', key, cfg, heartbeat_timeout, wait)

    def connect_serial(self, port, baudrate=115200,
                       heartbeat_timeout=None, wait=False):
        baudrate = int(baudrate)
        key = ('SERIAL', str(port).upper(), baudrate)
        cfg = {'port': port, 'baudrate': baudrate}
        return self._start_link('SERIAL', key, cfg, heartbeat_timeout, wait)

    def _start_link(self, kind, key, cfg, timeout, wait):
        timeout = timeout or self.heartbeat_timeout
        with self._lock:
            if key in self._links:
                link = self._links[key]
                if link.ready:
                    return True
                return False

            transport = UDPTransport(cfg) if kind == 'UDP' else SerialTransport(cfg['port'], cfg['baudrate'])
            session = MAVLinkSession(
                source_system=255,
                source_component=190,
                send_raw=transport.send,
                request_telemetry=True,
            )
            link = _Link(key=key, kind=kind, transport=transport, session=session)
            self._links[key] = link
            self.connection_type = kind
            self.transport = transport
            self.session = session

            transport.on_data = lambda data, address=None, l=link: self._on_raw_data(l, data, address)
            session.on_message = lambda message, l=link: self._on_mavlink_message(l, message)
            session.on_heartbeat = lambda message, l=link: self._on_heartbeat(l, message)

            self.state = ConnectionState.CONNECTING
            print(f"[CONNECTION STATE] CONNECTING | {kind} | {key}")
            if self.on_state_changed:
                try:
                    self.on_state_changed(self.state)
                except Exception:
                    pass

        link.thread = threading.Thread(
            target=self._worker,
            args=(link, timeout),
            daemon=True,
            name=f'RIGEL-{kind}-CONNECT',
        )
        link.thread.start()

        if not wait:
            return True
        link.thread.join(timeout + 1.0)
        return link.ready

    def _worker(self, link: _Link, timeout: float):
        try:
            link.transport.start()
            print(f"[CONNECTION] {link.kind} transport started; waiting HEARTBEAT | {link.key}")
            if not link.heartbeat_event.wait(timeout):
                raise TimeoutError(f"HEARTBEAT timeout: {link.key}")
            if link.stop_event.is_set():
                return
            link.ready = True
            print(f"[CONNECTION STATE] VEHICLE_DETECTED | {link.key}")
            self._refresh_global_state()
            link.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                args=(link,), daemon=True, name=f'RIGEL-{link.kind}-MONITOR')
            link.monitor_thread.start()
        except Exception as exc:
            self._set_error(exc)
            self._remove_link(link.key, final_disconnect=False)
            self._refresh_global_state()

    # ---------------------------------------------------------
    # RX / MAVLink
    # ---------------------------------------------------------
    def _on_raw_data(self, link, data, address=None):
        try:
            link.session.feed_bytes(data)
        except Exception as exc:
            print(f"[MAVLINK RX ERROR] {type(exc).__name__}: {exc}")

    def _on_mavlink_message(self, link, message):
        sysid = message.get_srcSystem()
        compid = message.get_srcComponent()
        if sysid is None:
            return
        compid = compid if compid is not None else 0

        rx = self._get_rx_endpoint(link)
        tx = self._get_tx_endpoint(link)
        device = self.registry.get_or_create(
            sysid=sysid,
            compid=compid,
            transport=link.kind,
            rx_endpoint=rx,
            tx_endpoint=tx,
        )

        if message.get_type() == 'HEARTBEAT':
            device.update_heartbeat(message)
            link.target_devices.add((sysid, compid))
        else:
            device.update_message(message)

        # STEP 11: feed every MAVLink message into the transport-aware
        # telemetry layer. TelemetryManager keeps UDP:1:1 and SERIAL:1:1
        # as independent states even when SYSID/COMPID are identical.
        try:
            self.telemetry.update(
                message=message,
                device=device,
                transport=link.kind,
                rx_endpoint=rx,
                tx_endpoint=tx,
            )
        except Exception as exc:
            print(
                f"[TELEMETRY UPDATE ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

        if self.on_message:
            try:
                self.on_message(message, device)
            except TypeError:
                self.on_message(message)
            except Exception as exc:
                print(f"[MESSAGE CALLBACK ERROR] {exc}")
        # ------------------------------------------------------
        # DEVICE CALLBACK
        # ------------------------------------------------------
        # Only notify when a device is discovered for the first time.
        # Do NOT call on_device() for every MAVLink message.

        device_key = (link.kind, sysid, compid)

        if device_key not in self._notified_devices:

            self._notified_devices.add(device_key)

            if self.on_device:
                try:
                    self.on_device(device)
                except Exception as exc:
                    print(
                        f"[DEVICE CALLBACK ERROR] "
                        f"{type(exc).__name__}: {exc}"
                    )

    def _on_heartbeat(self, link, message):
        print(f"[MAVLINK] HEARTBEAT SYSID={message.get_srcSystem()} COMPID={message.get_srcComponent()} LINK={link.key}")
        link.heartbeat_event.set()

    # ---------------------------------------------------------
    # Monitoring
    # ---------------------------------------------------------
    def _monitor_loop(self, link):
        while not link.stop_event.wait(0.25):
            if not link.session.heartbeat_alive(self.link_lost_timeout):
                link.ready = False
                print(f"[CONNECTION STATE] LOST | {link.key}")
                self._refresh_global_state()
                break

    # ---------------------------------------------------------
    # Endpoint helpers
    # ---------------------------------------------------------
    def _get_rx_endpoint(self, link):
        if link.kind == 'UDP':
            c = link.transport.config
            return f'{c.rx_host}:{c.rx_port}'
        return link.transport.port

    def _get_tx_endpoint(self, link):
        if link.kind == 'UDP':
            c = link.transport.config
            return f'{c.tx_host}:{c.tx_port}'
        return f'{link.transport.port}@{link.transport.baudrate}'

    # ---------------------------------------------------------
    # Device / connection API
    # ---------------------------------------------------------
    def get_devices(self):
        return self.registry.all()

    def get_device(self, sysid, compid, transport=None):
        return self.registry.get(sysid, compid, transport)

    def device_count(self):
        return self.registry.count()

    def connection_count(self):
        with self._lock:
            return len(self._links)

    def is_connected(self):
        return self.connected

    def get_connections(self):
        with self._lock:
            return [
                {
                    'key': link.key,
                    'transport': link.kind,
                    'ready': link.ready,
                    'devices': sorted(link.target_devices),
                    'rx_endpoint': self._get_rx_endpoint(link),
                    'tx_endpoint': self._get_tx_endpoint(link),
                }
                for link in self._links.values()
            ]

    # ---------------------------------------------------------
    # Telemetry API
    # ---------------------------------------------------------
    def get_telemetry(self, sysid, compid, transport=None):
        """Return one TelemetryState by transport-aware identity."""
        return self.telemetry.get(
            sysid=sysid,
            compid=compid,
            transport=transport,
        )

    def get_telemetry_by_id(self, device_id):
        """Return telemetry by ID such as UDP:1:1."""
        return self.telemetry.get_by_id(device_id)

    def get_all_telemetry(self):
        """Return all telemetry states."""
        return self.telemetry.all()

    def telemetry_snapshot(self):
        """Return a snapshot of all telemetry states."""
        return self.telemetry.snapshot()

    def statistics(self):
        with self._lock:
            links = list(self._links.values())
        return {
            'state': self.state.value,
            'connected': self.connected,
            'connection_count': len(links),
            'device_count': self.device_count(),
            'telemetry_count': self.telemetry.count(),
            'telemetry': self.telemetry.snapshot(),
            'connections': [
                {
                    'key': link.key,
                    'transport': link.kind,
                    'ready': link.ready,
                    'session': link.session.statistics(),
                    'transport_stats': link.transport.statistics(),
                }
                for link in links
            ],
        }

    # ---------------------------------------------------------
    # Disconnect
    # ---------------------------------------------------------
    def _stop_transport(self, transport):
        """Stop a transport safely. Test doubles may not implement stop()."""
        stop = getattr(transport, 'stop', None)
        if not callable(stop):
            return False
        try:
            stop()
            return True
        except Exception as exc:
            print(
                f"[TRANSPORT STOP ERROR] "
                f"{type(exc).__name__}: {exc}"
            )
            return False

    def _remove_link(self, key, final_disconnect=True):
        with self._lock:
            link = self._links.pop(key, None)
        if link is None:
            return False

        link.stop_event.set()
        link.ready = False
        self._stop_transport(link.transport)
        for sysid, compid in link.target_devices:
            d = self.registry.get(sysid, compid, link.kind)
            if d:
                d.disconnect()
            try:
                self.telemetry.mark_disconnected(
                    sysid=sysid,
                    compid=compid,
                    transport=link.kind,
                )
            except Exception as exc:
                print(
                    f"[TELEMETRY DISCONNECT ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )
        try:
            link.session.reset()
        except Exception:
            pass
        self._refresh_global_state()
        return True

    def disconnect(self, transport=None, port=None):
        """Disconnect one link, or all links when no filter is supplied."""
        with self._lock:
            links = list(self._links.values())

        if transport is None and port is None:
            for link in links:
                self._remove_link(link.key)
            self.transport = None
            self.session = None
            self.connection_type = None
            self.connected = False
            self._refresh_global_state()
            print('[CONNECTION] All links disconnected')
            return True

        wanted = str(transport).upper() if transport else None
        removed = False
        for link in links:
            if wanted and link.kind != wanted:
                continue
            if port and link.kind == 'SERIAL' and str(link.transport.port).upper() != str(port).upper():
                continue
            removed = self._remove_link(link.key) or removed
        return removed

    # ---------------------------------------------------------
    # MAVLINK COMMAND HELPERS
    # ---------------------------------------------------------

    def send_command_long(
        self,
        command: int,
        param1: float = 0.0,
        param2: float = 0.0,
        param3: float = 0.0,
        param4: float = 0.0,
        param5: float = 0.0,
        param6: float = 0.0,
        param7: float = 0.0,
        target_system: int = 1,
        target_component: int = 1,
        transport: Optional[str] = None,
    ) -> bool:
        """Pack and send a MAV_CMD via COMMAND_LONG."""
        with self._lock:
            links = list(self._links.values())

        if not links:
            print("[CMD ERROR] No active connection link.")
            return False

        target_link = None
        if transport:
            for l in links:
                if l.kind.upper() == transport.upper():
                    target_link = l
                    break
        if target_link is None:
            target_link = links[0]

        try:
            msg = target_link.session._parser.command_long_encode(
                int(target_system),
                int(target_component),
                int(command),
                0,
                float(param1),
                float(param2),
                float(param3),
                float(param4),
                float(param5),
                float(param6),
                float(param7),
            )
            return target_link.session.send_message(msg)
        except Exception as exc:
            print(f"[CMD SEND ERROR] {exc}")
            return False

    def arm_disarm(
        self,
        arm: bool,
        force: bool = False,
        target_system: int = 1,
        target_component: int = 1,
        transport: Optional[str] = None,
    ) -> bool:
        """Send MAV_CMD_COMPONENT_ARM_DISARM."""
        param1 = 1.0 if arm else 0.0
        param2 = 21196.0 if force else 0.0  # 21196 = force arm/disarm in ArduPilot
        cmd = 400  # MAV_CMD_COMPONENT_ARM_DISARM
        action = "ARM" if arm else "DISARM"
        print(f"[ACTION] Sending {action} command to SYSID={target_system}")
        return self.send_command_long(
            command=cmd,
            param1=param1,
            param2=param2,
            target_system=target_system,
            target_component=target_component,
            transport=transport,
        )

    def set_mode(
        self,
        mode_name: str,
        target_system: int = 1,
        target_component: int = 1,
        transport: Optional[str] = None,
    ) -> bool:
        """Set vehicle flight mode."""
        copter_modes = {
            "STABILIZE": 0,
            "ACRO": 1,
            "ALT_HOLD": 2,
            "AUTO": 3,
            "GUIDED": 4,
            "LOITER": 5,
            "RTL": 6,
            "CIRCLE": 7,
            "LAND": 9,
            "DRIFT": 11,
            "SPORT": 13,
            "FLIP": 14,
            "AUTOTUNE": 15,
            "POSHOLD": 16,
            "BRAKE": 17,
            "THROW": 18,
            "GUIDED_NOGPS": 20,
            "SMART_RTL": 21,
        }

        mode_upper = mode_name.upper().strip()
        custom_mode = copter_modes.get(mode_upper)

        if custom_mode is None:
            print(f"[SET MODE ERROR] Unknown mode: {mode_name}")
            return False

        # MAV_CMD_DO_SET_MODE (176): param1 = MAV_MODE_FLAG_CUSTOM_MODE_ENABLED (1), param2 = custom_mode
        print(f"[ACTION] Setting mode to {mode_upper} (custom_mode={custom_mode})")
        return self.send_command_long(
            command=176,
            param1=1.0,
            param2=float(custom_mode),
            target_system=target_system,
            target_component=target_component,
            transport=transport,
        )

    def takeoff(
        self,
        altitude: float = 5.0,
        target_system: int = 1,
        target_component: int = 1,
        transport: Optional[str] = None,
    ) -> bool:
        """Send MAV_CMD_NAV_TAKEOFF (22)."""
        print(f"[ACTION] Sending TAKEOFF to alt={altitude:.1f}m")
        return self.send_command_long(
            command=22,
            param7=float(altitude),
            target_system=target_system,
            target_component=target_component,
            transport=transport,
        )

    def return_to_launch(
        self,
        target_system: int = 1,
        target_component: int = 1,
        transport: Optional[str] = None,
    ) -> bool:
        """Send MAV_CMD_NAV_RETURN_TO_LAUNCH (20) or set RTL mode."""
        print("[ACTION] Sending Return To Launch (RTL)")
        res = self.send_command_long(
            command=20,
            target_system=target_system,
            target_component=target_component,
            transport=transport,
        )
        if not res:
            res = self.set_mode("RTL", target_system, target_component, transport)
        return res

    def land(
        self,
        target_system: int = 1,
        target_component: int = 1,
        transport: Optional[str] = None,
    ) -> bool:
        """Send MAV_CMD_NAV_LAND (21) or set LAND mode."""
        print("[ACTION] Sending LAND command")
        res = self.send_command_long(
            command=21,
            target_system=target_system,
            target_component=target_component,
            transport=transport,
        )
        if not res:
            res = self.set_mode("LAND", target_system, target_component, transport)
        return res
