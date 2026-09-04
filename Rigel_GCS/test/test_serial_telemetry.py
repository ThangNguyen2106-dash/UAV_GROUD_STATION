from __future__ import annotations

import sys
import time
from pathlib import Path
from collections import Counter


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from Rigel_GCS.core.connection_manager import ConnectionManager


# ============================================================
# CONFIG
# ============================================================

SERIAL_PORT = "COM6"
SERIAL_BAUDRATE = 115200

TEST_DURATION = 15.0
DISPLAY_INTERVAL = 1.0


# ============================================================
# GLOBAL DIAGNOSTIC
# ============================================================

message_counter = Counter()
heartbeat_count = 0


# ============================================================
# CALLBACK
# ============================================================

def on_message(message):
    global heartbeat_count

    message_type = getattr(message, "message_type", None)

    if message_type is None:

        getter = getattr(message, "get_type", None)

        if callable(getter):
            try:
                message_type = getter()
            except Exception:
                message_type = "UNKNOWN"
        else:
            message_type = "UNKNOWN"

    message_type = str(message_type).upper()

    message_counter[message_type] += 1

    if message_type == "HEARTBEAT":
        heartbeat_count += 1


# ============================================================
# SAFE VALUE
# ============================================================

def value(obj, name, default=None):
    return getattr(obj, name, default)


def fmt(value_, fmt_spec=""):
    if value_ is None:
        return "--"

    try:
        return format(value_, fmt_spec)
    except Exception:
        return str(value_)


# ============================================================
# DISPLAY TELEMETRY
# ============================================================

def display_state(state):

    print()
    print("=" * 72)
    print("PIXHAWK SERIAL TELEMETRY")
    print("=" * 72)

    # --------------------------------------------------------
    # DEVICE
    # --------------------------------------------------------

    print("\n[DEVICE]")

    print(f"Device ID       : {value(state, 'device_id', '--')}")
    print(f"Transport       : {value(state, 'transport', '--')}")
    print(f"SYSID           : {value(state, 'sysid', '--')}")
    print(f"COMPID          : {value(state, 'compid', '--')}")
    print(f"Connected       : {value(state, 'connected', False)}")
    print(f"Heartbeat       : {value(state, 'heartbeat_alive', False)}")

    # --------------------------------------------------------
    # POSITION
    # --------------------------------------------------------

    print("\n[POSITION]")

    print(
        f"Latitude        : "
        f"{fmt(value(state, 'latitude'), '.7f')}"
    )

    print(
        f"Longitude       : "
        f"{fmt(value(state, 'longitude'), '.7f')}"
    )

    print(
        f"Altitude        : "
        f"{fmt(value(state, 'altitude'), '.2f')} m"
    )

    print(
        f"Relative Alt    : "
        f"{fmt(value(state, 'relative_altitude'), '.2f')} m"
    )

    print(
        f"Ground Speed    : "
        f"{fmt(value(state, 'groundspeed'), '.2f')} m/s"
    )

    print(
        f"Heading         : "
        f"{fmt(value(state, 'heading'), '.1f')} deg"
    )

    # --------------------------------------------------------
    # GPS
    # --------------------------------------------------------

    print("\n[GPS]")

    print(
        f"Fix Type        : "
        f"{fmt(value(state, 'fix_type'))}"
    )

    print(
        f"Satellites      : "
        f"{fmt(value(state, 'satellites_visible'))}"
    )

    # --------------------------------------------------------
    # ATTITUDE
    # --------------------------------------------------------

    print("\n[ATTITUDE]")

    print(
        f"Roll            : "
        f"{fmt(value(state, 'roll'), '.2f')} deg"
    )

    print(
        f"Pitch           : "
        f"{fmt(value(state, 'pitch'), '.2f')} deg"
    )

    print(
        f"Yaw             : "
        f"{fmt(value(state, 'yaw'), '.2f')} deg"
    )

    # --------------------------------------------------------
    # FLIGHT
    # --------------------------------------------------------

    print("\n[FLIGHT]")

    print(
        f"Armed           : "
        f"{fmt(value(state, 'armed'))}"
    )

    print(
        f"MAV Type        : "
        f"{fmt(value(state, 'mav_type'))}"
    )

    print(
        f"Autopilot       : "
        f"{fmt(value(state, 'autopilot'))}"
    )

    print(
        f"Flight Mode     : "
        f"{fmt(value(state, 'flight_mode'))}"
    )

    # --------------------------------------------------------
    # VFR HUD
    # --------------------------------------------------------

    print("\n[VFR HUD]")

    print(
        f"Airspeed        : "
        f"{fmt(value(state, 'airspeed'), '.2f')} m/s"
    )

    print(
        f"Ground Speed    : "
        f"{fmt(value(state, 'vfr_groundspeed'), '.2f')} m/s"
    )

    print(
        f"Throttle        : "
        f"{fmt(value(state, 'throttle'), '.1f')} %"
    )

    print(
        f"Climb           : "
        f"{fmt(value(state, 'climb'), '.2f')} m/s"
    )

    # --------------------------------------------------------
    # BATTERY
    # --------------------------------------------------------

    print("\n[BATTERY / SYSTEM]")

    print(
        f"Voltage         : "
        f"{fmt(value(state, 'voltage_battery'), '.3f')} V"
    )

    print(
        f"Current         : "
        f"{fmt(value(state, 'current_battery'), '.3f')} A"
    )

    print(
        f"Battery         : "
        f"{fmt(value(state, 'battery_remaining'))} %"
    )

    print(
        f"Load            : "
        f"{fmt(value(state, 'load'))}"
    )

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    print("\n[HOME]")

    print(
        f"Home Latitude   : "
        f"{fmt(value(state, 'home_latitude'), '.7f')}"
    )

    print(
        f"Home Longitude  : "
        f"{fmt(value(state, 'home_longitude'), '.7f')}"
    )

    print(
        f"Home Altitude   : "
        f"{fmt(value(state, 'home_altitude'), '.2f')} m"
    )

    # --------------------------------------------------------
    # STATUS TEXT
    # --------------------------------------------------------

    print("\n[STATUS TEXT]")

    status_text = value(state, "status_text")

    if status_text:
        print(f"Message         : {status_text}")
    else:
        print("Message         : --")

    print("=" * 72)


# ============================================================
# FIND SERIAL DEVICE
# ============================================================

def find_serial_device(manager):

    devices = manager.telemetry.all()

    # Prefer SYSID=1 COMPID=1
    for state in devices:

        if (
            value(state, "transport") == "SERIAL"
            and value(state, "sysid") == 1
            and value(state, "compid") == 1
        ):
            return state

    # Fallback
    for state in devices:

        if value(state, "transport") == "SERIAL":
            return state

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print("RIGEL GCS - STEP 12 SERIAL TELEMETRY TEST")
    print("=" * 72)

    print(f"Serial Port     : {SERIAL_PORT}")
    print(f"Baudrate        : {SERIAL_BAUDRATE}")
    print(f"Test Duration   : {TEST_DURATION:.1f} seconds")

    manager = None

    try:

        # ====================================================
        # CREATE CONNECTION MANAGER
        # ====================================================

        manager = ConnectionManager(
            heartbeat_timeout=3.0,
            link_lost_timeout=3.0,
        )

        # ====================================================
        # REGISTER MESSAGE CALLBACK
        # ====================================================

        manager.on_message = on_message

        # ====================================================
        # CONNECT SERIAL
        # ====================================================

        print()
        print("[1] Connecting to Pixhawk...")

        result = manager.connect_serial(
            port=SERIAL_PORT,
            baudrate=SERIAL_BAUDRATE,
            wait=False,
        )

        print(f"[CONNECT RESULT] {result}")
        print("[OK] Serial connection started.")

        # ====================================================
        # WAIT HEARTBEAT
        # ====================================================

        print()
        print("[2] Waiting for Pixhawk heartbeat...")

        start = time.time()
        state = None

        while time.time() - start < 8.0:

            state = find_serial_device(manager)

            if state is not None:

                if value(state, "heartbeat_alive", False):
                    break

            time.sleep(0.2)

        if state is None:

            print()
            print("[ERROR] No SERIAL device discovered.")
            return 1

        if not value(state, "heartbeat_alive", False):

            print()
            print("[ERROR] Pixhawk heartbeat not detected.")
            return 1

        print("[OK] Pixhawk heartbeat detected.")

        # ====================================================
        # TELEMETRY LOOP
        # ====================================================

        print()
        print("[3] Receiving telemetry...")
        print()

        test_start = time.time()
        last_display = 0.0

        while time.time() - test_start < TEST_DURATION:

            state = find_serial_device(manager)

            if state is not None:

                now = time.time()

                if now - last_display >= DISPLAY_INTERVAL:

                    display_state(state)

                    last_display = now

            time.sleep(0.05)

        # ====================================================
        # FINAL DIAGNOSTIC
        # ====================================================

        print()
        print("=" * 72)
        print("FINAL SERIAL DIAGNOSTIC")
        print("=" * 72)

        state = find_serial_device(manager)

        if state is not None:

            print(
                f"DEVICE ID       : "
                f"{value(state, 'device_id', '--')}"
            )

            print(
                f"TRANSPORT       : "
                f"{value(state, 'transport', '--')}"
            )

            print(
                f"CONNECTED       : "
                f"{value(state, 'connected', False)}"
            )

            print(
                f"HEARTBEAT       : "
                f"{value(state, 'heartbeat_alive', False)}"
            )

            print(
                f"SYSID           : "
                f"{value(state, 'sysid', '--')}"
            )

            print(
                f"COMPID          : "
                f"{value(state, 'compid', '--')}"
            )

            print()
            print("[POSITION]")

            print(
                f"Latitude        : "
                f"{fmt(value(state, 'latitude'), '.7f')}"
            )

            print(
                f"Longitude       : "
                f"{fmt(value(state, 'longitude'), '.7f')}"
            )

            print(
                f"Altitude        : "
                f"{fmt(value(state, 'altitude'), '.2f')} m"
            )

            print(
                f"Relative Alt    : "
                f"{fmt(value(state, 'relative_altitude'), '.2f')} m"
            )

            print(
                f"Ground Speed    : "
                f"{fmt(value(state, 'groundspeed'), '.2f')} m/s"
            )

            print(
                f"Heading         : "
                f"{fmt(value(state, 'heading'), '.1f')} deg"
            )

            print()
            print("[GPS]")

            print(
                f"Fix Type        : "
                f"{fmt(value(state, 'fix_type'))}"
            )

            print(
                f"Satellites      : "
                f"{fmt(value(state, 'satellites_visible'))}"
            )

        else:

            print("[ERROR] TelemetryState not found.")

        # ====================================================
        # MESSAGE STATISTICS
        # ====================================================

        print()
        print("[MESSAGE STATISTICS]")

        print(
            f"HEARTBEAT       : "
            f"{message_counter.get('HEARTBEAT', 0)}"
        )

        print(
            f"GLOBAL_POSITION_INT : "
            f"{message_counter.get('GLOBAL_POSITION_INT', 0)}"
        )

        print(
            f"GPS_RAW_INT     : "
            f"{message_counter.get('GPS_RAW_INT', 0)}"
        )

        print(
            f"ATTITUDE        : "
            f"{message_counter.get('ATTITUDE', 0)}"
        )

        print(
            f"SYS_STATUS      : "
            f"{message_counter.get('SYS_STATUS', 0)}"
        )

        print(
            f"BATTERY_STATUS  : "
            f"{message_counter.get('BATTERY_STATUS', 0)}"
        )

        print(
            f"VFR_HUD         : "
            f"{message_counter.get('VFR_HUD', 0)}"
        )

        print()
        print(
            f"TOTAL MAVLINK MSG : "
            f"{sum(message_counter.values())}"
        )

        # ====================================================
        # REQUIRED MESSAGES
        # ====================================================

        required_messages = [
            "HEARTBEAT",
            "GLOBAL_POSITION_INT",
            "GPS_RAW_INT",
            "ATTITUDE",
            "SYS_STATUS",
            "BATTERY_STATUS",
            "VFR_HUD",
        ]

        missing = [
            msg
            for msg in required_messages
            if message_counter.get(msg, 0) == 0
        ]

        # ====================================================
        # RESULT
        # ====================================================

        print()
        print("=" * 72)

        if state is None:

            print("RESULT : FAIL")
            print("Reason : TelemetryState not found.")
            return 1

        if not value(state, "heartbeat_alive", False):

            print("RESULT : FAIL")
            print("Reason : Pixhawk heartbeat was not alive.")
            return 1

        if missing:

            print("RESULT : FAIL")
            print("Missing MAVLink messages:")

            for msg in missing:
                print(f"  - {msg}")

            return 1

        if sum(message_counter.values()) == 0:

            print("RESULT : FAIL")
            print("Reason : No MAVLink messages received.")
            return 1

        print("RESULT : PASS")
        print()
        print("Pixhawk SERIAL connection is working.")
        print("MAVLink messages are being received.")
        print("TelemetryState is available.")
        print("=" * 72)

        return 0

    # ========================================================
    # CTRL+C
    # ========================================================

    except KeyboardInterrupt:

        print()
        print("[CTRL+C] Test interrupted.")
        return 130

    # ========================================================
    # ERROR
    # ========================================================

    except Exception as exc:

        print()
        print("=" * 72)
        print("[UNHANDLED TEST ERROR]")
        print(f"{type(exc).__name__}: {exc}")
        print("=" * 72)

        return 1

    # ========================================================
    # CLEANUP
    # ========================================================

    finally:

        if manager is not None:

            try:

                # ConnectionManager hiện tại có disconnect().
                manager.disconnect()

                print("[CLEANUP] SERIAL connection closed.")

            except Exception as exc:

                print(
                    f"[CLEANUP ERROR] "
                    f"{type(exc).__name__}: {exc}"
                )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(main())