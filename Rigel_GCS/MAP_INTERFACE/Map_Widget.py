"""
Map display widget for RIGEL Ground Station.

UI layer:
    - Display map.
    - Zoom / pan.
    - Handle map click.
    - Create waypoint from GPS coordinates.
    - Display waypoint markers.
    - Draw mission route.

Map logic such as:
    - Mission upload
    - MAVLink
    - Flight controller
    - Telemetry

must remain outside this widget.
"""

import time
import tkinter as tk

from tkintermapview import TkinterMapView


class MapWidget(TkinterMapView):
    """
    Concrete map widget mounted into UI.Map_Container.

    Supports:

        Normal mode:
            - Pan map
            - Zoom map
            - Select existing map objects

        Waypoint mode:
            - Click map
            - Convert click position to GPS
            - Create waypoint
            - Draw marker
            - Draw mission route
    """

    # =========================================================
    # MAP SETTINGS
    # =========================================================

    HOME_LAT = 10.8231
    HOME_LON = 106.6297
    HOME_ZOOM = 12

    MIN_ZOOM = 1
    MAX_ZOOM = 19

    # =========================================================
    # INIT
    # =========================================================

    def __init__(self, parent, **kwargs):

        # =====================================================
        # MOUSE WHEEL STATE
        # =====================================================

        self._last_wheel_time = 0.0

        # =====================================================
        # INITIALIZE TKINTERMAPVIEW
        # =====================================================

        super().__init__(
            parent,
            corner_radius=0,
            **kwargs,
        )

        # =====================================================
        # INTERNAL OBJECT STORAGE
        # =====================================================

        self._markers = {}
        self._routes = {}
        self._attribution = ""

        # =====================================================
        # WAYPOINT STATE
        # =====================================================

        # True:
        #     Click map creates waypoint.
        #
        # False:
        #     Click map does not create waypoint.
        #
        self.waypoint_mode = False
        # Mission editing is allowed only while SETUP mode is ON.
        self.mission_edit_enabled = False

        # Internal waypoint list.
        #
        # Example:
        #
        # [
        #     {
        #         "index": 1,
        #         "lat": 10.8231,
        #         "lon": 106.6297,
        #         "alt": 50.0,
        #         "speed": 10.0,
        #     },
        # ]
        #
        self.waypoints = []

        # HOME point: the mission's starting position, placed by the
        # first map click after SETUP is enabled. All later clicks
        # create WP1, WP2, ... The mission route is drawn starting
        # from HOME.
        self.home_point = None

        # Callback called whenever HOME is placed or moved.
        #
        # callback(home_dict | None)
        #
        self._home_callback = None

        # Callback called whenever a new waypoint
        # is created.
        #
        # callback(waypoint)
        #
        self._waypoint_callback = None

        # Callback called when a waypoint is selected.
        #
        # callback(index)
        #
        self._waypoint_select_callback = None

        # Called after a waypoint is moved.
        self._waypoint_update_callback = None

        # Optional safety gate supplied by MainWindow/controller.
        # callback(index) -> True when this waypoint may be moved.
        self._waypoint_edit_callback = None

        # True while the pointer is dragging a waypoint marker.
        self._dragging_waypoint = False
        self._drag_waypoint_index = None

        # =====================================================
        # INITIAL MAP VIEW
        # =====================================================

        self.set_position(
            self.HOME_LAT,
            self.HOME_LON,
        )

        self.set_zoom(
            self.HOME_ZOOM
        )

        # =====================================================
        # MOUSE WHEEL
        # =====================================================

        # Windows
        self.bind(
            "<MouseWheel>",
            self._on_mousewheel,
            add="+",
        )

        # Linux
        self.bind(
            "<Button-4>",
            self._on_mousewheel,
            add="+",
        )

        self.bind(
            "<Button-5>",
            self._on_mousewheel,
            add="+",
        )

        # =====================================================
        # KEYBOARD ZOOM
        # =====================================================

        self.bind(
            "<KeyPress-plus>",
            lambda event: self._zoom_and_break(1),
        )

        self.bind(
            "<KeyPress-equal>",
            lambda event: self._zoom_and_break(1),
        )

        self.bind(
            "<KeyPress-minus>",
            lambda event: self._zoom_and_break(-1),
        )

        self.bind(
            "<KeyPress-0>",
            lambda event: self._go_home_and_break(),
        )

        # =====================================================
        # FOCUS
        # =====================================================

        self.bind(
            "<Enter>",
            self._on_enter,
            add="+",
        )

        # Intercept B1-Motion / ButtonRelease-1 BEFORE TkinterMapView's own
        # pan handlers by prepending a synthetic bindtag to the canvas.
        # Tk processes bindtags in order and a "break" from an earlier tag
        # stops later ones (including the base pan handlers) from running
        # for that same event. Without this, dragging a waypoint/HOME
        # marker also panned the map underneath it, since our old
        # add="+" handlers ran AFTER (not instead of) the base pan logic.
        self.canvas.bindtags(
            ("WaypointDragIntercept",) + self.canvas.bindtags()
        )
        self.canvas.bind_class(
            "WaypointDragIntercept",
            "<B1-Motion>",
            self._intercept_drag_motion,
        )
        self.canvas.bind_class(
            "WaypointDragIntercept",
            "<ButtonRelease-1>",
            self._intercept_drag_release,
        )

        # =====================================================
        # MAP CLICK
        # =====================================================

        # TkinterMapView provides GPS coordinates directly
        # when the map is clicked.
        #
        # The callback receives:
        #
        #     (latitude, longitude)
        #
        try:

            self.add_left_click_map_command(
                self._on_map_click
            )

        except Exception as error:

            print(
                "[MapWidget] "
                f"Cannot register map click: {error}"
            )

    # =========================================================
    # WAYPOINT MODE
    # =========================================================

    def enable_waypoint_mode(self):
        """
        Enable waypoint creation.

        After this is enabled:

            click map
                ↓
            create waypoint
        """

        self.waypoint_mode = True
        self.mission_edit_enabled = True

        print(
            "[MapWidget] "
            "WAYPOINT MODE: ON"
        )

    def disable_waypoint_mode(self):
        """
        Disable waypoint creation.
        """

        self.waypoint_mode = False
        # Mission editing is allowed only while SETUP mode is ON.
        self.mission_edit_enabled = False

        print(
            "[MapWidget] "
            "WAYPOINT MODE: OFF"
        )

    def toggle_waypoint_mode(self):
        """
        Toggle waypoint creation mode.

        Returns:
            True  -> enabled
            False -> disabled
        """

        if self.waypoint_mode:

            self.disable_waypoint_mode()

        else:

            self.enable_waypoint_mode()

        return self.waypoint_mode

    def set_mission_edit_enabled(self, enabled):
        """Enable mission editing independently of SETUP button state.

        Used by the flight UI to allow editing while PAUSED.
        """
        self.mission_edit_enabled = bool(enabled)

    def is_mission_edit_enabled(self):
        return bool(self.mission_edit_enabled)

    def is_waypoint_mode_enabled(self):
        """
        Return current waypoint mode state.
        """

        return self.waypoint_mode

    # =========================================================
    # WAYPOINT CALLBACK
    # =========================================================

    def set_waypoint_callback(self, callback):
        """
        Register callback for new waypoint.

        callback receives:

            {
                "index": 1,
                "lat": 10.8231,
                "lon": 106.6297,
                "alt": 50.0,
                "speed": 10.0,
            }
        """

        self._waypoint_callback = callback

    def set_home_callback(self, callback):
        """Register callback fired whenever HOME is placed or moved.

        callback(home_dict) where home_dict is {"lat": ..., "lon": ...}
        """
        self._home_callback = callback

    def set_waypoint_update_callback(self, callback):
        """Register callback after a waypoint is moved.

        callback(waypoint_dict)
        """
        self._waypoint_update_callback = callback

    def set_waypoint_edit_callback(self, callback):
        """Register an optional safety callback for waypoint dragging.

        callback(index) -> bool
        """
        self._waypoint_edit_callback = callback

    def set_waypoint_select_callback(self, callback):
        """
        Register callback for waypoint selection.
        """

        self._waypoint_select_callback = callback

    # =========================================================
    # MAP CLICK
    # =========================================================

    def _on_map_click(self, coordinates):
        """
        Handle click on map.

        TkinterMapView normally provides:

            (latitude, longitude)
        """

        # A map click caused by releasing a waypoint drag must never
        # create an accidental extra waypoint.
        if self._dragging_waypoint:
            return

        if not self.mission_edit_enabled:
            return

        if coordinates is None:

            return

        try:

            lat = float(coordinates[0])
            lon = float(coordinates[1])

        except (
            TypeError,
            ValueError,
            IndexError,
        ):

            print(
                "[MapWidget] "
                f"Invalid map coordinates: {coordinates}"
            )

            return

        print(
            "[MapWidget] "
            f"Map clicked: "
            f"LAT={lat:.7f}, "
            f"LON={lon:.7f}"
        )

        # First click after SETUP is enabled places HOME.
        # Every click after that adds WP1, WP2, ...
        if self.home_point is None:
            self.set_home_point(lat, lon)
            return

        self.add_waypoint(
            lat,
            lon,
        )

    # =========================================================
    # HOME POINT
    # =========================================================

    def set_home_point(self, lat, lon):
        """
        Place (or move) the mission HOME point.

        HOME is the mission's starting position. It is drawn first
        on the route, before WP1, WP2, ...
        """

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            print("[MapWidget] Invalid HOME data.")
            return None

        self.home_point = {"lat": lat, "lon": lon}

        self.add_marker(
            lat,
            lon,
            "HOME",
            draggable=True,
        )

        self._redraw_waypoint_route()

        if self._home_callback is not None:
            try:
                self._home_callback(dict(self.home_point))
            except Exception as error:
                print(f"[MapWidget] Home callback error: {error}")

        print(f"[MapWidget] HOME set: {lat:.7f}, {lon:.7f}")

        return dict(self.home_point)

    def get_home_point(self):
        """Return a copy of the HOME point, or None if not set yet."""
        return dict(self.home_point) if self.home_point is not None else None

    def has_home_point(self):
        return self.home_point is not None

    # =========================================================
    # ADD WAYPOINT
    # =========================================================

    def add_waypoint(
        self,
        lat,
        lon,
        altitude=50.0,
        speed=10.0,
    ):
        """
        Add a waypoint.

        Returns:
            waypoint dictionary
        """

        try:

            lat = float(lat)
            lon = float(lon)
            altitude = float(altitude)
            speed = float(speed)

        except (
            TypeError,
            ValueError,
        ):

            print(
                "[MapWidget] "
                "Invalid waypoint data."
            )

            return None

        # =====================================================
        # INDEX
        # =====================================================

        index = len(
            self.waypoints
        ) + 1

        # =====================================================
        # WAYPOINT OBJECT
        # =====================================================

        waypoint = {
            "index": index,
            "lat": lat,
            "lon": lon,
            "alt": altitude,
            "speed": speed,
        }

        self.waypoints.append(
            waypoint
        )

        # =====================================================
        # MARKER
        # =====================================================

        marker_id = (
            f"WP{index}"
        )

        self.add_marker(
            lat,
            lon,
            marker_id,
            draggable=True,
        )

        # =====================================================
        # ROUTE
        # =====================================================

        self._redraw_waypoint_route()

        # =====================================================
        # CALLBACK
        # =====================================================

        if self._waypoint_callback is not None:

            try:

                self._waypoint_callback(
                    waypoint
                )

            except Exception as error:

                print(
                    "[MapWidget] "
                    f"Waypoint callback error: {error}"
                )

        print(
            "[MapWidget] "
            f"Added WP{index}: "
            f"{lat:.7f}, "
            f"{lon:.7f}"
        )

        return waypoint

    # =========================================================
    # REDRAW WAYPOINT ROUTE
    # =========================================================

    def _redraw_waypoint_route(self):
        """
        Redraw route starting from HOME (if set), then all
        current waypoints in order.
        """

        points = []

        if self.home_point is not None:
            points.append(
                (
                    self.home_point["lat"],
                    self.home_point["lon"],
                )
            )

        points += [
            (
                waypoint["lat"],
                waypoint["lon"],
            )
            for waypoint in self.waypoints
        ]

        self.draw_route(
            points,
            route_id="MISSION",
        )

    # =========================================================
    # REMOVE WAYPOINT
    # =========================================================

    def remove_waypoint(
        self,
        index,
    ):
        """
        Remove waypoint by index.

        Example:

            remove_waypoint(2)

        removes WP2.
        """

        try:

            index = int(index)

        except (
            TypeError,
            ValueError,
        ):

            return False

        if index < 1:

            return False

        position = index - 1

        if position >= len(
            self.waypoints
        ):

            return False

        # =====================================================
        # REMOVE DATA
        # =====================================================

        self.waypoints.pop(
            position
        )

        # =====================================================
        # REMOVE OLD MARKERS
        # =====================================================

        for marker_id in list(
            self._markers.keys()
        ):

            if str(
                marker_id
            ).startswith("WP"):

                self.remove_marker(
                    marker_id
                )

        # =====================================================
        # REINDEX
        # =====================================================

        for new_index, waypoint in enumerate(
            self.waypoints,
            start=1,
        ):

            waypoint["index"] = new_index

            self.add_marker(
                waypoint["lat"],
                waypoint["lon"],
                f"WP{new_index}",
                draggable=True,
            )

        # =====================================================
        # REDRAW ROUTE
        # =====================================================

        self._redraw_waypoint_route()

        print(
            "[MapWidget] "
            f"Removed waypoint {index}"
        )

        return True

    # =========================================================
    # MOVE WAYPOINT
    # =========================================================

    def move_waypoint(self, index, lat, lon):
        """Move an existing waypoint and redraw its mission route."""
        try:
            index = int(index)
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return False

        position = index - 1
        if position < 0 or position >= len(self.waypoints):
            return False

        waypoint = self.waypoints[position]
        waypoint["lat"] = lat
        waypoint["lon"] = lon

        self.update_marker(f"WP{index}", lat, lon)
        self._redraw_waypoint_route()

        if self._waypoint_update_callback is not None:
            try:
                self._waypoint_update_callback(dict(waypoint))
            except Exception as error:
                print(f"[MapWidget] Waypoint update callback error: {error}")

        return True

    def _can_drag_waypoint(self, index):
        if not self.mission_edit_enabled:
            return False
        if self._waypoint_edit_callback is None:
            return True
        try:
            return bool(self._waypoint_edit_callback(index))
        except Exception as error:
            print(f"[MapWidget] Waypoint edit callback error: {error}")
            return False

    def _on_waypoint_marker_click(self, marker):
        """Start dragging a waypoint or the HOME marker when mission editing is allowed."""
        text = str(marker.text)

        if text == "HOME":
            drag_key = "HOME"
        else:
            try:
                drag_key = int(text.replace("WP", ""))
            except (TypeError, ValueError):
                return

        if not self._can_drag_waypoint(drag_key):
            return

        self._dragging_waypoint = True
        self._drag_waypoint_index = drag_key
        self._drag_marker = marker
        try:
            self.canvas.configure(cursor="fleur")
        except Exception:
            pass

    def _intercept_drag_motion(self, event):
        """Run BEFORE TkinterMapView's own pan handler (see the
        WaypointDragIntercept bindtag set up in __init__). Returning
        "break" here stops the map from also panning while a
        waypoint/HOME marker is being dragged.
        """
        if self._dragging_waypoint:
            self._on_waypoint_drag_motion(event)
            return "break"
        return None

    def _intercept_drag_release(self, event):
        """See _intercept_drag_motion."""
        if self._dragging_waypoint:
            self._on_waypoint_drag_release(event)
            return "break"
        return None

    def _on_waypoint_drag_motion(self, event):
        if not self._dragging_waypoint or self._drag_waypoint_index is None:
            return

        try:
            lat, lon = self.convert_canvas_coords_to_decimal_coords(event.x, event.y)

            if self._drag_waypoint_index == "HOME":
                if self.home_point is None:
                    return "break"
                self.home_point["lat"] = float(lat)
                self.home_point["lon"] = float(lon)
                marker = self._markers.get("HOME")
                if marker is not None:
                    marker.set_position((lat, lon))
                self._redraw_waypoint_route()
                return "break"

            position = self._drag_waypoint_index - 1
            if not (0 <= position < len(self.waypoints)):
                return

            self.waypoints[position]["lat"] = float(lat)
            self.waypoints[position]["lon"] = float(lon)

            marker = self._markers.get(f"WP{self._drag_waypoint_index}")
            if marker is not None:
                marker.set_position((lat, lon))

            self._redraw_waypoint_route()
            return "break"
        except Exception as error:
            print(f"[MapWidget] Waypoint drag error: {error}")
            return "break"

    def _on_waypoint_drag_release(self, event):
        if not self._dragging_waypoint or self._drag_waypoint_index is None:
            return

        index = self._drag_waypoint_index
        try:
            lat, lon = self.convert_canvas_coords_to_decimal_coords(event.x, event.y)
            if index == "HOME":
                self.set_home_point(lat, lon)
            else:
                self.move_waypoint(index, lat, lon)
        except Exception as error:
            print(f"[MapWidget] Waypoint release error: {error}")

        self._dragging_waypoint = False
        self._drag_waypoint_index = None
        self._drag_marker = None
        try:
            self.canvas.configure(cursor="")
        except Exception:
            pass

        return "break"

    # =========================================================
    # CLEAR WAYPOINTS
    # =========================================================

    def clear_waypoints(self):
        """
        Remove all mission waypoints, and HOME.

        A fresh SETUP session after this will ask for HOME again
        before WP1, WP2, ...
        """

        # =====================================================
        # REMOVE WAYPOINT MARKERS
        # =====================================================

        for marker_id in list(
            self._markers.keys()
        ):

            if str(
                marker_id
            ).startswith("WP"):

                self.remove_marker(
                    marker_id
                )

        # =====================================================
        # REMOVE HOME MARKER
        # =====================================================

        if self.home_point is not None:
            self.remove_marker("HOME")
            self.home_point = None
            if self._home_callback is not None:
                try:
                    self._home_callback(None)
                except Exception as error:
                    print(f"[MapWidget] Home callback error: {error}")

        # =====================================================
        # CLEAR DATA
        # =====================================================

        self.waypoints.clear()

        # =====================================================
        # CLEAR ROUTE
        # =====================================================

        self.clear_route(
            "MISSION"
        )

        print(
            "[MapWidget] "
            "All waypoints cleared."
        )

    # =========================================================
    # GET WAYPOINTS
    # =========================================================

    def get_waypoints(self):
        """
        Return a copy of current waypoints.
        """

        return [
            dict(waypoint)
            for waypoint in self.waypoints
        ]

    # =========================================================
    # SET WAYPOINTS
    # =========================================================

    def set_waypoints(
        self,
        waypoints,
    ):
        """
        Replace all current waypoints.

        Useful when loading a saved mission.
        """

        self.clear_waypoints()

        if waypoints is None:

            return

        for waypoint in waypoints:

            if not isinstance(
                waypoint,
                dict,
            ):

                continue

            self.add_waypoint(
                waypoint.get(
                    "lat",
                    0.0,
                ),
                waypoint.get(
                    "lon",
                    0.0,
                ),
                waypoint.get(
                    "alt",
                    50.0,
                ),
                waypoint.get(
                    "speed",
                    10.0,
                ),
            )

    # =========================================================
    # MOUSE
    # =========================================================

    def _on_enter(self, event):
        """
        Give the map keyboard focus when mouse enters.
        """

        try:

            self.focus_set()

        except tk.TclError:

            pass

    def _on_mousewheel(self, event):
        """
        Mouse wheel zoom.

        Normal:
            Wheel UP   -> +1
            Wheel DOWN -> -1

        Ctrl + Wheel:
            Faster zoom.

        Returning "break" prevents another
        zoom handler from processing the event.
        """

        # =====================================================
        # DETECT WHEEL DIRECTION
        # =====================================================

        event_num = getattr(
            event,
            "num",
            None,
        )

        event_delta = getattr(
            event,
            "delta",
            0,
        )

        # -----------------------------------------------------
        # Linux
        # -----------------------------------------------------

        if event_num == 4:

            direction = 1
            wheel_amount = 1

        elif event_num == 5:

            direction = -1
            wheel_amount = 1

        # -----------------------------------------------------
        # Windows / macOS
        # -----------------------------------------------------

        elif event_delta > 0:

            direction = 1

            wheel_amount = max(
                1,
                int(
                    abs(event_delta) / 120
                ),
            )

        elif event_delta < 0:

            direction = -1

            wheel_amount = max(
                1,
                int(
                    abs(event_delta) / 120
                ),
            )

        else:

            return "break"

        # =====================================================
        # CHECK CTRL
        # =====================================================

        ctrl_pressed = bool(
            getattr(
                event,
                "state",
                0,
            )
            & 0x0004
        )

        # =====================================================
        # NORMAL WHEEL
        # =====================================================

        if not ctrl_pressed:

            self._last_wheel_time = 0.0

            zoom_step = wheel_amount

            new_zoom = (
                self.zoom
                + direction * zoom_step
            )

            self.set_zoom(
                new_zoom
            )

            return "break"

        # =====================================================
        # CTRL + WHEEL
        # =====================================================

        current_time = time.monotonic()

        if self._last_wheel_time == 0.0:

            delta_time = 999.0

        else:

            delta_time = (
                current_time
                - self._last_wheel_time
            )

        self._last_wheel_time = (
            current_time
        )

        # =====================================================
        # DETERMINE SCROLL SPEED
        # =====================================================

        if delta_time < 0.035:

            zoom_step = 3

        elif delta_time < 0.080:

            zoom_step = 2

        else:

            zoom_step = 2

        zoom_step *= wheel_amount

        # =====================================================
        # APPLY ZOOM
        # =====================================================

        new_zoom = (
            self.zoom
            + direction * zoom_step
        )

        self.set_zoom(
            new_zoom
        )

        return "break"

    # =========================================================
    # PROVIDER
    # =========================================================

    def set_tile_provider(
        self,
        url,
        attribution="",
        max_zoom=19,
    ):
        """
        Set exactly ONE tile provider.

        Calling this replaces the current tile source.
        """

        self.set_tile_server(
            url,
            max_zoom=max_zoom,
        )

        self._attribution = (
            attribution or ""
        )

    def get_attribution(self):

        return self._attribution

    # =========================================================
    # VIEW
    # =========================================================

    def set_center(
        self,
        lat,
        lon,
    ):
        """
        Set map center.
        """

        self.set_position(
            float(lat),
            float(lon),
        )

    def set_zoom(
        self,
        zoom,
        relative_pointer_x=None,
        relative_pointer_y=None,
        **kwargs,
    ):
        """
        Set zoom level with safety limits.
        """

        try:

            zoom = int(zoom)

        except (
            TypeError,
            ValueError,
        ):

            zoom = self.HOME_ZOOM

        zoom = max(
            self.MIN_ZOOM,
            min(
                self.MAX_ZOOM,
                zoom,
            ),
        )

        # =====================================================
        # NORMAL ZOOM
        # =====================================================

        if (
            relative_pointer_x is None
            or relative_pointer_y is None
        ):

            return super().set_zoom(
                zoom,
                **kwargs,
            )

        # =====================================================
        # MOUSE-POSITION ZOOM
        # =====================================================

        return super().set_zoom(
            zoom,
            relative_pointer_x=relative_pointer_x,
            relative_pointer_y=relative_pointer_y,
            **kwargs,
        )

    def zoom_in(self):

        self.set_zoom(
            self.zoom + 1
        )

    def zoom_out(self):

        self.set_zoom(
            self.zoom - 1
        )

    def go_home(self):
        """
        Return to initial RIGEL map position.
        """

        self.set_position(
            self.HOME_LAT,
            self.HOME_LON,
        )

        self.set_zoom(
            self.HOME_ZOOM
        )

    def center_uav(
        self,
        lat,
        lon,
        zoom=None,
    ):
        """
        Center map on UAV position.
        """

        self.set_position(
            float(lat),
            float(lon),
        )

        if zoom is not None:

            self.set_zoom(
                zoom
            )

    # =========================================================
    # KEYBOARD HELPERS
    # =========================================================

    def _zoom_and_break(
        self,
        direction,
    ):

        if direction > 0:

            self.zoom_in()

        else:

            self.zoom_out()

        return "break"

    def _go_home_and_break(self):

        self.go_home()

        return "break"

    # =========================================================
    # MARKER
    # =========================================================

    def add_marker(
        self,
        lat,
        lon,
        marker_id,
        draggable=False,
    ):
        """
        Add a marker to the map.

        Existing marker with the same ID
        will be removed first.
        """

        self.remove_marker(
            marker_id
        )

        marker = self.set_marker(
            float(lat),
            float(lon),
            text=str(marker_id),
            command=self._on_waypoint_marker_click if draggable else None,
        )

        marker.draggable = bool(draggable)

        self._markers[
            marker_id
        ] = marker

        return marker

    def update_marker(
        self,
        marker_id,
        lat,
        lon,
    ):
        """
        Update an existing marker.

        If marker does not exist,
        it will be created.
        """

        marker = self._markers.get(
            marker_id
        )

        if marker is None:

            return self.add_marker(
                lat,
                lon,
                marker_id,
            )

        marker.set_position(
            float(lat),
            float(lon),
        )

        return marker

    def remove_marker(
        self,
        marker_id,
    ):
        """
        Remove marker from map.
        """

        marker = self._markers.pop(
            marker_id,
            None,
        )

        if marker is not None:

            try:

                marker.delete()

            except Exception:

                pass

    # =========================================================
    # ROUTE
    # =========================================================

    def draw_route(
        self,
        points,
        route_id="MISSION",
    ):
        """
        Draw route from:

            [
                (latitude, longitude),
                ...
            ]
        """

        self.clear_route(
            route_id
        )

        if points is None:
            return None

        if len(points) < 2:
            return None

        path = self.set_path(
            [
                (
                    float(lat),
                    float(lon),
                )
                for lat, lon in points
            ]
        )

        self._routes[
            route_id
        ] = path

        return path

    def clear_route(
        self,
        route_id="MISSION",
    ):
        """
        Remove route from map.
        """

        path = self._routes.pop(
            route_id,
            None,
        )

        if path is not None:

            try:

                path.delete()

            except Exception:

                pass

    # =========================================================
    # CLEAR MAP OBJECTS
    # =========================================================

    def clear_map_objects(self):
        """
        Remove all markers and routes.
        """

        # -----------------------------------------------------
        # Remove markers
        # -----------------------------------------------------

        for marker_id in list(
            self._markers
        ):

            self.remove_marker(
                marker_id
            )

        # -----------------------------------------------------
        # Remove routes
        # -----------------------------------------------------

        for route_id in list(
            self._routes
        ):

            self.clear_route(
                route_id
            )

        # -----------------------------------------------------
        # Clear waypoint data
        # -----------------------------------------------------

        self.waypoints.clear()