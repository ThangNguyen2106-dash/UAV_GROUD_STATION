from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Rigel_GCS.core.connection_manager import ConnectionManager
from Rigel_GCS.core.active_vehicle import ActiveVehicleManager


def main():
    manager = ConnectionManager(
        heartbeat_timeout=3.0,
        link_lost_timeout=3.0,
    )

    active = ActiveVehicleManager()

    print("=" * 78)
    print("RIGEL GCS - STEP 12.5 DEVICE SELECTION TEST")
    print("=" * 78)
    print()
    print("This test does not modify the transport backend.")
    print("It verifies:")
    print("  1. Exactly 1 discovered device -> AUTO SELECT")
    print("  2. More than 1 device -> MANUAL SELECTION REQUIRED")
    print("  3. Selection is based on LINK + SYSID + COMPID")
    print()

    print("[1] UDP")
    print("[2] SERIAL")
    print("[0] EXIT")
    print()

    choice = input("Start connection [0/1/2]: ").strip()

    try:
        if choice == "0":
            return

        if choice == "1":
            manager.connect_udp(
                rx_host="0.0.0.0",
                rx_port=14550,
                tx_host="127.0.0.1",
                tx_port=14560,
                wait=False,
            )

        elif choice == "2":
            port = input(
                "COM port [default COM6]: "
            ).strip() or "COM6"

            baud_raw = input(
                "Baudrate [default 115200]: "
            ).strip() or "115200"

            manager.connect_serial(
                port=port,
                baudrate=int(baud_raw),
                wait=False,
            )

        else:
            print("Invalid selection.")
            return

        print()
        print("[DISCOVERY] Waiting for MAVLink device(s)...")

        # Give the selected link time to receive heartbeat.
        deadline = time.monotonic() + 10.0

        while time.monotonic() < deadline:
            candidates = active.refresh(manager)

            if candidates:
                break

            time.sleep(0.1)

        candidates = active.refresh(manager)

        print()
        active.print_candidates()

        if not candidates:
            print()
            print("RESULT : FAIL")
            print("No MAVLink devices discovered.")
            return

        # ------------------------------------------------------
        # Exactly one device -> AUTO
        # ------------------------------------------------------

        if len(candidates) == 1:

            selected = active.require_selection()

            print()
            print("=" * 78)
            print("AUTO SELECTION")
            print("=" * 78)
            print()
            print(
                f"ACTIVE DEVICE : {selected.device_id}"
            )
            print(
                f"TRANSPORT     : {selected.transport}"
            )
            print(
                f"RX ENDPOINT   : {selected.rx_endpoint}"
            )
            print(
                f"TX ENDPOINT   : {selected.tx_endpoint}"
            )
            print(
                f"SYSID         : {selected.sysid}"
            )
            print(
                f"COMPID        : {selected.compid}"
            )
            print(
                f"AUTO SELECTED : {active.auto_selected}"
            )

        # ------------------------------------------------------
        # Multiple devices -> mandatory manual selection
        # ------------------------------------------------------

        else:

            print()
            print(
                "Multiple devices are present."
            )
            print(
                "The GCS MUST NOT auto-select one."
            )

            selected = active.require_selection()

            print()
            print("=" * 78)
            print("MANUAL SELECTION")
            print("=" * 78)
            print()
            print(
                f"ACTIVE DEVICE : {selected.device_id}"
            )
            print(
                f"TRANSPORT     : {selected.transport}"
            )
            print(
                f"RX ENDPOINT   : {selected.rx_endpoint}"
            )
            print(
                f"TX ENDPOINT   : {selected.tx_endpoint}"
            )
            print(
                f"SYSID         : {selected.sysid}"
            )
            print(
                f"COMPID        : {selected.compid}"
            )
            print(
                f"AUTO SELECTED : {active.auto_selected}"
            )

        print()
        print("=" * 78)
        print("RESULT : PASS")
        print("=" * 78)

    except KeyboardInterrupt:
        print()
        print("Interrupted by user.")

    finally:
        try:
            manager.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    main()
