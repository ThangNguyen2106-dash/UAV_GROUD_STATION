from Rigel_GCS.MAP_INTERFACE.Map_Coordinate import Coordinate
from Rigel_GCS.MAP_INTERFACE.Map_Provider import MapProvider
from Rigel_GCS.MAP_INTERFACE.Map_Marker import MapMaker


class MapManager:
    """
    Trung tâm quản lý hệ thống Map.

    MapManager kết nối:

        MapProvider
             ↓
        MapMaker
             ↓
        MapWidget
    """

    def __init__(self, map_widget):

        self.map_widget = map_widget

        self.provider = MapProvider()

        self.maker = MapMaker(
            map_widget
        )

        self.uav_position = None
        self.home_position = None

        self.waypoints = []

    # =========================================================
    # PROVIDER
    # =========================================================

    def set_map_provider(self, provider_name):

        self.provider.set_provider(
            provider_name
        )

        self.map_widget.set_tile_provider(
            self.provider.get_url(),
            self.provider.get_attribution(),
        )

    def get_map_provider(self):

        return self.provider.get_name()

    # =========================================================
    # MAP
    # =========================================================

    def set_center(
        self,
        lat,
        lon
    ):

        self.map_widget.set_center(
            lat,
            lon
        )

    def set_zoom(self, zoom):

        self.map_widget.set_zoom(
            zoom
        )

    # =========================================================
    # UAV
    # =========================================================

    def update_uav(
        self,
        lat,
        lon,
        alt=0.0,
        heading=0.0
    ):

        self.uav_position = Coordinate(
            lat,
            lon,
            alt
        )

        self.maker.update_uav(
            lat,
            lon
        )

    # =========================================================
    # HOME
    # =========================================================

    def set_home(
        self,
        lat,
        lon,
        alt=0.0
    ):

        self.home_position = Coordinate(
            lat,
            lon,
            alt
        )

        self.maker.create_home_marker(
            lat,
            lon
        )

    # =========================================================
    # WAYPOINT
    # =========================================================

    def add_waypoint(
        self,
        lat,
        lon,
        alt=0.0
    ):

        coordinate = Coordinate(
            lat,
            lon,
            alt
        )

        self.waypoints.append(
            coordinate
        )

        index = len(
            self.waypoints
        )

        self.maker.create_waypoint(
            lat,
            lon,
            index
        )

        self._update_route()

    def remove_waypoint(self, index):

        if index < 0:
            return

        if index >= len(
            self.waypoints
        ):
            return

        self.waypoints.pop(index)

        self.maker.clear_waypoints()

        for i, waypoint in enumerate(
            self.waypoints,
            start=1
        ):

            self.maker.create_waypoint(
                waypoint.lat,
                waypoint.lon,
                i
            )

        self._update_route()

    def clear_waypoints(self):

        self.waypoints.clear()

        self.maker.clear_waypoints()

        self.maker.clear_route()

    # =========================================================
    # ROUTE
    # =========================================================

    def _update_route(self):

        points = [
            (
                waypoint.lat,
                waypoint.lon
            )
            for waypoint
            in self.waypoints
        ]

        if len(points) >= 2:

            self.maker.draw_route(
                points
            )

        else:

            self.maker.clear_route()

    # =========================================================
    # MISSION
    # =========================================================

    def get_mission(self):

        return [
            {
                "index": index + 1,
                "lat": waypoint.lat,
                "lon": waypoint.lon,
                "alt": waypoint.alt
            }

            for index, waypoint
            in enumerate(
                self.waypoints
            )
        ]

    # =========================================================
    # RESET
    # =========================================================

    def clear_map_objects(self):

        self.waypoints.clear()

        self.uav_position = None
        self.home_position = None

        self.maker.clear_all()