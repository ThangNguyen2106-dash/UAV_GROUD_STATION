"""
RIGEL GCS - Active Vehicle Selection
====================================

STEP 12.5
Keeps the currently selected MAVLink vehicle/link.

Rules:
    - 0 devices  -> no active vehicle
    - 1 device   -> AUTO SELECT
    - >1 devices -> user MUST select

Selection identity is transport/link aware.  The same SYSID/COMPID
on different COM ports or UDP links is therefore still selectable
as a different connection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class VehicleCandidate:
    index: int
    transport: str
    sysid: int
    compid: int
    rx_endpoint: str
    tx_endpoint: str
    link_key: tuple
    device_id: str

    @property
    def display_name(self) -> str:
        return (
            f"{self.transport} | "
            f"SYSID={self.sysid} COMPID={self.compid} | "
            f"RX={self.rx_endpoint}"
        )


class ActiveVehicleManager:
    """
    Selects one active vehicle from discovered devices.

    The manager does not open/close transports and does not parse
    MAVLink. It only decides which discovered link/device is active.
    """

    def __init__(self) -> None:
        self._candidates: list[VehicleCandidate] = []
        self._active: Optional[VehicleCandidate] = None
        self._auto_selected = False

    # ------------------------------------------------------------------
    # Discovery -> candidates
    # ------------------------------------------------------------------

    def refresh(self, connection_manager: Any) -> list[VehicleCandidate]:
        """
        Build candidates from ConnectionManager.

        A candidate is:
            link + SYSID + COMPID

        This means:
            SERIAL COM6 SYSID=1
            SERIAL COM8 SYSID=1

        remain two different candidates.
        """

        candidates: list[VehicleCandidate] = []

        connections = connection_manager.get_connections()
        devices = connection_manager.get_devices()

        # Map each link to its discovered devices.
        for connection in connections:
            link_key = tuple(connection.get("key", ()))
            transport = str(
                connection.get("transport", "UNKNOWN")
            ).upper()

            rx_endpoint = str(
                connection.get("rx_endpoint", "--")
            )

            tx_endpoint = str(
                connection.get("tx_endpoint", "--")
            )

            link_devices = set(
                tuple(x)
                for x in connection.get("devices", [])
                if isinstance(x, (tuple, list))
                and len(x) >= 2
            )

            # Prefer registry information so the candidate contains
            # the exact endpoint belonging to that connection.
            for device in devices:
                d_transport = str(
                    getattr(device, "transport", "UNKNOWN")
                    or "UNKNOWN"
                ).upper()

                sysid = int(getattr(device, "sysid", 0))
                compid = int(getattr(device, "compid", 0))

                if d_transport != transport:
                    continue

                if link_devices and (sysid, compid) not in link_devices:
                    continue

                device_id = (
                    f"{transport}:{sysid}:{compid}"
                )

                candidates.append(
                    VehicleCandidate(
                        index=0,
                        transport=transport,
                        sysid=sysid,
                        compid=compid,
                        rx_endpoint=str(
                            getattr(
                                device,
                                "rx_endpoint",
                                rx_endpoint,
                            )
                            or rx_endpoint
                        ),
                        tx_endpoint=str(
                            getattr(
                                device,
                                "tx_endpoint",
                                tx_endpoint,
                            )
                            or tx_endpoint
                        ),
                        link_key=link_key,
                        device_id=device_id,
                    )
                )

            # A ready link may exist before a registry device appears.
            # Do not create a fake vehicle in that case.

        # Deduplicate by link + SYSID + COMPID.
        unique: dict[tuple, VehicleCandidate] = {}

        for candidate in candidates:
            identity = (
                candidate.link_key,
                candidate.sysid,
                candidate.compid,
            )
            unique[identity] = candidate

        ordered = sorted(
            unique.values(),
            key=lambda c: (
                c.transport,
                c.rx_endpoint,
                c.sysid,
                c.compid,
            ),
        )

        self._candidates = [
            VehicleCandidate(
                index=i,
                transport=c.transport,
                sysid=c.sysid,
                compid=c.compid,
                rx_endpoint=c.rx_endpoint,
                tx_endpoint=c.tx_endpoint,
                link_key=c.link_key,
                device_id=c.device_id,
            )
            for i, c in enumerate(ordered, start=1)
        ]

        # AUTO only when exactly one candidate exists.
        if len(self._candidates) == 1:
            self._active = self._candidates[0]
            self._auto_selected = True
        else:
            self._auto_selected = False

            # Existing active selection is preserved if still present.
            if self._active is not None:
                active_identity = (
                    self._active.link_key,
                    self._active.sysid,
                    self._active.compid,
                )

                if not any(
                    (
                        c.link_key,
                        c.sysid,
                        c.compid,
                    ) == active_identity
                    for c in self._candidates
                ):
                    self._active = None

            # Never silently choose one of many.
            if len(self._candidates) != 1:
                self._active = None

        return list(self._candidates)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def candidates(self) -> list[VehicleCandidate]:
        return list(self._candidates)

    @property
    def active(self) -> Optional[VehicleCandidate]:
        return self._active

    @property
    def auto_selected(self) -> bool:
        return self._auto_selected

    @property
    def requires_selection(self) -> bool:
        return len(self._candidates) > 1 and self._active is None

    @property
    def count(self) -> int:
        return len(self._candidates)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select(self, index: int) -> VehicleCandidate:
        index = int(index)

        for candidate in self._candidates:
            if candidate.index == index:
                self._active = candidate
                self._auto_selected = False
                return candidate

        raise ValueError(
            f"Invalid vehicle selection: {index}"
        )

    def select_by_device_id(
        self,
        device_id: str,
    ) -> VehicleCandidate:
        target = str(device_id).upper()

        matches = [
            c for c in self._candidates
            if c.device_id.upper() == target
        ]

        if len(matches) == 1:
            self._active = matches[0]
            self._auto_selected = False
            return matches[0]

        if not matches:
            raise ValueError(
                f"Device not found: {device_id}"
            )

        raise ValueError(
            f"Device ID is ambiguous: {device_id}. "
            "Select by index/link."
        )

    def clear(self) -> None:
        self._active = None
        self._auto_selected = False

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def print_candidates(self) -> None:
        print()
        print("=" * 78)
        print("RIGEL GCS - MAVLink DEVICE SELECTION")
        print("=" * 78)

        if not self._candidates:
            print("No MAVLink devices discovered.")
            return

        print(
            f"Found {len(self._candidates)} device(s)."
        )
        print()

        for c in self._candidates:
            print(
                f"[{c.index}] "
                f"{c.transport:<6} "
                f"SYSID={c.sysid:<3} "
                f"COMPID={c.compid:<3}"
            )
            print(
                f"    RX : {c.rx_endpoint}"
            )
            print(
                f"    TX : {c.tx_endpoint}"
            )
            print(
                f"    Link: {c.link_key}"
            )
            print()

        if len(self._candidates) == 1:
            c = self._candidates[0]
            print(
                f"AUTO SELECT -> "
                f"[{c.index}] {c.display_name}"
            )
        else:
            print(
                "MULTIPLE DEVICES DETECTED."
            )
            print(
                "Manual selection is REQUIRED."
            )

        print("=" * 78)

    def require_selection(self) -> VehicleCandidate:
        """
        Interactive selection.

        Exactly one device:
            returns it automatically.

        More than one:
            asks user to select.

        Zero:
            raises RuntimeError.
        """

        count = len(self._candidates)

        if count == 0:
            raise RuntimeError(
                "No MAVLink device available."
            )

        if count == 1:
            self._active = self._candidates[0]
            self._auto_selected = True
            return self._active

        self.print_candidates()

        while True:
            raw = input(
                f"Select device [1-{count}]: "
            ).strip()

            try:
                index = int(raw)
            except ValueError:
                print("Please enter a number.")
                continue

            try:
                return self.select(index)
            except ValueError as exc:
                print(exc)
