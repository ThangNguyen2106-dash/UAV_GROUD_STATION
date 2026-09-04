from __future__ import annotations

import sys
import time
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Rigel_GCS.core.connection_manager import ConnectionManager


# ============================================================
# STEP 12 - LIVE TELEMETRY TEST
# Purpose:
#   1. Select UDP or SERIAL.
#   2. Connect to Simulator / Pixhawk.
#   3. Show transport-isolated telemetry.
#   4. Show exactly which MAVLink message types are arriving.
#      This is important for diagnosing Pixhawk SERIAL telemetry.
# ============================================================

def fmt(value, digits=2, suffix=""):
    if value is None:
        return "--"
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def choose_transport():
    print("=" * 90)
    print(" RIGEL GCS - STEP 12 - LIVE MAVLINK TELEMETRY TEST")
    print("=" * 90)
    print("[1] UDP    -> Drone Simulator")
    print("[2] SERIAL -> Pixhawk")
    print("=" * 90)

    while True:
        choice = input("Chọn [1/2]: ").strip()
        if choice == "1":
            return "UDP"
        if choice == "2":
            return "SERIAL"
        print("[ERROR] Vui lòng nhập 1 hoặc 2.")


def choose_serial_port():
    print("\n--- SERIAL PORT ---")

    try:
        from serial.tools import list_ports
        ports = list(list_ports.comports())
    except Exception as exc:
        print(f"[WARN] Không đọc được danh sách COM: {exc}")
        ports = []

    if ports:
        for index, port in enumerate(ports, 1):
            desc = port.description or "Unknown"
            print(f"[{index}] {port.device:<8} {desc}")

        print("[0] Nhập COM thủ công")

        while True:
            choice = input("Chọn COM: ").strip()

            if choice == "0":
                break

            if choice.isdigit() and 1 <= int(choice) <= len(ports):
                return ports[int(choice) - 1].device.upper()

            print("[ERROR] Lựa chọn không hợp lệ.")

    return (input("Nhập COM, ví dụ COM6: ").strip() or "COM6").upper()


def selected_state(manager, transport):
    states = [
        state
        for state in manager.get_all_telemetry()
        if str(getattr(state, "transport", "")).upper() == transport
    ]

    if not states:
        return None

    states.sort(
        key=lambda state: bool(getattr(state, "heartbeat_alive", False)),
        reverse=True,
    )
    return states[0]


def message_type(message):
    try:
        return str(message.get_type()).upper()
    except Exception:
        return type(message).__name__.upper()


def make_rx_tracker():
    """
    Returns:
        rx_counter:
            Counter of MAVLink message types received.
        recent:
            Small queue containing the latest message names.
        last_message:
            Mutable dict containing latest raw message metadata.
    """
    rx_counter = Counter()
    recent = deque(maxlen=12)
    last_message = {
        "type": None,
        "sysid": None,
        "compid": None,
        "time": None,
    }

    def on_message(message, device=None):
        mtype = message_type(message)

        try:
            sysid = message.get_srcSystem()
        except Exception:
            sysid = None

        try:
            compid = message.get_srcComponent()
        except Exception:
            compid = None

        rx_counter[mtype] += 1
        recent.append(mtype)
        last_message["type"] = mtype
        last_message["sysid"] = sysid
        last_message["compid"] = compid
        last_message["time"] = time.monotonic()

    return rx_counter, recent, last_message, on_message


def show(state, transport, rx_counter, recent, last_message, started_at):
    # ANSI clear-screen. If ANSI is not supported, output is still readable.
    print("\033[2J\033[H", end="")

    print("=" * 90)
    print(" RIGEL GCS - STEP 12 - LIVE MAVLINK TELEMETRY")
    print("=" * 90)

    print(f"TRANSPORT       : {transport}")
    print(f"DEVICE ID       : {state.device_id}")
    print(f"SYSID / COMPID  : {state.sysid} / {state.compid}")
    print(f"CONNECTED       : {state.connected}")
    print(f"HEARTBEAT       : {state.heartbeat_alive}")

    print("-" * 90)
    print("[POSITION]")
    print(f"Latitude        : {fmt(getattr(state, 'latitude', None), 7)}")
    print(f"Longitude       : {fmt(getattr(state, 'longitude', None), 7)}")
    print(f"Altitude        : {fmt(getattr(state, 'altitude', None), 2, ' m')}")
    print(
        f"Relative Alt    : "
        f"{fmt(getattr(state, 'relative_altitude', None), 2, ' m')}"
    )
    print(
        f"Ground Speed    : "
        f"{fmt(getattr(state, 'groundspeed', None), 2, ' m/s')}"
    )
    print(f"Heading         : {fmt(getattr(state, 'heading', None), 1, ' deg')}")

    print("-" * 90)
    print("[GPS]")
    print(f"Fix Type        : {getattr(state, 'fix_type', None) if getattr(state, 'fix_type', None) is not None else '--'}")
    print(
        f"Satellites      : "
        f"{getattr(state, 'satellites_visible', None) if getattr(state, 'satellites_visible', None) is not None else '--'}"
    )

    print("-" * 90)
    print("[ATTITUDE]")
    print(f"Roll            : {fmt(getattr(state, 'roll', None), 3, ' rad')}")
    print(f"Pitch           : {fmt(getattr(state, 'pitch', None), 3, ' rad')}")
    print(f"Yaw             : {fmt(getattr(state, 'yaw', None), 3, ' rad')}")

    print("-" * 90)
    print("[FLIGHT]")
    print(f"Armed           : {getattr(state, 'armed', False)}")
    print(f"Airspeed        : {fmt(getattr(state, 'airspeed', None), 2, ' m/s')}")
    print(
        f"VFR Groundspd   : "
        f"{fmt(getattr(state, 'vfr_groundspeed', None), 2, ' m/s')}"
    )
    print(f"Throttle        : {fmt(getattr(state, 'throttle', None), 1, ' %')}")
    print(f"Climb           : {fmt(getattr(state, 'climb', None), 2, ' m/s')}")

    print("-" * 90)
    print("[BATTERY / SYSTEM]")
    print(
        f"Battery         : "
        f"{fmt(getattr(state, 'battery_remaining', None), 1, ' %')}"
    )
    print(
        f"Voltage         : "
        f"{fmt(getattr(state, 'voltage_battery', None), 3, ' V')}"
    )
    print(
        f"Current         : "
        f"{fmt(getattr(state, 'current_battery', None), 3, ' A')}"
    )
    print(f"Load            : {fmt(getattr(state, 'load', None), 1, ' %')}")

    print("-" * 90)
    print("[HOME]")
    print(
        f"Home Latitude   : "
        f"{fmt(getattr(state, 'home_latitude', None), 7)}"
    )
    print(
        f"Home Longitude  : "
        f"{fmt(getattr(state, 'home_longitude', None), 7)}"
    )
    print(
        f"Home Altitude   : "
        f"{fmt(getattr(state, 'home_altitude', None), 2, ' m')}"
    )

    print("-" * 90)
    print("[STATUS]")
    print(getattr(state, "status_text", None) or "--")

    # ------------------------------------------------------------
    # RAW MAVLINK RX DIAGNOSTICS
    # ------------------------------------------------------------
    print("-" * 90)
    print("[MAVLINK RX DIAGNOSTICS]")
    total = sum(rx_counter.values())
    elapsed = max(time.monotonic() - started_at, 0.001)
    rate = total / elapsed

    print(f"Total MAVLink messages : {total}")
    print(f"RX rate                : {rate:.1f} msg/s")

    if last_message["type"] is None:
        print("Last message           : --")
    else:
        print(
            f"Last message           : "
            f"{last_message['type']} "
            f"(SYSID={last_message['sysid']} COMPID={last_message['compid']})"
        )

    print("Message counts:")
    if rx_counter:
        for name, count in rx_counter.most_common():
            print(f"  {name:<22} {count}")
    else:
        print("  --")

    print("Recent:")
    if recent:
        print("  " + " -> ".join(recent))
    else:
        print("  --")

    print("=" * 90)
    print("Ctrl+C = STOP")
    print()


def main():
    transport = choose_transport()

    manager = ConnectionManager(
        heartbeat_timeout=5.0,
        link_lost_timeout=3.0,
    )

    rx_counter, recent, last_message, on_message = make_rx_tracker()

    # IMPORTANT:
    # ConnectionManager already sends every decoded MAVLink message
    # to on_message(). We use that callback only for diagnostics.
    manager.on_message = on_message

    try:
        if transport == "UDP":
            print("\n--- UDP CONFIG ---")

            rx_host = (
                input("GCS RX host [0.0.0.0]: ").strip()
                or "0.0.0.0"
            )
            rx_port = int(
                input("GCS RX port [14550]: ").strip()
                or "14550"
            )
            tx_host = (
                input("Simulator RX host [127.0.0.1]: ").strip()
                or "127.0.0.1"
            )
            tx_port = int(
                input("Simulator RX port [14560]: ").strip()
                or "14560"
            )

            print(f"\nGCS RX <- Simulator : {rx_host}:{rx_port}")
            print(f"GCS TX -> Simulator : {tx_host}:{tx_port}")

            ok = manager.connect_udp(
                rx_host=rx_host,
                rx_port=rx_port,
                tx_host=tx_host,
                tx_port=tx_port,
                heartbeat_timeout=5.0,
                wait=False,
            )

        else:
            port = choose_serial_port()

            baud = int(
                input("Baudrate [115200]: ").strip()
                or "115200"
            )

            print(f"\nPixhawk : {port} @ {baud}")

            ok = manager.connect_serial(
                port=port,
                baudrate=baud,
                heartbeat_timeout=5.0,
                wait=False,
            )

        if not ok:
            print("[FAIL] Không tạo được connection.")
            return 1

        print("[WAIT] Chờ HEARTBEAT trong tối đa 10 giây...")

        deadline = time.monotonic() + 10.0
        state = None

        while time.monotonic() < deadline:
            state = selected_state(manager, transport)

            if state is not None and state.heartbeat_alive:
                break

            time.sleep(0.2)

        if state is None or not state.heartbeat_alive:
            print("[FAIL] Không nhận được HEARTBEAT.")

            if transport == "UDP":
                print("Kiểm tra Simulator TX -> GCS UDP 14550.")
            else:
                print(
                    "Kiểm tra COM/baudrate và bảo đảm COM "
                    "không bị phần mềm khác chiếm."
                )

            return 2

        print(f"[OK] HEARTBEAT: {state.device_id}")
        print("[OK] Bắt đầu kiểm tra toàn bộ MAVLink telemetry...")
        time.sleep(1.0)

        started_at = time.monotonic()

        while True:
            state = selected_state(manager, transport)

            if state is None:
                print("[LOST] Không còn telemetry của transport đã chọn.")
                break

            show(
                state,
                transport,
                rx_counter,
                recent,
                last_message,
                started_at,
            )

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[STOP] Dừng STEP 12.")

    except (ValueError, OSError) as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}")
        return 3

    except Exception as exc:
        print(f"[TEST ERROR] {type(exc).__name__}: {exc}")
        return 4

    finally:
        try:
            manager.disconnect()
        except Exception:
            pass

        print("[DONE] Connection closed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
