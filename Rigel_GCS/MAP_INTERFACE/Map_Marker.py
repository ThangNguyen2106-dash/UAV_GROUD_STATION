class MapMaker:
    """
    Tạo và quản lý các đối tượng hiển thị trên Map.

    MapMaker không quyết định map provider.
    """

    def __init__(self, map_widget):

        self.map_widget = map_widget

        self.uav_marker = None
        self.home_marker = None

        self.waypoint_markers = []
        self.route = None

    # =========================================================
    # UAV
    # =========================================================

    def create_uav_marker(
        self,
        lat,
        lon
    ):

        self.uav_marker = {
            "lat": lat,
            "lon": lon
        }

        self.map_widget.add_marker(
            lat,
            lon,
            "UAV"
        )

    def update_uav(
        self,
        lat,
        lon
    ):

        if self.uav_marker is None:

            self.create_uav_marker(
                lat,
                lon
            )

            return

        self.uav_marker["lat"] = lat
        self.uav_marker["lon"] = lon

        self.map_widget.update_marker(
            "UAV",
            lat,
            lon
        )

    # =========================================================
    # HOME
    # =========================================================

    def create_home_marker(
        self,
        lat,
        lon
    ):

        self.home_marker = {
            "lat": lat,
            "lon": lon
        }

        self.map_widget.add_marker(
            lat,
            lon,
            "HOME"
        )

    def update_home(
        self,
        lat,
        lon
    ):

        if self.home_marker is None:

            self.create_home_marker(
                lat,
                lon
            )

            return

        self.home_marker["lat"] = lat
        self.home_marker["lon"] = lon

        self.map_widget.update_marker(
            "HOME",
            lat,
            lon
        )

    # =========================================================
    # WAYPOINT
    # =========================================================

    def create_waypoint(
        self,
        lat,
        lon,
        index
    ):

        waypoint = {
            "index": index,
            "lat": lat,
            "lon": lon
        }

        self.waypoint_markers.append(
            waypoint
        )

        self.map_widget.add_marker(
            lat,
            lon,
            f"WP{index}"
        )

    def clear_waypoints(self):

        for waypoint in self.waypoint_markers:

            self.map_widget.remove_marker(
                f"WP{waypoint['index']}"
            )

        self.waypoint_markers.clear()

    # =========================================================
    # ROUTE
    # =========================================================

    def draw_route(
        self,
        points
    ):

        self.route = points

        self.map_widget.draw_route(
            points
        )

    def clear_route(self):

        self.route = None

        self.map_widget.clear_route()

    # =========================================================
    # CLEAR
    # =========================================================

    def clear_all(self):

        self.clear_waypoints()
        self.clear_route()

        self.map_widget.remove_marker(
            "UAV"
        )

        self.map_widget.remove_marker(
            "HOME"
        )

        self.uav_marker = None
        self.home_marker = None