"""
RIGEL GCS - MAVLink Message Models Test

Run from project root:

    .venv\\Scripts\\python.exe -m Rigel_GCS.test.test_mavlink_messages
"""

from pathlib import Path
import sys


# ============================================================================
# PROJECT PATH
# ============================================================================

# Project root:
# RIGEL GROUD STATION/
ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================================
# IMPORTS
# ============================================================================

from Rigel_GCS.mavlink.messages import (
    MAVLinkMessageData,
    HeartbeatMessage,
    GlobalPositionMessage,
    GPSRawMessage,
    AttitudeMessage,
    SystemStatusMessage,
    BatteryStatusMessage,
    VFRHUDMessage,
    HomePositionMessage,
    StatusTextMessage,
    message_from_dict,
)


# ============================================================================
# TEST HELPER
# ============================================================================

PASS_COUNT = 0
FAIL_COUNT = 0


def check(condition: bool, message: str) -> None:
    """
    Simple assertion helper.
    """

    global PASS_COUNT, FAIL_COUNT

    if condition:
        PASS_COUNT += 1
        print(f"[PASS] {message}")

    else:
        FAIL_COUNT += 1
        print(f"[FAIL] {message}")
        raise AssertionError(message)


# ============================================================================
# TEST BASE MESSAGE
# ============================================================================

def test_base_message():
    print("\n=== TEST base message ===")

    msg = MAVLinkMessageData(
        sysid=1,
        compid=1,
        protocol_version=2,
    )

    # Base model is UNKNOWN by default.
    check(
        msg.message_type == "UNKNOWN",
        "base message default type",
    )

    data = msg.to_dict()

    check(
        data["message_type"] == "UNKNOWN",
        "base message type in dict",
    )

    check(
        data["sysid"] == 1,
        "base SYSID",
    )

    check(
        data["compid"] == 1,
        "base COMPID",
    )

    check(
        data["protocol_version"] == 2,
        "base protocol version",
    )


# ============================================================================
# TEST HEARTBEAT
# ============================================================================

def test_heartbeat():
    print("\n=== TEST HEARTBEAT ===")

    msg = HeartbeatMessage(
        sysid=1,
        compid=1,
        protocol_version=2,
        mav_type=2,
        autopilot=3,
        base_mode=128,
        custom_mode=4,
        system_status=4,
    )

    check(
        msg.message_type == "HEARTBEAT",
        "HEARTBEAT message type",
    )

    check(
        msg.sysid == 1,
        "HEARTBEAT SYSID",
    )

    check(
        msg.compid == 1,
        "HEARTBEAT COMPID",
    )

    check(
        msg.protocol_version == 2,
        "HEARTBEAT protocol version",
    )

    check(
        msg.mav_type == 2,
        "HEARTBEAT MAV_TYPE",
    )

    check(
        msg.autopilot == 3,
        "HEARTBEAT AUTOPILOT",
    )

    check(
        msg.base_mode == 128,
        "HEARTBEAT base mode",
    )

    check(
        msg.custom_mode == 4,
        "HEARTBEAT custom mode",
    )

    check(
        msg.system_status == 4,
        "HEARTBEAT system status",
    )

    check(
        msg.armed is True,
        "HEARTBEAT armed state",
    )

    data = msg.to_dict()

    check(
        data["message_type"] == "HEARTBEAT",
        "HEARTBEAT dict type",
    )

    check(
        data["armed"] is True,
        "HEARTBEAT dict armed state",
    )


# ============================================================================
# TEST GLOBAL POSITION
# ============================================================================

def test_global_position():
    print("\n=== TEST GLOBAL_POSITION_INT ===")

    msg = GlobalPositionMessage(
        sysid=1,
        compid=1,
        protocol_version=2,
        latitude=10.8231,
        longitude=106.6297,
        altitude=25.0,
        relative_altitude=20.0,
        velocity_x=3.0,
        velocity_y=4.0,
        velocity_z=-1.0,
        heading=90.0,
    )

    check(
        msg.message_type == "GLOBAL_POSITION_INT",
        "GLOBAL_POSITION_INT message type",
    )

    check(
        msg.latitude == 10.8231,
        "latitude",
    )

    check(
        msg.longitude == 106.6297,
        "longitude",
    )

    check(
        msg.altitude == 25.0,
        "altitude",
    )

    check(
        msg.relative_altitude == 20.0,
        "relative altitude",
    )

    check(
        msg.velocity_x == 3.0,
        "velocity X",
    )

    check(
        msg.velocity_y == 4.0,
        "velocity Y",
    )

    check(
        msg.velocity_z == -1.0,
        "velocity Z",
    )

    check(
        msg.ground_speed == 5.0,
        "ground speed calculation",
    )

    check(
        msg.heading == 90.0,
        "heading",
    )

    data = msg.to_dict()

    check(
        data["ground_speed"] == 5.0,
        "ground speed in dict",
    )


# ============================================================================
# TEST GPS
# ============================================================================

def test_gps():
    print("\n=== TEST GPS_RAW_INT ===")

    msg = GPSRawMessage(
        sysid=1,
        compid=1,
        protocol_version=1,
        latitude=10.8,
        longitude=106.6,
        altitude=15.0,
        fix_type=3,
        satellites_visible=14,
    )

    check(
        msg.message_type == "GPS_RAW_INT",
        "GPS_RAW_INT message type",
    )

    check(
        msg.has_fix is True,
        "GPS has fix",
    )

    check(
        msg.fix_type == 3,
        "GPS fix type",
    )

    check(
        msg.satellites_visible == 14,
        "GPS satellites",
    )

    data = msg.to_dict()

    check(
        data["has_fix"] is True,
        "GPS has_fix in dict",
    )


# ============================================================================
# TEST ATTITUDE
# ============================================================================

def test_attitude():
    print("\n=== TEST ATTITUDE ===")

    msg = AttitudeMessage(
        sysid=1,
        compid=1,
        protocol_version=2,
        roll=0.1,
        pitch=-0.2,
        yaw=1.57,
        roll_speed=0.01,
        pitch_speed=0.02,
        yaw_speed=0.03,
    )

    check(
        msg.message_type == "ATTITUDE",
        "ATTITUDE message type",
    )

    check(
        msg.roll == 0.1,
        "ATTITUDE roll",
    )

    check(
        msg.pitch == -0.2,
        "ATTITUDE pitch",
    )

    check(
        msg.yaw == 1.57,
        "ATTITUDE yaw",
    )

    check(
        msg.roll_speed == 0.01,
        "ATTITUDE roll speed",
    )

    check(
        msg.pitch_speed == 0.02,
        "ATTITUDE pitch speed",
    )

    check(
        msg.yaw_speed == 0.03,
        "ATTITUDE yaw speed",
    )


# ============================================================================
# TEST BATTERY
# ============================================================================

def test_battery():
    print("\n=== TEST BATTERY ===")

    sys_status = SystemStatusMessage(
        sysid=1,
        compid=1,
        protocol_version=2,
        voltage_battery=22.4,
        current_battery=8.5,
        battery_remaining=78,
        load=350,
    )

    check(
        sys_status.message_type == "SYS_STATUS",
        "SYS_STATUS message type",
    )

    check(
        sys_status.voltage_battery == 22.4,
        "battery voltage",
    )

    check(
        sys_status.current_battery == 8.5,
        "battery current",
    )

    check(
        sys_status.battery_remaining == 78,
        "battery percentage",
    )

    check(
        sys_status.load == 350,
        "system load",
    )

    battery = BatteryStatusMessage(
        sysid=1,
        compid=1,
        protocol_version=2,
        battery_id=0,
        battery_remaining=80,
        current_consumed=1000,
        energy_consumed=200,
    )

    check(
        battery.message_type == "BATTERY_STATUS",
        "BATTERY_STATUS message type",
    )

    check(
        battery.battery_id == 0,
        "BATTERY_STATUS battery ID",
    )

    check(
        battery.battery_remaining == 80,
        "BATTERY_STATUS percentage",
    )

    check(
        battery.current_consumed == 1000,
        "BATTERY_STATUS current consumed",
    )

    check(
        battery.energy_consumed == 200,
        "BATTERY_STATUS energy consumed",
    )


# ============================================================================
# TEST OTHER MESSAGES
# ============================================================================

def test_other_messages():
    print("\n=== TEST other messages ===")

    # ------------------------------------------------------------------------
    # VFR_HUD
    # ------------------------------------------------------------------------

    vfr = VFRHUDMessage(
        sysid=1,
        compid=1,
        protocol_version=2,
        airspeed=10.0,
        groundspeed=8.0,
        heading=90,
        throttle=50,
        altitude=20.0,
        climb=1.5,
    )

    check(
        vfr.message_type == "VFR_HUD",
        "VFR_HUD message type",
    )

    check(
        vfr.groundspeed == 8.0,
        "VFR_HUD groundspeed",
    )

    check(
        vfr.airspeed == 10.0,
        "VFR_HUD airspeed",
    )

    check(
        vfr.heading == 90,
        "VFR_HUD heading",
    )

    check(
        vfr.throttle == 50,
        "VFR_HUD throttle",
    )

    # ------------------------------------------------------------------------
    # HOME_POSITION
    # ------------------------------------------------------------------------

    home = HomePositionMessage(
        sysid=1,
        compid=1,
        protocol_version=2,
        latitude=10.8231,
        longitude=106.6297,
        altitude=5.0,
        x=0.0,
        y=0.0,
        z=0.0,
    )

    check(
        home.message_type == "HOME_POSITION",
        "HOME_POSITION message type",
    )

    check(
        home.latitude == 10.8231,
        "HOME_POSITION latitude",
    )

    check(
        home.longitude == 106.6297,
        "HOME_POSITION longitude",
    )

    check(
        home.altitude == 5.0,
        "HOME_POSITION altitude",
    )

    # ------------------------------------------------------------------------
    # STATUSTEXT
    # ------------------------------------------------------------------------

    status = StatusTextMessage(
        sysid=1,
        compid=1,
        protocol_version=2,
        severity=6,
        text="GPS OK",
    )

    check(
        status.message_type == "STATUSTEXT",
        "STATUSTEXT message type",
    )

    check(
        status.severity == 6,
        "STATUSTEXT severity",
    )

    check(
        status.text == "GPS OK",
        "STATUSTEXT text",
    )


# ============================================================================
# TEST FACTORY
# ============================================================================

def test_factory():
    print("\n=== TEST message factory ===")

    data = {
        "message_type": "GLOBAL_POSITION_INT",
        "sysid": 1,
        "compid": 1,
        "protocol_version": 2,
        "latitude": 10.8231,
        "longitude": 106.6297,
        "altitude": 25.0,
        "relative_altitude": 20.0,
        "velocity_x": 3.0,
        "velocity_y": 4.0,
        "velocity_z": 0.0,
        "heading": 90.0,
    }

    msg = message_from_dict(data)

    check(
        isinstance(msg, GlobalPositionMessage),
        "factory creates GlobalPositionMessage",
    )

    check(
        msg.message_type == "GLOBAL_POSITION_INT",
        "factory preserves message type",
    )

    check(
        msg.sysid == 1,
        "factory preserves SYSID",
    )

    check(
        msg.compid == 1,
        "factory preserves COMPID",
    )

    check(
        msg.protocol_version == 2,
        "factory preserves protocol version",
    )

    check(
        msg.latitude == 10.8231,
        "factory preserves latitude",
    )

    check(
        msg.longitude == 106.6297,
        "factory preserves longitude",
    )

    check(
        msg.ground_speed == 5.0,
        "factory preserves velocity data",
    )


# ============================================================================
# TEST UNKNOWN MESSAGE
# ============================================================================

def test_unknown_message():
    print("\n=== TEST unknown message ===")

    msg = message_from_dict(
        {
            "message_type": "UNKNOWN_MESSAGE",
            "sysid": 5,
            "compid": 10,
            "protocol_version": 2,
        }
    )

    check(
        isinstance(msg, MAVLinkMessageData),
        "unknown message uses base model",
    )

    check(
        msg.message_type == "UNKNOWN_MESSAGE",
        "unknown message type preserved",
    )

    check(
        msg.sysid == 5,
        "unknown SYSID preserved",
    )

    check(
        msg.compid == 10,
        "unknown COMPID preserved",
    )

    check(
        msg.protocol_version == 2,
        "unknown protocol version preserved",
    )


# ============================================================================
# TEST INVALID INPUT
# ============================================================================

def test_invalid_input():
    print("\n=== TEST invalid input ===")

    # message_from_dict() must reject non-dictionary input.

    try:
        message_from_dict(None)
    except TypeError:
        print("[PASS] factory rejects non-dict input")
    else:
        raise AssertionError(
            "factory should reject non-dict input"
        )

    # Missing message_type must raise ValueError.

    try:
        message_from_dict(
            {
                "sysid": 1,
                "compid": 1,
            }
        )
    except ValueError:
        print("[PASS] factory rejects missing message_type")
    else:
        raise AssertionError(
            "factory should reject missing message_type"
        )


# ============================================================================
# MAIN
# ============================================================================

def main():
    global PASS_COUNT, FAIL_COUNT

    PASS_COUNT = 0
    FAIL_COUNT = 0

    print("=" * 64)
    print("RIGEL GCS - MAVLink Message Models Test")
    print("=" * 64)

    tests = [
        test_base_message,
        test_heartbeat,
        test_global_position,
        test_gps,
        test_attitude,
        test_battery,
        test_other_messages,
        test_factory,
        test_unknown_message,
        test_invalid_input,
    ]

    for test in tests:
        try:
            test()

        except Exception as exc:
            FAIL_COUNT += 1

            print()
            print("=" * 64)
            print(f"[ERROR] {test.__name__}")
            print(f"{type(exc).__name__}: {exc}")
            print("=" * 64)

            raise

    print()
    print("=" * 64)
    print(
        f"RESULT: PASS={PASS_COUNT} FAIL={FAIL_COUNT}"
    )
    print("=" * 64)

    if FAIL_COUNT == 0:
        print(
            "[SUCCESS] MAVLink Message Models test PASSED"
        )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()