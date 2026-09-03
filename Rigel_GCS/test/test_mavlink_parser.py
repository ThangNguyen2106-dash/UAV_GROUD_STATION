"""Tests for Rigel_GCS.mavlink.mavlink.

Run from the project root (RIGEL GROUD STATION):

    .\.venv\Scripts\python.exe -m Rigel_GCS.test.test_mavlink_parser

The tests generate real MAVLink frames with pymavlink, then feed them to
MAVLinkEngine in complete and fragmented chunks. No Serial/UDP device is
required for this test.
"""

from __future__ import annotations
from io import BytesIO
from pathlib import Path
import sys

# Make direct execution of this test file work too.  parents[2] is the
# project root: RIGEL GROUD STATION.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pymavlink import mavutil
from pymavlink.dialects.v10 import ardupilotmega as mavlink1
from pymavlink.dialects.v20 import ardupilotmega as mavlink2

from Rigel_GCS.mavlink import (
    MAVLinkEngine,
    MAVLinkMessage,
    MAVLINK_V1_STX,
    MAVLINK_V2_STX,
    normalize_message,
)


PASS = 0
FAIL = 0


def check(condition: bool, message: str) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {message}")
    else:
        FAIL += 1
        print(f"[FAIL] {message}")


def make_frame(protocol_version, sysid=1, compid=1):
    """
    Tạo một frame HEARTBEAT MAVLink thật để test parser.

    protocol_version:
        1 -> MAVLink 1.0
        2 -> MAVLink 2.0
    """

    if protocol_version == 1:
        from pymavlink.dialects.v10 import ardupilotmega as dialect

    elif protocol_version == 2:
        from pymavlink.dialects.v20 import ardupilotmega as dialect

    else:
        raise ValueError(
            f"Unsupported MAVLink protocol version: {protocol_version}"
        )

    # pymavlink cần một file-like object có .write()
    output = BytesIO()

    encoder = dialect.MAVLink(output)

    # Đặt source identity của vehicle
    encoder.srcSystem = int(sysid)
    encoder.srcComponent = int(compid)

    # Tạo HEARTBEAT
    encoder.heartbeat_send(
        dialect.MAV_TYPE_QUADROTOR,
        dialect.MAV_AUTOPILOT_ARDUPILOTMEGA,
        0,
        0,
        dialect.MAV_STATE_ACTIVE,
        3,
    )

    # Lấy toàn bộ bytes MAVLink đã encode
    frame = output.getvalue()

    if not frame:
        raise RuntimeError(
            f"Không tạo được MAVLink {protocol_version}.0 frame"
        )

    # Kiểm tra STX
    expected_stx = 0xFE if protocol_version == 1 else 0xFD

    if frame[0] != expected_stx:
        raise RuntimeError(
            f"MAVLink version mismatch: "
            f"expected STX=0x{expected_stx:02X}, "
            f"got=0x{frame[0]:02X}"
        )

    return frame


def test_protocol_marker_helper() -> None:
    print("\n=== TEST protocol marker helper ===")
    check(MAVLinkEngine.detect_protocol_version(b"\x00\xFE\x01") == 1,
          "detect_protocol_version detects MAVLink 1 marker")
    check(MAVLinkEngine.detect_protocol_version(b"\x00\xFD\x01") == 2,
          "detect_protocol_version detects MAVLink 2 marker")
    check(MAVLinkEngine.detect_protocol_version(b"\x00\x01\x02") is None,
          "detect_protocol_version returns None for non-MAVLink bytes")
    check(MAVLinkEngine.detect_protocol_version(b"") is None,
          "detect_protocol_version handles empty data")


def test_parse(protocol_version: int) -> bytes:
    print(f"\n=== TEST MAVLink {protocol_version}.0 ===")
    frame = make_frame(protocol_version, sysid=1, compid=1)
    received: list[MAVLinkMessage] = []
    engine = MAVLinkEngine(on_message=received.append)

    # Feed the frame in deliberately small chunks to verify parser state is
    # preserved across feed_bytes() calls.
    split_points = [1, 2, 5, 9, len(frame)]
    start = 0
    total = 0
    for end in split_points:
        end = min(end, len(frame))
        if end <= start:
            continue
        total += engine.feed_bytes(frame[start:end])
        start = end
        if start >= len(frame):
            break

    check(total == 1, f"MAVLink {protocol_version}.0 frame parsed exactly once")
    check(engine.message_count == 1,
          f"MAVLink {protocol_version}.0 message_count == 1")
    check(len(received) == 1,
          f"MAVLink {protocol_version}.0 callback fired once")

    if received:
        message = received[0]
        check(message.message_type == "HEARTBEAT",
              f"MAVLink {protocol_version}.0 message type is HEARTBEAT")
        check(message.sysid == 1,
              f"MAVLink {protocol_version}.0 SYSID == 1")
        check(message.compid == 1,
              f"MAVLink {protocol_version}.0 COMPID == 1")
        check(message.protocol_version == protocol_version,
              f"MAVLink {protocol_version}.0 wire version detected correctly")
        check(message.to_dict().get("mavpackettype") == "HEARTBEAT",
              "MAVLink wrapper to_dict() returns pymavlink message data")

        normalized = normalize_message(message)
        check(normalized["message_type"] == "HEARTBEAT",
              "normalize_message preserves message_type")
        check(normalized["sysid"] == 1 and normalized["compid"] == 1,
              "normalize_message preserves source identity")
        check(normalized["protocol_version"] == protocol_version,
              "normalize_message preserves protocol version")

    stats = engine.get_statistics()
    check(stats["protocol_counts"][protocol_version] == 1,
          f"statistics counts one MAVLink {protocol_version}.0 frame")
    check(stats["message_counts"]["HEARTBEAT"] == 1,
          "statistics counts HEARTBEAT")
    check(engine.get_protocol_version() == protocol_version,
          "get_protocol_version() returns last wire version")

    return frame


def test_reset() -> None:
    print("\n=== TEST reset ===")
    engine = MAVLinkEngine()
    frame = make_frame(2, sysid=9, compid=10)
    engine.feed_bytes(frame)
    check(engine.message_count == 1, "engine has state before reset")
    engine.reset()
    check(engine.message_count == 0, "reset clears message_count")
    check(engine.byte_count == 0, "reset clears byte_count")
    check(engine.last_message is None, "reset clears last_message")
    check(engine.get_protocol_version() is None, "reset clears protocol version")
    check(engine.target_system is None and engine.target_component is None,
          "reset clears target identity")


def test_normalize_none_safety() -> None:
    print("\n=== TEST normalize None safety ===")

    class Dummy:
        def get_type(self):
            return "GLOBAL_POSITION_INT"

        def get_srcSystem(self):
            return 1

        def get_srcComponent(self):
            return 1

        lat = None
        lon = None
        alt = None
        relative_alt = None
        vx = None
        vy = None
        vz = None
        hdg = 65535

    raw = Dummy()
    wrapped = MAVLinkMessage(raw, "GLOBAL_POSITION_INT", 1, 1, 2)
    normalized = normalize_message(wrapped)

    check(normalized["latitude"] is None,
          "GLOBAL_POSITION_INT handles missing latitude safely")
    check(normalized["longitude"] is None,
          "GLOBAL_POSITION_INT handles missing longitude safely")
    check(normalized["altitude"] is None,
          "GLOBAL_POSITION_INT handles missing altitude safely")
    check(normalized["heading"] is None,
          "GLOBAL_POSITION_INT handles unknown heading 65535")


def main() -> int:
    print("=" * 64)
    print("RIGEL GCS - MAVLink Parser Test")
    print("=" * 64)

    test_protocol_marker_helper()
    frame_v1 = test_parse(1)
    frame_v2 = test_parse(2)

    check(frame_v1[0] == MAVLINK_V1_STX,
          "generated MAVLink 1 frame starts with 0xFE")
    check(frame_v2[0] == MAVLINK_V2_STX,
          "generated MAVLink 2 frame starts with 0xFD")

    test_reset()
    test_normalize_none_safety()

    print("\n" + "=" * 64)
    print(f"RESULT: PASS={PASS} FAIL={FAIL}")
    print("=" * 64)

    if FAIL:
        print("[FAILED] MAVLink parser test")
        return 1

    print("[SUCCESS] MAVLink parser test PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
