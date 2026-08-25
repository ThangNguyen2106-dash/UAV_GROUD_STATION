from dataclasses import dataclass


@dataclass
class TileProvider:
    name: str
    url: str
    attribution: str = ""


class MapProvider:
    """
    Quản lý nguồn bản đồ cho RIGEL GCS.

    MapProvider chỉ chịu trách nhiệm:

        - Tile server
        - Map source
        - Provider configuration

    Không xử lý:

        - UAV
        - Waypoint
        - Mission
        - Route
        - Telemetry
    """

    OSM = TileProvider(
        name="OpenStreetMap",
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        attribution="© OpenStreetMap contributors"
    )

    ESRI_SATELLITE = TileProvider(
        name="Esri Satellite",
        url=(
            "https://server.arcgisonline.com/"
            "ArcGIS/rest/services/"
            "World_Imagery/"
            "MapServer/tile/{z}/{y}/{x}"
        ),
        attribution="© Esri"
    )

    ESRI_STREET = TileProvider(
        name="Esri Street",
        url=(
            "https://server.arcgisonline.com/"
            "ArcGIS/rest/services/"
            "World_Street_Map/"
            "MapServer/tile/{z}/{y}/{x}"
        ),
        attribution="© Esri"
    )

    def __init__(self):

        self.providers = {
            "osm": self.OSM,
            "esri_satellite": self.ESRI_SATELLITE,
            "esri_street": self.ESRI_STREET,
        }

        self.current_provider = self.OSM

    def add_provider(
        self,
        key,
        name,
        url,
        attribution=""
    ):

        self.providers[key] = TileProvider(
            name=name,
            url=url,
            attribution=attribution
        )

    def set_provider(self, key):

        if key not in self.providers:
            raise ValueError(
                f"Unknown map provider: {key}"
            )

        self.current_provider = self.providers[key]

    def get_provider(self):

        return self.current_provider

    def get_url(self):

        return self.current_provider.url

    def get_name(self):

        return self.current_provider.name

    def get_attribution(self):

        return self.current_provider.attribution

    def list_providers(self):

        return {
            key: provider.name
            for key, provider
            in self.providers.items()
        }