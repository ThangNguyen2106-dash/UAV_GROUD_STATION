from dataclasses import dataclass
import math


@dataclass
class Coordinate:
    """
    Đại diện cho một tọa độ GPS.

    lat:
        Latitude, đơn vị độ.

    lon:
        Longitude, đơn vị độ.

    alt:
        Altitude, đơn vị mét.
    """

    lat: float
    lon: float
    alt: float = 0.0

    def __post_init__(self):
        self.lat = float(self.lat)
        self.lon = float(self.lon)
        self.alt = float(self.alt)

    def is_valid(self):
        return (
            -90.0 <= self.lat <= 90.0
            and -180.0 <= self.lon <= 180.0
        )

    def copy(self):
        return Coordinate(
            self.lat,
            self.lon,
            self.alt
        )

    def distance_to(self, other):
        """
        Khoảng cách giữa 2 GPS coordinate.
        Trả về mét.
        """

        earth_radius = 6371000.0

        lat1 = math.radians(self.lat)
        lat2 = math.radians(other.lat)

        dlat = math.radians(other.lat - self.lat)
        dlon = math.radians(other.lon - self.lon)

        a = (
            math.sin(dlat / 2) ** 2
            +
            math.cos(lat1)
            * math.cos(lat2)
            * math.sin(dlon / 2) ** 2
        )

        c = 2 * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )

        return earth_radius * c

    def bearing_to(self, other):
        """
        Tính hướng từ coordinate hiện tại
        tới coordinate khác.

        Kết quả:
            0   = Bắc
            90  = Đông
            180 = Nam
            270 = Tây
        """

        lat1 = math.radians(self.lat)
        lat2 = math.radians(other.lat)

        dlon = math.radians(other.lon - self.lon)

        x = math.sin(dlon) * math.cos(lat2)

        y = (
            math.cos(lat1) * math.sin(lat2)
            -
            math.sin(lat1)
            * math.cos(lat2)
            * math.cos(dlon)
        )

        bearing = math.degrees(
            math.atan2(x, y)
        )

        return (bearing + 360) % 360

    def to_tuple(self):
        return (
            self.lat,
            self.lon,
            self.alt
        )

    @classmethod
    def from_tuple(cls, value):
        return cls(
            value[0],
            value[1],
            value[2] if len(value) > 2 else 0.0
        )

    def __repr__(self):
        return (
            f"Coordinate("
            f"lat={self.lat:.7f}, "
            f"lon={self.lon:.7f}, "
            f"alt={self.alt:.2f})"
        )