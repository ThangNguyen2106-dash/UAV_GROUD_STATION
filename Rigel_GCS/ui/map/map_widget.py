from __future__ import annotations

import json
from typing import Any, List, Optional

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MapBridge(QObject):
    """Bridge for communication between Python and Leaflet JavaScript."""

    map_clicked = Signal(float, float)  # lat, lon

    @Slot(float, float)
    def onMapClick(self, lat: float, lon: float) -> None:  # noqa: N802
        self.map_clicked.emit(lat, lon)


MAP_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RIGEL Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        html, body, #map {
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            background: #0b0f14;
        }
        .uav-icon {
            transition: transform 0.15s ease-out;
            transform-origin: center center;
        }
        .waypoint-label {
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid #38bdf8;
            color: #f8fafc;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: bold;
            text-align: center;
        }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {
            zoomControl: false,
            attributionControl: false
        }).setView([21.028511, 105.804817], 16);

        L.control.zoom({ position: 'topright' }).addTo(map);

        // Tile Layers
        var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19
        }).addTo(map);

        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19
        });

        var baseMaps = {
            "Bản đồ số (OSM)": osmLayer,
            "Ảnh vệ tinh (Satellite)": satelliteLayer
        };
        L.control.layers(baseMaps, null, { position: 'topright' }).addTo(map);

        // UAV Icon (SVG triangle/drone pointer)
        var uavSvg = '<svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">' +
                     '<polygon points="18,2 32,32 18,24 4,32" fill="#38bdf8" stroke="#ffffff" stroke-width="2"/>' +
                     '<circle cx="18" cy="18" r="3" fill="#facc15"/>' +
                     '</svg>';

        var uavIcon = L.divIcon({
            html: '<div id="uav-marker-icon" class="uav-icon">' + uavSvg + '</div>',
            className: 'custom-uav-icon',
            iconSize: [36, 36],
            iconAnchor: [18, 18]
        });

        var uavMarker = L.marker([21.028511, 105.804817], { icon: uavIcon, zIndexOffset: 1000 }).addTo(map);
        var homeMarker = null;

        // Flight Trail
        var flightTrail = L.polyline([], {
            color: '#f59e0b',
            weight: 3,
            opacity: 0.85,
            smoothFactor: 1
        }).addTo(map);

        // Mission Waypoints Layer
        var missionLine = L.polyline([], {
            color: '#06b6d4',
            weight: 2.5,
            dashArray: '6, 6',
            opacity: 0.9
        }).addTo(map);
        var waypointMarkers = [];

        var followDrone = true;
        var pyBridge = null;

        // WebChannel Setup
        new QWebChannel(qt.webChannelTransport, function(channel) {
            pyBridge = channel.objects.pyBridge;
        });

        map.on('click', function(e) {
            if (pyBridge) {
                pyBridge.onMapClick(e.latlng.lat, e.latlng.lng);
            }
        });

        // API Methods called from Python
        window.updateUavPosition = function(lat, lon, heading, alt) {
            var latlng = [lat, lon];
            uavMarker.setLatLng(latlng);
            
            var el = document.getElementById('uav-marker-icon');
            if (el) {
                el.style.transform = 'rotate(' + (heading || 0) + 'deg)';
            }

            flightTrail.addLatLng(latlng);

            if (followDrone) {
                map.panTo(latlng, { animate: true, duration: 0.2 });
            }
        };

        window.setHomePosition = function(lat, lon) {
            if (!homeMarker) {
                var homeIcon = L.divIcon({
                    html: '<div style="background:#ef4444;color:white;border-radius:50%;width:24px;height:24px;text-align:center;line-height:24px;font-weight:bold;border:2px solid white;">H</div>',
                    className: 'home-icon',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                });
                homeMarker = L.marker([lat, lon], { icon: homeIcon, zIndexOffset: 900 }).addTo(map);
            } else {
                homeMarker.setLatLng([lat, lon]);
            }
        };

        window.clearFlightTrail = function() {
            flightTrail.setLatLngs([]);
        };

        window.setFollowDrone = function(enable) {
            followDrone = enable;
            if (followDrone && uavMarker) {
                map.panTo(uavMarker.getLatLng());
            }
        };

        window.centerOnUav = function() {
            if (uavMarker) {
                map.setView(uavMarker.getLatLng(), map.getZoom());
            }
        };

        window.updateMissionWaypoints = function(waypoints) {
            // waypoints is an array of {lat: float, lon: float, alt: float, index: int}
            waypointMarkers.forEach(function(m) { map.removeLayer(m); });
            waypointMarkers = [];

            var latlngs = [];
            waypoints.forEach(function(wp, i) {
                var pos = [wp.lat, wp.lon];
                latlngs.push(pos);

                var marker = L.marker(pos, {
                    icon: L.divIcon({
                        className: 'waypoint-label',
                        html: 'WP ' + (i + 1) + ' (' + wp.alt + 'm)',
                        iconSize: [60, 20],
                        iconAnchor: [30, 10]
                    })
                }).addTo(map);

                waypointMarkers.push(marker);
            });

            missionLine.setLatLngs(latlngs);
        };
    </script>
</body>
</html>
"""


class MapWidget(QFrame):
    """Interactive Realtime Map View with Live UAV tracking and Waypoint visualizer."""

    waypoint_clicked = Signal(float, float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("MapWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._follow_drone = True
        self._last_lat: Optional[float] = None
        self._last_lon: Optional[float] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Map Control Bar
        toolbar = QFrame()
        toolbar.setStyleSheet("background:#11161c; border-bottom:1px solid #232d38; padding:4px;")
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(8, 4, 8, 4)
        t_layout.setSpacing(8)

        self.coords_label = QLabel("GPS: LAT --   LON --")
        self.coords_label.setStyleSheet("color:#38bdf8; font-weight:bold; font-size:11px;")
        t_layout.addWidget(self.coords_label)
        t_layout.addStretch(1)

        self.btn_center = QPushButton("🎯 Center UAV")
        self.btn_center.setFixedHeight(24)
        self.btn_center.clicked.connect(self.center_on_uav)
        t_layout.addWidget(self.btn_center)

        self.btn_follow = QPushButton("📍 Follow: ON")
        self.btn_follow.setFixedHeight(24)
        self.btn_follow.clicked.connect(self._toggle_follow)
        t_layout.addWidget(self.btn_follow)

        self.btn_clear_trail = QPushButton("🧹 Clear Trail")
        self.btn_clear_trail.setFixedHeight(24)
        self.btn_clear_trail.clicked.connect(self.clear_flight_trail)
        t_layout.addWidget(self.btn_clear_trail)

        layout.addWidget(toolbar)

        # WebEngine View
        self.web_view = QWebEngineView()
        self.channel = QWebChannel(self)
        self.bridge = MapBridge(self)
        self.bridge.map_clicked.connect(self.waypoint_clicked.emit)
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        self.web_view.setHtml(MAP_HTML_TEMPLATE)
        layout.addWidget(self.web_view, 1)

    def update_uav_telemetry(self, state: Any) -> None:
        """Update UAV live marker and path on the map."""
        lat = getattr(state, "latitude", None)
        lon = getattr(state, "longitude", None)
        heading = getattr(state, "heading", None) or getattr(state, "vfr_heading", 0.0) or 0.0
        alt = getattr(state, "altitude", None) or getattr(state, "relative_altitude", 0.0) or 0.0

        if lat is None or lon is None or (lat == 0.0 and lon == 0.0):
            return

        try:
            lat_f = float(lat)
            lon_f = float(lon)
            head_f = float(heading)
            alt_f = float(alt)

            # Check if coordinates moved significantly (> 1e-6)
            if self._last_lat is None or abs(lat_f - self._last_lat) > 1e-7 or abs(lon_f - self._last_lon) > 1e-7:
                self._last_lat = lat_f
                self._last_lon = lon_f
                self.coords_label.setText(f"GPS: {lat_f:.6f}, {lon_f:.6f} | Alt: {alt_f:.1f}m")

            js = f"window.updateUavPosition({lat_f}, {lon_f}, {head_f}, {alt_f});"
            self.web_view.page().runJavaScript(js)
        except (TypeError, ValueError):
            pass

    def set_home_position(self, lat: float, lon: float) -> None:
        """Set home location on map."""
        js = f"window.setHomePosition({float(lat)}, {float(lon)});"
        self.web_view.page().runJavaScript(js)

    def update_waypoints_display(self, waypoints: List[dict]) -> None:
        """Render waypoints and mission path on map."""
        data_json = json.dumps(waypoints)
        js = f"window.updateMissionWaypoints({data_json});"
        self.web_view.page().runJavaScript(js)

    def clear_flight_trail(self) -> None:
        """Clear flight path history on map."""
        self.web_view.page().runJavaScript("window.clearFlightTrail();")

    def center_on_uav(self) -> None:
        """Pan map to UAV current location."""
        self.web_view.page().runJavaScript("window.centerOnUav();")

    def _toggle_follow(self) -> None:
        self._follow_drone = not self._follow_drone
        self.btn_follow.setText("📍 Follow: ON" if self._follow_drone else "📍 Follow: OFF")
        js = f"window.setFollowDrone({'true' if self._follow_drone else 'false'});"
        self.web_view.page().runJavaScript(js)
