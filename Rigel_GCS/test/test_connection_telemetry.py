from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Rigel_GCS.core.connection_manager import ConnectionManager, _Link


class FakeConfig:
    rx_host = "0.0.0.0"
    rx_port = 14550
    tx_host = "127.0.0.1"
    tx_port = 14560


class FakeTransport:
    """Intentionally has no stop() to verify safe transport shutdown."""

    def __init__(self, kind):
        self.kind = kind
        self.config = FakeConfig()
        self.port = "COM6"
        self.baudrate = 115200


class FakeMessage:
    def __init__(self, msg_type, sysid=1, compid=1, **fields):
        self._type = msg_type
        self._sysid = sysid
        self._compid = compid
        for key, value in fields.items():
            setattr(self, key, value)

    def get_type(self):
        return self._type

    def get_srcSystem(self):
        return self._sysid

    def get_srcComponent(self):
        return self._compid


class FakeSession:
    def __init__(self):
        self.reset_called = False

    def reset(self):
        self.reset_called = True

    def statistics(self):
        return {"connected": True}


def make_link(kind, key):
    transport = FakeTransport(kind)
    from Rigel_GCS.core.mavlink_session import MAVLinkSession
    session = MAVLinkSession(source_system=255, source_component=190)
    return _Link(key=key, kind=kind, transport=transport, session=session)


def main():
    print("=" * 70)
    print("STEP 11 - CONNECTION -> TELEMETRY INTEGRATION TEST")
    print("=" * 70)

    manager = ConnectionManager(heartbeat_timeout=3.0, link_lost_timeout=3.0)

    udp = make_link("UDP", ("UDP", "0.0.0.0", 14550, "127.0.0.1", 14560))
    serial = make_link("SERIAL", ("SERIAL", "COM6", 115200))

    manager._links[udp.key] = udp
    manager._links[serial.key] = serial

    # ---------------------------------------------------------
    # 1. HEARTBEAT: same SYSID/COMPID, different transports
    # ---------------------------------------------------------
    hb_udp = FakeMessage(
        "HEARTBEAT",
        mav_type=2,
        autopilot=3,
        base_mode=81,
        custom_mode=0,
        system_status=4,
    )
    hb_serial = FakeMessage(
        "HEARTBEAT",
        mav_type=2,
        autopilot=3,
        base_mode=1,
        custom_mode=0,
        system_status=4,
    )

    manager._on_mavlink_message(udp, hb_udp)
    manager._on_mavlink_message(serial, hb_serial)

    udp_t = manager.get_telemetry(1, 1, "UDP")
    serial_t = manager.get_telemetry(1, 1, "SERIAL")

    assert udp_t is not None
    assert serial_t is not None
    assert udp_t.device_id == "UDP:1:1"
    assert serial_t.device_id == "SERIAL:1:1"
    assert manager.telemetry.count() == 2

    # ---------------------------------------------------------
    # 2. TELEMETRY UPDATE
    # ---------------------------------------------------------
    manager._on_mavlink_message(
        udp,
        FakeMessage(
            "GLOBAL_POSITION_INT",
            lat=108231000,
            lon=1066297000,
            alt=12500,
            relative_alt=10000,
            vx=300,
            vy=400,
            vz=-100,
            hdg=9000,
        ),
    )

    manager._on_mavlink_message(
        serial,
        FakeMessage(
            "VFR_HUD",
            airspeed=12.5,
            groundspeed=8.0,
            heading=180,
            throttle=55,
            alt=7.5,
            climb=0.8,
        ),
    )

    assert abs(udp_t.latitude - 10.8231) < 1e-6
    assert abs(udp_t.longitude - 106.6297) < 1e-6
    assert abs(udp_t.altitude - 12.5) < 1e-6
    assert abs(udp_t.relative_altitude - 10.0) < 1e-6
    assert abs(udp_t.groundspeed - 5.0) < 1e-6
    assert abs(udp_t.heading - 90.0) < 1e-6

    assert abs(serial_t.vfr_groundspeed - 8.0) < 1e-6
    assert abs(serial_t.altitude - 7.5) < 1e-6
    assert serial_t.heading == 180.0

    # ---------------------------------------------------------
    # 3. TRANSPORT ISOLATION
    # ---------------------------------------------------------
    assert udp_t.device_id != serial_t.device_id
    assert manager.get_telemetry_by_id("UDP:1:1") is udp_t
    assert manager.get_telemetry_by_id("SERIAL:1:1") is serial_t
    assert set(manager.telemetry.device_ids()) == {"UDP:1:1", "SERIAL:1:1"}

    # ---------------------------------------------------------
    # 4. DISCONNECT UDP ONLY
    # ---------------------------------------------------------
    udp.target_devices.add((1, 1))
    serial.target_devices.add((1, 1))
    udp.ready = True
    serial.ready = True
    from Rigel_GCS.core.connection_state import ConnectionState
    manager.state = ConnectionState.READY
    manager.connected = True

    assert manager._remove_link(udp.key) is True
    assert udp_t.connected is False
    assert serial_t.connected is True
    assert manager.connection_count() == 1

    # ---------------------------------------------------------
    # 5. DISCONNECT SERIAL
    # ---------------------------------------------------------
    assert manager._remove_link(serial.key) is True
    assert serial_t.connected is False
    assert manager.connection_count() == 0

    # The FakeTransport deliberately lacks stop(). There must be no
    # AttributeError / TRANSPORT STOP ERROR from that situation.
    print("[PASS] ConnectionManager -> TelemetryManager integration")
    print("[PASS] Transport-aware identities: UDP:1:1 / SERIAL:1:1")
    print("[PASS] Telemetry updates and transport isolation")
    print("[PASS] UDP disconnect propagates only to UDP telemetry")
    print("[PASS] SERIAL disconnect propagates only to SERIAL telemetry")
    print("[PASS] FakeTransport without stop() is handled safely")
    print("[PASS] STEP 11 completed")
    print("=" * 70)


if __name__ == "__main__":
    main()
