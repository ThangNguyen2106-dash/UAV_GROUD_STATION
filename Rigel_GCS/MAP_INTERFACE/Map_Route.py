class MapRouteManager:

    def __init__(self, map_widget):

        self.map_widget = map_widget

        self.route = None

    def update(self, waypoints):

        self.clear()

        if len(waypoints) < 2:

            return

        points = []

        for waypoint in waypoints:

            points.append(
                (
                    waypoint.latitude,
                    waypoint.longitude
                )
            )

        self.route = (
            self.map_widget.set_path(
                points
            )
        )

    def clear(self):

        if self.route:

            self.route.delete()

            self.route = None