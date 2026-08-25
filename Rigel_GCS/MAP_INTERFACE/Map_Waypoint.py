from dataclasses import dataclass


@dataclass
class Waypoint:

    id: str

    latitude: float
    longitude: float

    altitude: float = 50.0
    speed: float = 10.0

    hold_time: float = 0.0

    def as_dict(self):

        return {
            "id": self.id,
            "lat": self.latitude,
            "lon": self.longitude,
            "alt": self.altitude,
            "speed": self.speed,
            "hold_time": self.hold_time,
        }

    def coordinate(self):

        return (
            self.latitude,
            self.longitude
        )