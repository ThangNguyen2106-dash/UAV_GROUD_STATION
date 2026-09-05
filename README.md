# RIGEL GCS — UAV Ground Control Station

Phần mềm trạm điều khiển mặt đất (Ground Control Station) cho UAV RIGEL, xây dựng trên **Python + PySide6**, giao tiếp với Flight Controller (ArduPilot) qua giao thức **MAVLink**.

Đây là Module M1–M12 (Phase 1) trong lộ trình phát triển tổng thể của dự án RIGEL UAV — xem [Roadmap dự án](#roadmap-dự-án) bên dưới.

## Tính năng hiện có

| Khu vực | Trạng thái | Ghi chú |
|---|---|---|
| Kết nối MAVLink (Serial / UDP) | ✅ Đã có | `Rigel_GCS/core/connection_manager.py`, `mavlink_session.py` — hỗ trợ đa liên kết, đa thiết bị (multi-vehicle) |
| Giải mã MAVLink 1.0/2.0 & telemetry | ✅ Đã có | `Rigel_GCS/mavlink/mavlink.py`, `messages.py`, `telemetry.py` |
| HUD: Artificial Horizon, Compass, Flight Status | ✅ Đã có | `Rigel_GCS/ui/vehicle_panel/hud/` |
| Bản đồ, Waypoint, Mission Planner | ✅ Đã có | `Rigel_GCS/ui/map/`, `Rigel_GCS/ui/mission/` (dùng Qt WebEngine) |
| Điều khiển bay (ARM, RTL, Flight Mode) | ✅ Đã có | `Rigel_GCS/ui/controls/` |
| Ghi log telemetry | ✅ Đã có | `Rigel_GCS/core/telemetry_logger.py` |
| Camera/Video streaming, Parameters, Failsafe UI, User management | 🕒 Chưa triển khai | Xem Module M5, M8, M9, M10 trong roadmap |

## Cài đặt

Yêu cầu Python 3.11+.

```bash
pip install -r requirements.txt
```

> Lưu ý: phải cài `PySide6` bản đầy đủ (không chỉ `PySide6-Essentials`) vì module bản đồ dùng `QtWebEngineWidgets`, nằm trong gói `PySide6-Addons` được `PySide6` kéo theo tự động.

## Chạy ứng dụng

```bash
python main.py
```

## Cấu trúc mã nguồn

```text
UAV_GROUND_STATION_DEMO_CLONE/
├── main.py                          # Composition root, khởi chạy ứng dụng
├── requirements.txt
└── Rigel_GCS/
    ├── core/                        # Kết nối, phiên MAVLink, quản lý thiết bị
    │   ├── connection_manager.py    # Quản lý nhiều liên kết (Serial/UDP) đồng thời
    │   ├── mavlink_session.py       # Parse MAVLink, heartbeat, request telemetry
    │   ├── active_vehicle.py        # Chọn vehicle đang hoạt động (multi-vehicle)
    │   ├── device.py / device_registry.py
    │   ├── auto_discovery_manager.py
    │   ├── discovery/                # Serial/UDP auto-discovery
    │   ├── transports/               # SerialTransport, UDPTransport
    │   └── telemetry_logger.py
    ├── mavlink/                      # Lớp giao thức MAVLink & telemetry state
    │   ├── mavlink.py
    │   ├── messages.py
    │   └── telemetry.py
    ├── ui/
    │   ├── main_window.py            # Cửa sổ chính
    │   ├── topbar/                   # Thanh chọn kết nối / vehicle
    │   ├── vehicle_panel/hud/        # Artificial Horizon, Compass, Flight Status
    │   ├── map/                      # Bản đồ, waypoint, track, vehicle marker
    │   ├── mission/                  # Mission planner, danh sách waypoint
    │   └── controls/                 # ARM, RTL, Flight Mode
    └── test/                         # Unit test
```

## Roadmap dự án

Toàn bộ chi tiết task, tiêu chí nghiệm thu và timeline nằm trong tài liệu quản lý dự án:
`PLG_PM_DRONE_RIGEL/PM/Drone_Rigel_Tech_v1.0_TASK_PHASE.docx`

Tóm tắt 3 giai đoạn:

| Phase | Nội dung | Thời lượng | Nhân sự |
|---|---|---|---|
| 🔴 Phase 1 — GCS Core Platform | Phần mềm trạm điều khiển mặt đất (repo này): 12 module M1–M12, từ kết nối MAVLink đến cấu hình hệ thống | 12 tuần (~3 tháng) | Embedded/Protocol, Frontend, GIS, Control, Media, Backend, Fullstack Dev |
| 🟠 Phase 2 — Hardware Integration & QC | Lắp ráp phần cứng, nạp firmware ArduPilot, hiệu chuẩn, PID tuning, quy trình QC 8 bước | 8 tuần (~2 tháng) | Hardware & Embedded Engineers |
| 🟡 Phase 3 — Hệ thống AI phân tích dữ liệu đa thời gian | Ghép ảnh Orthomosaic/DSM/DEM, AI phát hiện biến động 2D/3D, nền tảng WebGIS | 16 tuần (~4 tháng) | AI / Data / WebGIS Team |

**Tổng:** 3 phase · 97+ task · ~36 tuần (~9 tháng).

### Phase 1 — 12 module (repo này)

| Module | Nội dung | Thời gian | Phụ trách |
|---|---|---|---|
| M1 | Kết nối & Truyền thông MAVLink | 1.5 tuần | Embedded / Protocol Dev |
| M2 | Giám sát bay & HUD 3D | 1 tuần | Frontend / Graphics Dev |
| M3 | Bản đồ & Quản lý Waypoint | 2 tuần | GIS / UI Dev |
| M4 | Điều khiển bay (One-Click Control) | 1.5 tuần | Safety / Control Dev |
| M5 | Camera & Video Streaming | 2 tuần | Media / Streaming Dev |
| M6 | Trạng thái hệ thống (Pin/GPS) | 1 tuần | UI Dev |
| M7 | Nhật ký & Cảnh báo | 1 tuần | Backend Dev |
| M8 | Quản lý tham số cấu hình (Parameters) | 1.5 tuần | Embedded Dev |
| M9 | Failsafe & An toàn bay | 1.5 tuần | Control / QA Lead |
| M10 | Quản lý người dùng & Nhật ký thao tác | 1 tuần | Fullstack Dev |
| M11 | Lưu trữ Dữ liệu Ảnh & Geotag | 1.5 tuần | Data / UI Dev |
| M12 | Cấu hình Hệ thống (Settings) | 1 tuần | Fullstack Dev |

## Nhánh Git

- `main` — nhánh phát triển chính.
- `PLG` — nhánh dùng để triển khai/thử nghiệm nội bộ, đồng bộ định kỳ từ `main`.
