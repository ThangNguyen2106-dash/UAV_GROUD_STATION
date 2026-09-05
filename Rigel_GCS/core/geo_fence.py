"""Geo-Fence, No-Fly Zone (NFZ), and Border Safety System for RIGEL GCS.

Provides geographic datasets and proximity detection for major airports, military
installations, high-security zones, and national boundaries in Vietnam and surrounding airspace.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class NoFlyZone:
    id: str
    name: str
    code: str
    lat: float
    lon: float
    prohibited_radius_m: float  # Red zone: absolute no-fly (Core 4-5km)
    restricted_radius_m: float  # Yellow zone: altitude/permit restricted (8-10km)
    category: str  # 'civil_airport', 'military_airbase', 'security_zone'
    description: str


# Comprehensive No-Fly Zones Database (Vietnam Civil & Military Airspace)
NO_FLY_ZONES: List[NoFlyZone] = [
    NoFlyZone(
        id="NFZ-VVNB",
        name="Sân bay Quốc tế Nội Bài (HAN)",
        code="VVNB",
        lat=21.2212,
        lon=105.8072,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Vùng kiểm soát tiếp cận sân bay quốc tế Nội Bài - Cấm bay tuyệt đối mọi phương tiện bay không người lái.",
    ),
    NoFlyZone(
        id="NFZ-VVTS",
        name="Sân bay Quốc tế Tân Sơn Nhất (SGN)",
        code="VVTS",
        lat=10.8188,
        lon=106.6519,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Vùng kiểm soát tiếp cận sân bay Tân Sơn Nhất - Cấm bay nghiêm ngặt trong khu vực nội đô TP.HCM.",
    ),
    NoFlyZone(
        id="NFZ-VVDN",
        name="Sân bay Quốc tế Đà Nẵng (DAD)",
        code="VVDN",
        lat=16.0439,
        lon=108.1994,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Quốc tế & Căn cứ Không quân Đà Nẵng.",
    ),
    NoFlyZone(
        id="NFZ-VVCI",
        name="Sân bay Quốc tế Cát Bi (HPH)",
        code="VVCI",
        lat=20.8192,
        lon=106.7247,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Quốc tế Cát Bi - Hải Phòng.",
    ),
    NoFlyZone(
        id="NFZ-VVCR",
        name="Sân bay Quốc tế Cam Ranh (CXR)",
        code="VVCR",
        lat=11.9981,
        lon=109.2194,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Quốc tế Cam Ranh & Vùng căn cứ Hải quân Cam Ranh.",
    ),
    NoFlyZone(
        id="NFZ-VVGL",
        name="Sân bay Quân sự Gia Lâm",
        code="VVGL",
        lat=21.0378,
        lon=105.8878,
        prohibited_radius_m=4000.0,
        restricted_radius_m=8000.0,
        category="military_airbase",
        description="Sân bay quân sự & Trung đoàn Không quân 916/918.",
    ),
    NoFlyZone(
        id="NFZ-VVHL",
        name="Sân bay Quân sự Hòa Lạc",
        code="VVHL",
        lat=21.0381,
        lon=105.5342,
        prohibited_radius_m=4500.0,
        restricted_radius_m=9000.0,
        category="military_airbase",
        description="Căn cứ Không quân Hòa Lạc & Khu vực thử nghiệm quân sự.",
    ),
    NoFlyZone(
        id="NFZ-VVPQ",
        name="Sân bay Quốc tế Phú Quốc (PQC)",
        code="VVPQ",
        lat=10.1698,
        lon=103.9931,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Quốc tế Phú Quốc - Kiên Giang.",
    ),
    NoFlyZone(
        id="NFZ-VVCT",
        name="Sân bay Quốc tế Cần Thơ (VCA)",
        code="VVCT",
        lat=10.0851,
        lon=105.7119,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Quốc tế Cần Thơ.",
    ),
    NoFlyZone(
        id="NFZ-VVPB",
        name="Sân bay Quốc tế Phú Bài (HUI)",
        code="VVPB",
        lat=16.4008,
        lon=107.7028,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Quốc tế Phú Bài - Thừa Thiên Huế.",
    ),
    NoFlyZone(
        id="NFZ-VVDL",
        name="Sân bay Liên Khương (DLI)",
        code="VVDL",
        lat=11.7506,
        lon=108.3733,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Liên Khương - Đà Lạt.",
    ),
    NoFlyZone(
        id="NFZ-VVBH",
        name="Sân bay Quân sự Biên Hòa",
        code="VVBH",
        lat=10.9719,
        lon=106.8186,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="military_airbase",
        description="Căn cứ Không quân Biên Hòa - Trung đoàn Không quân 935.",
    ),
    NoFlyZone(
        id="NFZ-VVTX",
        name="Sân bay Thọ Xuân (THD)",
        code="VVTX",
        lat=19.9011,
        lon=105.4678,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Thọ Xuân & Trung đoàn Không quân 923 - Thanh Hóa.",
    ),
    NoFlyZone(
        id="NFZ-VVVH",
        name="Sân bay Quốc tế Vinh (VII)",
        code="VVVH",
        lat=18.7275,
        lon=105.6706,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Quốc tế Vinh - Nghệ An.",
    ),
    NoFlyZone(
        id="NFZ-VVCL",
        name="Sân bay Chu Lai (VCL)",
        code="VVCL",
        lat=15.4061,
        lon=108.7056,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Chu Lai - Quảng Nam.",
    ),
    NoFlyZone(
        id="NFZ-VVPC",
        name="Sân bay Phù Cát (UIH)",
        code="VVPC",
        lat=13.9550,
        lon=109.0425,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Phù Cát & Căn cứ Không quân 925 - Bình Định.",
    ),
    NoFlyZone(
        id="NFZ-VVPK",
        name="Sân bay Pleiku (PXU)",
        code="VVPK",
        lat=14.0044,
        lon=108.0169,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Pleiku - Gia Lai.",
    ),
    NoFlyZone(
        id="NFZ-VVBM",
        name="Sân bay Buôn Ma Thuột (BMV)",
        code="VVBM",
        lat=12.6681,
        lon=108.1203,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Buôn Ma Thuột - Đắk Lắk.",
    ),
    NoFlyZone(
        id="NFZ-VVDH",
        name="Sân bay Đồng Hới (VDH)",
        code="VVDH",
        lat=17.5150,
        lon=106.5906,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Đồng Hới - Quảng Bình.",
    ),
    NoFlyZone(
        id="NFZ-VVTH",
        name="Sân bay Tuy Hòa (TBB)",
        code="VVTH",
        lat=13.0494,
        lon=109.3339,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Tuy Hòa - Phú Yên.",
    ),
    NoFlyZone(
        id="NFZ-VVDN-DBP",
        name="Sân bay Điện Biên Phủ (DIN)",
        code="VVDB",
        lat=21.3972,
        lon=103.0078,
        prohibited_radius_m=5000.0,
        restricted_radius_m=10000.0,
        category="civil_airport",
        description="Sân bay Điện Biên Phủ - Điện Biên.",
    ),
    NoFlyZone(
        id="NFZ-VVCS",
        name="Sân bay Côn Đảo (VCS)",
        code="VVCS",
        lat=8.7328,
        lon=106.6328,
        prohibited_radius_m=4000.0,
        restricted_radius_m=8000.0,
        category="civil_airport",
        description="Sân bay Côn Đảo - Bà Rịa - Vũng Tàu.",
    ),
    NoFlyZone(
        id="NFZ-SEC-BD",
        name="Khu vực Trung tâm Chính trị Ba Đình (Hà Nội)",
        code="SEC-BD",
        lat=21.0366,
        lon=105.8347,
        prohibited_radius_m=2500.0,
        restricted_radius_m=5000.0,
        category="security_zone",
        description="Khu vực trọng điểm an ninh quốc gia, cơ quan đầu não Trung ương Đảng & Nhà nước.",
    ),
]


# National Border Line Vectors (Key geographic boundary coordinates)
NATIONAL_BORDERS = [
    {
        "name": "Biên giới Việt Nam - Trung Quốc (Phía Bắc)",
        "coordinates": [
            [22.4000, 102.1500],
            [22.6500, 103.0000],
            [22.8500, 103.6500],
            [23.3800, 105.3000],  # Lũng Cú, Hà Giang
            [23.1000, 105.9000],
            [22.8000, 106.7000],
            [21.8500, 107.5500],
            [21.5300, 107.9700],  # Móng Cái, Quảng Ninh
        ],
    },
    {
        "name": "Biên giới Việt Nam - Lào (Phía Tây)",
        "coordinates": [
            [22.4000, 102.1500],  # A Pa Chải
            [21.5000, 103.0000],
            [20.7000, 104.2000],
            [19.8000, 104.9000],
            [18.4000, 105.2000],
            [17.4000, 106.2000],
            [16.2000, 107.3000],
            [14.7000, 107.5500],  # Ngã 3 Đông Dương
        ],
    },
    {
        "name": "Biên giới Việt Nam - Campuchia (Tây Nam)",
        "coordinates": [
            [14.7000, 107.5500],  # Ngã 3 Đông Dương
            [13.5000, 107.5000],
            [12.3000, 106.8000],
            [11.5000, 106.0000],
            [10.9500, 105.8000],
            [10.7000, 105.1000],
            [10.4000, 104.4500],  # Hà Tiên, Kiên Giang
        ],
    },
]


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in meters between two points on the Earth."""
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


@dataclass
class AirspaceCheckResult:
    is_inside_prohibited: bool
    is_inside_restricted: bool
    nearest_zone: Optional[NoFlyZone]
    distance_to_nearest_m: float
    message: str


def check_airspace(lat: float, lon: float) -> AirspaceCheckResult:
    """Check whether a given GPS coordinate infringes any No-Fly Zone or restricted area."""
    nearest_zone: Optional[NoFlyZone] = None
    min_dist = float("inf")
    inside_prohibited = False
    inside_restricted = False

    for zone in NO_FLY_ZONES:
        dist = haversine_distance_m(lat, lon, zone.lat, zone.lon)
        if dist < min_dist:
            min_dist = dist
            nearest_zone = zone

        if dist <= zone.prohibited_radius_m:
            inside_prohibited = True
        elif dist <= zone.restricted_radius_m:
            inside_restricted = True

    if nearest_zone is None:
        return AirspaceCheckResult(
            is_inside_prohibited=False,
            is_inside_restricted=False,
            nearest_zone=None,
            distance_to_nearest_m=0.0,
            message="Không gian bay an toàn.",
        )

    if inside_prohibited:
        msg = f"⛔ VI PHẠM VÙNG CẤM BAY: Bạn đang trong bán kính cấm bay của {nearest_zone.name} ({min_dist:.0f}m)!"
    elif inside_restricted:
        msg = f"⚠️ CẢNH BÁO: Bạn đang trong vùng hạn chế bay của {nearest_zone.name} (cách {min_dist / 1000.0:.1f}km)."
    elif min_dist <= (nearest_zone.restricted_radius_m + 3000.0):
        msg = f"ℹ️ Tiếp cận vùng hạn chế: {nearest_zone.name} cách {(min_dist / 1000.0):.1f}km."
    else:
        msg = "Không gian bay an toàn (Không nằm trong vùng cấm)."

    return AirspaceCheckResult(
        is_inside_prohibited=inside_prohibited,
        is_inside_restricted=inside_restricted,
        nearest_zone=nearest_zone,
        distance_to_nearest_m=min_dist,
        message=msg,
    )
