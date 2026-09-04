from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

# ============================================================
# PROJECT ROOT
# Cho phép chạy trực tiếp bằng VS Code:
# python Rigel_GCS/test/test_telemetry_select.py
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

UDP_RX_HOST = "0.0.0.0"
UDP_RX_PORT = 14550

UDP_TX_HOST = "127.0.0.1"
UDP_TX_PORT = 14560

DISPLAY_INTERVAL = 1.0


# ============================================================
# GLOBAL
# ============================================================

manager: Optional[ConnectionManager] = None

message_counter = {}


# ============================================================
# MAVLINK MESSAGE CALLBACK
# ============================================================

def on_message(message):
    """
    Callback nhận tất cả MAVLink message từ ConnectionManager.
    """

    try:
        message_type = message.get_type()

        if message_type == "BAD_DATA":
            return

        message_counter[message_type] = (
            message_counter.get(message_type, 0) + 1
        )

    except Exception:
        pass


# ============================================================
# MENU
# ============================================================

def print_menu():
    print()
    print("=" * 72)
    print("              RIGEL TELEMETRY TEST - STEP 12")
    print("=" * 72)
    print()
    print("[1] UDP")
    print("    Drone Simulator")
    print("    RX : 0.0.0.0:14550")
    print("    TX : 127.0.0.1:14560")
    print()
    print("[2] SERIAL")
    print("    Pixhawk")
    print(f"    PORT : {SERIAL_PORT}")
    print(f"    BAUD : {SERIAL_BAUDRATE}")
    print()
    print("[0] EXIT")
    print()
    print("=" * 72)


# ============================================================
# FIND DEVICE
# ============================================================

def find_device():
    """
    Tìm thiết bị ưu tiên SYSID=1 / COMPID=1.

    Ưu tiên:
        SERIAL:1:1
        UDP:1:1

    Nếu không tìm thấy thì lấy device đầu tiên.
    """

    try:
        devices = manager.telemetry.all()
    except Exception as exc:
        print(f"[TELEMETRY ERROR] Cannot get devices: {exc}")
        return None

    if not devices:
        return None

    preferred_transport = None

    if manager.connection_type:
        preferred_transport = str(manager.connection_type).upper()

    # --------------------------------------------------------
    # Ưu tiên SYSID=1 COMPID=1
    # --------------------------------------------------------

    for device in devices:

        try:
            if (
                int(device.sysid) == 1
                and int(device.compid) == 1
            ):
                if preferred_transport is None:
                    return device

                if str(device.transport).upper() == preferred_transport:
                    return device

        except Exception:
            continue

    # --------------------------------------------------------
    # Không có SYSID=1/COMPID=1 -> lấy thiết bị đầu tiên
    # --------------------------------------------------------

    return devices[0]


# ============================================================
# FORMAT
# ============================================================

def fmt(value, digits=2, suffix=""):
    if value is None:
        return "--"

    try:
        return f"{float(value):.{digits}f}{suffix}"
    except Exception:
        return str(value)


def fmt_int(value, suffix=""):
    if value is None:
        return "--"

    try:
        return f"{int(value)}{suffix}"
    except Exception:
        return str(value)


# ============================================================
# DISPLAY TELEMETRY
# ============================================================

def display_telemetry(device):
    print("\033[2J\033[H", end="")

    print("=" * 72)
    print("                    RIGEL TELEMETRY")
    print("=" * 72)

    print()

    # ========================================================
    # DEVICE
    # ========================================================

    print("[DEVICE]")

    print(
        f"Device ID       : "
        f"{getattr(device, 'device_id', '--')}"
    )

    print(
        f"Transport       : "
        f"{getattr(device, 'transport', '--')}"
    )

    print(
        f"SYSID           : "
        f"{getattr(device, 'sysid', '--')}"
    )

    print(
        f"COMPID          : "
        f"{getattr(device, 'compid', '--')}"
    )

    print(
        f"Connected       : "
        f"{getattr(device, 'connected', False)}"
    )

    print(
        f"Heartbeat       : "
        f"{getattr(device, 'heartbeat_alive', False)}"
    )

    print()

    # ========================================================
    # POSITION
    # ========================================================

    print("[POSITION]")

    print(
        f"Latitude        : "
        f"{fmt(getattr(device, 'latitude', None), 7)}"
    )

    print(
        f"Longitude       : "
        f"{fmt(getattr(device, 'longitude', None), 7)}"
    )

    print(
        f"Altitude        : "
        f"{fmt(getattr(device, 'altitude', None), 2, ' m')}"
    )

    print(
        f"Relative Alt    : "
        f"{fmt(getattr(device, 'relative_altitude', None), 2, ' m')}"
    )

    print(
        f"Ground Speed    : "
        f"{fmt(getattr(device, 'ground_speed', None), 2, ' m/s')}"
    )

    print(
        f"Heading         : "
        f"{fmt(getattr(device, 'heading', None), 1, ' deg')}"
    )

    print()

    # ========================================================
    # GPS
    # ========================================================

    print("[GPS]")

    print(
        f"Fix Type        : "
        f"{fmt_int(getattr(device, 'fix_type', None))}"
    )

    print(
        f"Satellites      : "
        f"{fmt_int(getattr(device, 'satellites_visible', None))}"
    )

    print()

    # ========================================================
    # ATTITUDE
    # ========================================================

    print("[ATTITUDE]")

    print(
        f"Roll            : "
        f"{fmt(getattr(device, 'roll', None), 2, ' deg')}"
    )

    print(
        f"Pitch           : "
        f"{fmt(getattr(device, 'pitch', None), 2, ' deg')}"
    )

    print(
        f"Yaw             : "
        f"{fmt(getattr(device, 'yaw', None), 2, ' deg')}"
    )

    print()

    # ========================================================
    # FLIGHT
    # ========================================================

    print("[FLIGHT]")

    print(
        f"Armed           : "
        f"{getattr(device, 'armed', False)}"
    )

    print(
        f"MAV Type        : "
        f"{fmt_int(getattr(device, 'mav_type', None))}"
    )

    print(
        f"Autopilot       : "
        f"{fmt_int(getattr(device, 'autopilot', None))}"
    )

    print(
        f"Flight Mode     : "
        f"{getattr(device, 'flight_mode', '--')}"
    )

    print()

    # ========================================================
    # VFR HUD
    # ========================================================

    print("[VFR HUD]")

    print(
        f"Airspeed        : "
        f"{fmt(getattr(device, 'airspeed', None), 2, ' m/s')}"
    )

    print(
        f"Ground Speed    : "
        f"{fmt(getattr(device, 'vfr_groundspeed', None), 2, ' m/s')}"
    )

    print(
        f"Throttle        : "
        f"{fmt(getattr(device, 'throttle', None), 1, ' %')}"
    )

    print(
        f"Climb           : "
        f"{fmt(getattr(device, 'climb', None), 2, ' m/s')}"
    )

    print()

    # ========================================================
    # BATTERY / SYSTEM
    # ========================================================

    print("[BATTERY / SYSTEM]")

    print(
        f"Voltage         : "
        f"{fmt(getattr(device, 'voltage_battery', None), 3, ' V')}"
    )

    print(
        f"Current         : "
        f"{fmt(getattr(device, 'current_battery', None), 3, ' A')}"
    )

    print(
        f"Battery         : "
        f"{fmt_int(getattr(device, 'battery_remaining', None), ' %')}"
    )

    print(
        f"Load            : "
        f"{fmt(getattr(device, 'load', None), 1)}"
    )

    print()

    # ========================================================
    # HOME
    # ========================================================

    print("[HOME]")

    print(
        f"Home Latitude   : "
        f"{fmt(getattr(device, 'home_latitude', None), 7)}"
    )

    print(
        f"Home Longitude  : "
        f"{fmt(getattr(device, 'home_longitude', None), 7)}"
    )

    print(
        f"Home Altitude   : "
        f"{fmt(getattr(device, 'home_altitude', None), 2, ' m')}"
    )

    print()

    # ========================================================
    # STATUS TEXT
    # ========================================================

    print("[STATUS TEXT]")

    print(
        f"Message         : "
        f"{getattr(device, 'status_text', '--') or '--'}"
    )

    print()

    # ========================================================
    # MESSAGE STATISTICS
    # ========================================================

    print("[MESSAGE STATISTICS]")

    important_messages = [
        "HEARTBEAT",
        "GLOBAL_POSITION_INT",
        "GPS_RAW_INT",
        "ATTITUDE",
        "SYS_STATUS",
        "BATTERY_STATUS",
        "VFR_HUD",
        "HOME_POSITION",
        "STATUSTEXT",
    ]

    total = sum(message_counter.values())

    for name in important_messages:
        print(
            f"{name:<20}: "
            f"{message_counter.get(name, 0)}"
        )

    print()

    print(f"TOTAL MAVLINK MSG : {total}")

    print()
    print("=" * 72)


# ============================================================
# WAIT FOR DEVICE
# ============================================================

def wait_for_device(timeout=10.0):
    print()
    print("[DISCOVERY] Waiting for MAVLink device...")

    start = time.monotonic()

    while time.monotonic() - start < timeout:

        device = find_device()

        if device is not None:

            print()
            print(
                "[DISCOVERY] Device found:"
            )

            print(
                f"  Device ID : "
                f"{getattr(device, 'device_id', '--')}"
            )

            print(
                f"  Transport : "
                f"{getattr(device, 'transport', '--')}"
            )

            print(
                f"  SYSID     : "
                f"{getattr(device, 'sysid', '--')}"
            )

            print(
                f"  COMPID    : "
                f"{getattr(device, 'compid', '--')}"
            )

            return device

        time.sleep(0.1)

    return None


# ============================================================
# UDP
# ============================================================

def connect_udp():
    print()
    print("=" * 72)
    print("CONNECT UDP - DRONE SIMULATOR")
    print("=" * 72)

    print()
    print(
        f"[UDP] RX : "
        f"{UDP_RX_HOST}:{UDP_RX_PORT}"
    )

    print(
        f"[UDP] TX : "
        f"{UDP_TX_HOST}:{UDP_TX_PORT}"
    )

    try:
        result = manager.connect_udp(
            rx_host=UDP_RX_HOST,
            rx_port=UDP_RX_PORT,
            tx_host=UDP_TX_HOST,
            tx_port=UDP_TX_PORT,
            wait=False,
        )

        print()
        print(f"[UDP] connect result: {result}")

        return True

    except TypeError as exc:

        print()
        print(
            "[UDP ERROR] connect_udp() API mismatch:"
        )
        print(exc)

        return False

    except Exception as exc:

        print()
        print(
            f"[UDP ERROR] "
            f"{type(exc).__name__}: {exc}"
        )

        return False


# ============================================================
# SERIAL
# ============================================================

def connect_serial():
    print()
    print("=" * 72)
    print("CONNECT SERIAL - PIXHAWK")
    print("=" * 72)

    print()
    print(
        f"[SERIAL] PORT : "
        f"{SERIAL_PORT}"
    )

    print(
        f"[SERIAL] BAUD : "
        f"{SERIAL_BAUDRATE}"
    )

    try:
        result = manager.connect_serial(
            port=SERIAL_PORT,
            baudrate=SERIAL_BAUDRATE,
            wait=False,
        )

        print()
        print(
            f"[SERIAL] connect result: "
            f"{result}"
        )

        return True

    except Exception as exc:

        print()
        print(
            f"[SERIAL ERROR] "
            f"{type(exc).__name__}: {exc}"
        )

        return False


# ============================================================
# MAIN TEST
# ============================================================

def run_test():
    global manager

    manager = ConnectionManager(
        heartbeat_timeout=3.0,
        link_lost_timeout=3.0,
    )

    # ConnectionManager hiện tại nhận callback
    # bằng cách gán thuộc tính sau khi tạo object.
    manager.on_message = on_message

    print_menu()

    choice = input("Select [0/1/2]: ").strip()

    if choice == "0":
        return

    # ========================================================
    # UDP
    # ========================================================

    if choice == "1":

        if not connect_udp():
            return

    # ========================================================
    # SERIAL
    # ========================================================

    elif choice == "2":

        if not connect_serial():
            return

    else:

        print()
        print("[ERROR] Invalid selection.")
        return

    # ========================================================
    # WAIT DEVICE
    # ========================================================

    device = wait_for_device(timeout=10.0)

    if device is None:

        print()
        print("=" * 72)
        print("RESULT : FAIL")
        print("=" * 72)

        print()
        print("Không tìm thấy MAVLink device.")

        if choice == "1":
            print()
            print("Kiểm tra:")
            print("  1. Drone Simulator đang chạy.")
            print("  2. Simulator TX -> 127.0.0.1:14550")
            print("  3. GCS RX -> 0.0.0.0:14550")
            print("  4. Simulator RX <- 0.0.0.0:14560")

        elif choice == "2":
            print()
            print("Kiểm tra:")
            print("  1. Pixhawk đã cắm USB.")
            print(f"  2. COM port = {SERIAL_PORT}")
            print(f"  3. Baudrate = {SERIAL_BAUDRATE}")

        return

    # ========================================================
    # TELEMETRY LOOP
    # ========================================================

    print()
    print("[TELEMETRY] Receiving MAVLink...")
    print("[TELEMETRY] Press Ctrl+C to stop.")

    try:

        while True:

            # Device có thể được recreate/update,
            # nên lấy lại object mỗi vòng.
            current = find_device()

            if current is not None:
                device = current

            display_telemetry(device)

            time.sleep(DISPLAY_INTERVAL)

    except KeyboardInterrupt:

        print()
        print()
        print("=" * 72)
        print("TEST STOPPED BY USER")
        print("=" * 72)

    finally:

        try:
            manager.disconnect()
        except Exception as exc:
            print(
                f"[CLEANUP ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

        print()
        print("[CLEANUP] Connection closed.")


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":
    run_test()