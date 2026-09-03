"""
RIGEL GCS - MAVLink Telemetry Manager Test
===========================================

Run from project root:

    .venv\\Scripts\\python.exe -m Rigel_GCS.test.test_mavlink_telemetry
"""

from __future__ import annotations

from pathlib import Path
import sys
import time


# ============================================================================
# PROJECT PATH
# ============================================================================

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================================
# IMPORTS
# ============================================================================

from Rigel_GCS.mavlink.telemetry import (
    TelemetryManager,
    TelemetryState,
    normalize_telemetry_message,
)


# ============================================================================
# TEST COUNTERS
# ============================================================================

PASS_COUNT = 0
FAIL_COUNT = 0


def check(condition: bool, description: str) -> None:
    global PASS_COUNT, FAIL_COUNT

    if condition:
        PASS_COUNT += 1
        print(f"[PASS] {description}")
    else:
        FAIL_COUNT += 1
        print(f"[FAIL] {description}")


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================================
# TEST 1
# ============================================================================

def test_telemetry_state() -> None:

    section("TEST 1 - TelemetryState")

    state = TelemetryState(
        sysid=1,
        compid=1,
        transport="UDP",
    )

    check(
        state.sysid == 1,
        "SYSID = 1",
    )

    check(
        state.compid == 1,
        "COMPID = 1",
    )

    check(
        state.transport == "UDP",
        "TRANSPORT = UDP",
    )

    check(
        state.device_id == "UDP:1:1",
        "DEVICE ID = UDP:1:1",
    )

    check(
        state.connected is False,
        "Initial connected = False",
    )

    check(
        state.heartbeat_alive is False,
        "Initial heartbeat_alive = False",
    )


# ============================================================================
# TEST 2
# ============================================================================

def test_heartbeat() -> None:

    section("TEST 2 - HEARTBEAT")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "mav_type": 2,
            "autopilot": 3,
            "base_mode": 128,
            "custom_mode": 4,
            "system_status": 4,
        },
        transport="UDP",
    )

    check(
        state.device_id == "UDP:1:1",
        "Device ID",
    )

    check(
        state.mav_type == 2,
        "mav_type = 2",
    )

    check(
        state.autopilot == 3,
        "autopilot = 3",
    )

    check(
        state.base_mode == 128,
        "base_mode = 128",
    )

    check(
        state.custom_mode == 4,
        "custom_mode = 4",
    )

    check(
        state.system_status == 4,
        "system_status = 4",
    )

    check(
        state.connected is True,
        "connected = True",
    )

    check(
        state.last_heartbeat is not None,
        "last_heartbeat updated",
    )

    check(
        state.heartbeat_alive is True,
        "heartbeat_alive = True",
    )


# ============================================================================
# TEST 3
# ============================================================================

def test_gps_raw() -> None:

    section("TEST 3 - GPS_RAW_INT")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "GPS_RAW_INT",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "latitude": 10.8231,
            "longitude": 106.6297,
            "altitude": 12.5,
            "fix_type": 3,
            "satellites_visible": 15,
        },
        transport="UDP",
    )

    check(
        abs(state.latitude - 10.8231) < 1e-7,
        "Latitude = 10.8231",
    )

    check(
        abs(state.longitude - 106.6297) < 1e-7,
        "Longitude = 106.6297",
    )

    check(
        abs(state.gps_altitude - 12.5) < 1e-6,
        "GPS altitude = 12.5 m",
    )

    check(
        state.fix_type == 3,
        "fix_type = 3",
    )

    check(
        state.satellites_visible == 15,
        "satellites_visible = 15",
    )

    check(
        state.gps_has_fix is True,
        "GPS has fix",
    )


# ============================================================================
# TEST 4
# ============================================================================

def test_global_position() -> None:

    section("TEST 4 - GLOBAL_POSITION_INT")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "GLOBAL_POSITION_INT",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "latitude": 10.8240,
            "longitude": 106.6300,
            "altitude": 25.0,
            "relative_altitude": 20.0,
            "velocity_x": 3.0,
            "velocity_y": 4.0,
            "velocity_z": -1.0,
            "heading": 90.0,
        },
        transport="UDP",
    )

    check(
        abs(state.latitude - 10.8240) < 1e-7,
        "Latitude",
    )

    check(
        abs(state.longitude - 106.6300) < 1e-7,
        "Longitude",
    )

    check(
        abs(state.altitude - 25.0) < 1e-6,
        "Altitude = 25 m",
    )

    check(
        abs(state.relative_altitude - 20.0) < 1e-6,
        "Relative altitude = 20 m",
    )

    check(
        abs(state.velocity_x - 3.0) < 1e-6,
        "Velocity X = 3 m/s",
    )

    check(
        abs(state.velocity_y - 4.0) < 1e-6,
        "Velocity Y = 4 m/s",
    )

    check(
        abs(state.velocity_z + 1.0) < 1e-6,
        "Velocity Z = -1 m/s",
    )

    check(
        abs(state.heading - 90.0) < 1e-6,
        "Heading = 90 deg",
    )

    check(
        abs(state.ground_speed - 5.0) < 1e-6,
        "Ground speed = 5 m/s",
    )


# ============================================================================
# TEST 5
# ============================================================================

def test_attitude() -> None:

    section("TEST 5 - ATTITUDE")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "ATTITUDE",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "roll": 0.1,
            "pitch": -0.2,
            "yaw": 1.5,
            "roll_speed": 0.01,
            "pitch_speed": 0.02,
            "yaw_speed": 0.03,
        },
        transport="UDP",
    )

    check(
        abs(state.roll - 0.1) < 1e-9,
        "Roll",
    )

    check(
        abs(state.pitch + 0.2) < 1e-9,
        "Pitch",
    )

    check(
        abs(state.yaw - 1.5) < 1e-9,
        "Yaw",
    )

    check(
        abs(state.roll_speed - 0.01) < 1e-9,
        "Roll speed",
    )

    check(
        abs(state.pitch_speed - 0.02) < 1e-9,
        "Pitch speed",
    )

    check(
        abs(state.yaw_speed - 0.03) < 1e-9,
        "Yaw speed",
    )


# ============================================================================
# TEST 6
# ============================================================================

def test_system_status() -> None:

    section("TEST 6 - SYS_STATUS")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "SYS_STATUS",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "voltage_battery": 22.2,
            "current_battery": 5.5,
            "battery_remaining": 78,
            "load": 32,
        },
        transport="UDP",
    )

    check(
        abs(state.voltage_battery - 22.2) < 1e-6,
        "Voltage = 22.2 V",
    )

    check(
        abs(state.current_battery - 5.5) < 1e-6,
        "Current = 5.5 A",
    )

    check(
        state.battery_remaining == 78,
        "Battery remaining = 78%",
    )

    check(
        state.load == 32,
        "Load = 32%",
    )


# ============================================================================
# TEST 7
# ============================================================================

def test_battery_status() -> None:

    section("TEST 7 - BATTERY_STATUS")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "BATTERY_STATUS",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "battery_id": 0,
            "battery_remaining": 65,
            "current_consumed": 1250,
            "energy_consumed": 330,
        },
        transport="UDP",
    )

    check(
        state.battery_id == 0,
        "Battery ID = 0",
    )

    check(
        state.battery_remaining == 65,
        "Battery remaining = 65%",
    )

    check(
        state.current_consumed == 1250,
        "Current consumed = 1250",
    )

    check(
        state.energy_consumed == 330,
        "Energy consumed = 330",
    )


# ============================================================================
# TEST 8
# ============================================================================

def test_vfr_hud() -> None:

    section("TEST 8 - VFR_HUD")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "VFR_HUD",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "airspeed": 8.0,
            "groundspeed": 7.5,
            "heading": 180,
            "throttle": 45,
            "altitude": 30.0,
            "climb": 1.5,
        },
        transport="UDP",
    )

    check(
        abs(state.airspeed - 8.0) < 1e-6,
        "Airspeed = 8 m/s",
    )

    check(
        abs(state.groundspeed - 7.5) < 1e-6,
        "Groundspeed = 7.5 m/s",
    )

    check(
        state.heading == 180,
        "Heading = 180 deg",
    )

    check(
        state.throttle == 45,
        "Throttle = 45%",
    )

    check(
        abs(state.altitude - 30.0) < 1e-6,
        "Altitude = 30 m",
    )

    check(
        abs(state.climb - 1.5) < 1e-6,
        "Climb = 1.5 m/s",
    )


# ============================================================================
# TEST 9
# ============================================================================

def test_home_position() -> None:

    section("TEST 9 - HOME_POSITION")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "HOME_POSITION",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "latitude": 10.8231,
            "longitude": 106.6297,
            "altitude": 5.0,
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
        },
        transport="UDP",
    )

    check(
        abs(state.home_latitude - 10.8231) < 1e-7,
        "Home latitude",
    )

    check(
        abs(state.home_longitude - 106.6297) < 1e-7,
        "Home longitude",
    )

    check(
        abs(state.home_altitude - 5.0) < 1e-6,
        "Home altitude",
    )

    check(
        state.home_x == 0.0,
        "Home X",
    )

    check(
        state.home_y == 0.0,
        "Home Y",
    )

    check(
        state.home_z == 0.0,
        "Home Z",
    )


# ============================================================================
# TEST 10
# ============================================================================

def test_status_text() -> None:

    section("TEST 10 - STATUSTEXT")

    manager = TelemetryManager()

    state = manager.update(
        {
            "message_type": "STATUSTEXT",
            "sysid": 1,
            "compid": 1,
            "protocol_version": 2,
            "severity": 6,
            "text": "Mission started",
        },
        transport="UDP",
    )

    check(
        state.status_severity == 6,
        "Severity = 6",
    )

    check(
        state.status_text == "Mission started",
        "Status text",
    )


# ============================================================================
# TEST 11 - MESSAGE COUNTS
# ============================================================================

def test_message_counts() -> None:

    section("TEST 11 - MESSAGE COUNTS")

    manager = TelemetryManager()

    for _ in range(3):

        manager.update(
            {
                "message_type": "HEARTBEAT",
                "sysid": 1,
                "compid": 1,
                "mav_type": 2,
            },
            transport="UDP",
        )

    manager.update(
        {
            "message_type": "GPS_RAW_INT",
            "sysid": 1,
            "compid": 1,
            "latitude": 10.0,
            "longitude": 106.0,
            "altitude": 1.0,
            "fix_type": 3,
            "satellites_visible": 10,
        },
        transport="UDP",
    )

    state = manager.get(
        1,
        1,
        "UDP",
    )

    check(
        state is not None,
        "Telemetry state exists",
    )

    check(
        state.message_counts.get("HEARTBEAT") == 3,
        "HEARTBEAT count = 3",
    )

    check(
        state.message_counts.get("GPS_RAW_INT") == 1,
        "GPS_RAW_INT count = 1",
    )

    check(
        state.last_message_type == "GPS_RAW_INT",
        "Last message type = GPS_RAW_INT",
    )


# ============================================================================
# TEST 12 - MULTI DEVICE
# ============================================================================

def test_multi_device_isolation() -> None:

    section("TEST 12 - MULTI DEVICE ISOLATION")

    manager = TelemetryManager()

    manager.update(
        {
            "message_type": "GLOBAL_POSITION_INT",
            "sysid": 1,
            "compid": 1,
            "latitude": 10.1,
            "longitude": 106.1,
            "altitude": 10.0,
        },
        transport="UDP",
    )

    manager.update(
        {
            "message_type": "GLOBAL_POSITION_INT",
            "sysid": 1,
            "compid": 1,
            "latitude": 11.1,
            "longitude": 107.1,
            "altitude": 20.0,
        },
        transport="SERIAL",
    )

    manager.update(
        {
            "message_type": "GLOBAL_POSITION_INT",
            "sysid": 2,
            "compid": 1,
            "latitude": 12.1,
            "longitude": 108.1,
            "altitude": 30.0,
        },
        transport="UDP",
    )

    manager.update(
        {
            "message_type": "GLOBAL_POSITION_INT",
            "sysid": 2,
            "compid": 1,
            "latitude": 13.1,
            "longitude": 109.1,
            "altitude": 40.0,
        },
        transport="SERIAL",
    )

    check(
        manager.count() == 4,
        "Telemetry device count = 4",
    )

    udp1 = manager.get(1, 1, "UDP")
    serial1 = manager.get(1, 1, "SERIAL")
    udp2 = manager.get(2, 1, "UDP")
    serial2 = manager.get(2, 1, "SERIAL")

    check(
        udp1 is not None,
        "UDP:1:1 exists",
    )

    check(
        serial1 is not None,
        "SERIAL:1:1 exists",
    )

    check(
        udp2 is not None,
        "UDP:2:1 exists",
    )

    check(
        serial2 is not None,
        "SERIAL:2:1 exists",
    )

    check(
        abs(udp1.latitude - 10.1) < 1e-9,
        "UDP:1:1 isolated",
    )

    check(
        abs(serial1.latitude - 11.1) < 1e-9,
        "SERIAL:1:1 isolated",
    )

    check(
        abs(udp2.latitude - 12.1) < 1e-9,
        "UDP:2:1 isolated",
    )

    check(
        abs(serial2.latitude - 13.1) < 1e-9,
        "SERIAL:2:1 isolated",
    )


# ============================================================================
# TEST 13 - DEVICE IDS
# ============================================================================

def test_device_ids() -> None:

    section("TEST 13 - DEVICE IDS")

    manager = TelemetryManager()

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 1,
            "compid": 1,
        },
        transport="UDP",
    )

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 1,
            "compid": 1,
        },
        transport="SERIAL",
    )

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 2,
            "compid": 1,
        },
        transport="UDP",
    )

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 2,
            "compid": 1,
        },
        transport="SERIAL",
    )

    expected = {
        "UDP:1:1",
        "SERIAL:1:1",
        "UDP:2:1",
        "SERIAL:2:1",
    }

    actual = set(manager.device_ids())

    check(
        actual == expected,
        "Transport-aware device IDs",
    )

    check(
        manager.get_by_id("UDP:1:1") is not None,
        "get_by_id UDP:1:1",
    )

    check(
        manager.get_by_id("SERIAL:1:1") is not None,
        "get_by_id SERIAL:1:1",
    )


# ============================================================================
# TEST 14 - CALLBACK
# ============================================================================

def test_callback() -> None:

    section("TEST 14 - CALLBACK")

    received = []

    def on_update(state, message):

        received.append(
            (
                state.device_id,
                message.message_type,
            )
        )

    manager = TelemetryManager(
        on_update=on_update,
    )

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 1,
            "compid": 1,
        },
        transport="UDP",
    )

    manager.update(
        {
            "message_type": "GPS_RAW_INT",
            "sysid": 1,
            "compid": 1,
            "latitude": 10.0,
            "longitude": 106.0,
            "altitude": 1.0,
            "fix_type": 3,
            "satellites_visible": 12,
        },
        transport="UDP",
    )

    check(
        len(received) == 2,
        "Callback called twice",
    )

    check(
        received[0] == ("UDP:1:1", "HEARTBEAT"),
        "Heartbeat callback",
    )

    check(
        received[1] == ("UDP:1:1", "GPS_RAW_INT"),
        "GPS callback",
    )


# ============================================================================
# TEST 15 - SNAPSHOT
# ============================================================================

def test_snapshot() -> None:

    section("TEST 15 - SNAPSHOT")

    manager = TelemetryManager()

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 1,
            "compid": 1,
            "mav_type": 2,
        },
        transport="UDP",
    )

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 1,
            "compid": 1,
            "mav_type": 2,
        },
        transport="SERIAL",
    )

    snapshot = manager.snapshot()

    check(
        isinstance(snapshot, dict),
        "snapshot() returns dict",
    )

    check(
        "UDP:1:1" in snapshot,
        "Snapshot contains UDP:1:1",
    )

    check(
        "SERIAL:1:1" in snapshot,
        "Snapshot contains SERIAL:1:1",
    )

    check(
        snapshot["UDP:1:1"]["sysid"] == 1,
        "Snapshot SYSID",
    )

    check(
        snapshot["UDP:1:1"]["transport"] == "UDP",
        "Snapshot transport",
    )


# ============================================================================
# TEST 16 - REMOVE
# ============================================================================

def test_remove() -> None:

    section("TEST 16 - REMOVE")

    manager = TelemetryManager()

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 1,
            "compid": 1,
        },
        transport="UDP",
    )

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 1,
            "compid": 1,
        },
        transport="SERIAL",
    )

    check(
        manager.count() == 2,
        "Before remove count = 2",
    )

    removed = manager.remove(
        1,
        1,
        "UDP",
    )

    check(
        removed is not None,
        "UDP:1:1 removed",
    )

    check(
        manager.get(1, 1, "UDP") is None,
        "UDP:1:1 no longer exists",
    )

    check(
        manager.get(1, 1, "SERIAL") is not None,
        "SERIAL:1:1 remains",
    )

    check(
        manager.count() == 1,
        "After remove count = 1",
    )


# ============================================================================
# TEST 17 - REMOVE BY ID
# ============================================================================

def test_remove_by_id() -> None:

    section("TEST 17 - REMOVE BY ID")

    manager = TelemetryManager()

    manager.update(
        {
            "message_type": "HEARTBEAT",
            "sysid": 5,
            "compid": 1,
        },
        transport="UDP",
    )

    removed = manager.remove_by_id(
        "UDP:5:1",
    )

    check(
        removed is not None,
        "remove_by_id returned state",
    )

    check(
        manager.get_by_id("UDP:5:1") is None,
        "Device removed",
    )


# ============================================================================
# TEST 18 - CLEAR
# ============================================================================

def test_clear() -> None:

    section("TEST 18 - CLEAR")

    manager = TelemetryManager()

    for sysid in range(1, 5):

        manager.update(
            {
                "message_type": "HEARTBEAT",
                "sysid": sysid,
                "compid": 1,
            },
            transport="UDP",
        )

    check(
        manager.count() == 4,
        "Before clear count = 4",
    )

    manager.clear()

    check(
        manager.count() == 0,
        "After clear count = 0",
    )

    check(
        manager.all() == [],
        "all() is empty",
    )


# ============================================================================
# TEST 19 - NORMALIZER
# ============================================================================

def test_normalizer() -> None:

    section("TEST 19 - NORMALIZER")

    message = normalize_telemetry_message(
        {
            "message_type": "HEARTBEAT",
            "sysid": 7,
            "compid": 2,
            "protocol_version": 2,
            "mav_type": 2,
            "autopilot": 3,
        },
        transport="UDP",
    )

    check(
        message.message_type == "HEARTBEAT",
        "Message type",
    )

    check(
        message.sysid == 7,
        "SYSID",
    )

    check(
        message.compid == 2,
        "COMPID",
    )

    check(
        message.protocol_version == 2,
        "Protocol version = 2",
    )

    check(
        message.mav_type == 2,
        "mav_type",
    )

    check(
        message.autopilot == 3,
        "autopilot",
    )


# ============================================================================
# TEST 20 - INVALID MESSAGE
# ============================================================================

def test_invalid_message() -> None:

    section("TEST 20 - INVALID MESSAGE")

    manager = TelemetryManager()

    raised = False

    try:

        manager.update(
            {
                "message_type": "HEARTBEAT",
            },
            transport="UDP",
        )

    except (TypeError, ValueError):

        raised = True

    check(
        raised,
        "Invalid message rejected",
    )


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:

    global PASS_COUNT
    global FAIL_COUNT

    print()
    print("=" * 70)
    print("RIGEL GCS - MAVLink Telemetry Manager Test")
    print("=" * 70)

    tests = [
        test_telemetry_state,
        test_heartbeat,
        test_gps_raw,
        test_global_position,
        test_attitude,
        test_system_status,
        test_battery_status,
        test_vfr_hud,
        test_home_position,
        test_status_text,
        test_message_counts,
        test_multi_device_isolation,
        test_device_ids,
        test_callback,
        test_snapshot,
        test_remove,
        test_remove_by_id,
        test_clear,
        test_normalizer,
        test_invalid_message,
    ]

    for test in tests:

        try:
            test()

        except Exception as exc:

            FAIL_COUNT += 1

            print(
                f"[FAIL] {test.__name__} "
                f"raised {type(exc).__name__}: {exc}"
            )

    print()
    print("=" * 70)
    print(
        f"RESULT: PASS={PASS_COUNT} "
        f"FAIL={FAIL_COUNT}"
    )
    print("=" * 70)

    if FAIL_COUNT == 0:

        print(
            "[SUCCESS] MAVLink Telemetry Manager "
            "test PASSED"
        )

        return 0

    print(
        "[ERROR] MAVLink Telemetry Manager "
        "test FAILED"
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())