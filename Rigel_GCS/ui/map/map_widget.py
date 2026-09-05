import json
import math
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

from Rigel_GCS.core.geo_fence import (
    NATIONAL_BORDERS,
    NO_FLY_ZONES,
    check_airspace,
)


class MapBridge(QObject):
    """Bridge for communication between Python and Leaflet JavaScript."""

    map_clicked = Signal(float, float)  # lat, lon
    nfz_violation_alert = Signal(str)  # warning message

    @Slot(float, float)
    def onMapClick(self, lat: float, lon: float) -> None:  # noqa: N802
        self.map_clicked.emit(lat, lon)

    @Slot(str)
    def onNfzAlert(self, message: str) -> None:  # noqa: N802
        self.nfz_violation_alert.emit(message)


# Build JSON datasets for Leaflet JS
_NFZ_JSON = json.dumps([
    {
        "id": z.id,
        "name": z.name,
        "code": z.code,
        "lat": z.lat,
        "lon": z.lon,
        "prohibited_radius_m": z.prohibited_radius_m,
        "restricted_radius_m": z.restricted_radius_m,
        "category": z.category,
        "description": z.description,
    }
    for z in NO_FLY_ZONES
])

_BORDERS_JSON = json.dumps(NATIONAL_BORDERS)


MAP_HTML_TEMPLATE = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RIGEL Satellite Tactical Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        html, body, #map {{
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            background: #070a0e;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        }}
        .custom-uav-icon {{
            display: flex;
            align-items: center;
            justify-content: center;
            background: transparent !important;
            border: none !important;
        }}
        .uav-icon {{
            transition: transform 0.1s ease-out;
            transform-origin: 50% 50%;
            display: inline-block;
            filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.8));
        }}
        .waypoint-label {{
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid #38bdf8;
            color: #38bdf8;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.6);
        }}
        .nfz-popup {{
            font-size: 12px;
            line-height: 1.4;
            color: #f8fafc;
            background: #0f172a;
            border-radius: 6px;
            padding: 4px;
        }}
        .leaflet-popup-content-wrapper {{
            background: #0f172a !important;
            color: #f8fafc !important;
            border: 1px solid #dc2626 !important;
            box-shadow: 0 4px 16px rgba(220, 38, 38, 0.4) !important;
            border-radius: 8px !important;
        }}
        .leaflet-popup-tip {{
            background: #0f172a !important;
        }}
        .border-tooltip {{
            background: rgba(15, 23, 42, 0.95) !important;
            border: 1px solid #eab308 !important;
            color: #fef08a !important;
            font-size: 11px !important;
            font-weight: bold !important;
            border-radius: 4px !important;
            padding: 3px 6px !important;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var NFZ_DATA = {_NFZ_JSON};
        var BORDER_DATA = {_BORDERS_JSON};

        var map = L.map('map', {{
            zoomControl: false,
            attributionControl: false
        }}).setView([21.028511, 105.804817], 15);

        L.control.zoom({{ position: 'topright' }}).addTo(map);

        // 1. High-Resolution Satellite Basemap (ArcGIS World Imagery)
        var satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 19,
            attribution: 'Esri World Imagery'
        }}).addTo(map);

        // 2. High-Contrast Road & Reference Overlay
        var referenceOverlay = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
            maxZoom: 19,
            opacity: 0.85
        }}).addTo(map);

        // 3. No-Fly Zones Layer Group
        var nfzLayerGroup = L.layerGroup().addTo(map);
        var nfzCircles = [];

        function initNoFlyZones() {{
            NFZ_DATA.forEach(function(zone) {{
                // Outer Restricted Zone (Yellow)
                var restrictedCircle = L.circle([zone.lat, zone.lon], {{
                    radius: zone.restricted_radius_m,
                    color: '#f59e0b',
                    weight: 1.5,
                    dashArray: '5, 5',
                    fillColor: '#f59e0b',
                    fillOpacity: 0.08
                }}).addTo(nfzLayerGroup);

                var descHtml = '<div class="nfz-popup">' +
                    '<b style="color:#ef4444; font-size:13px;">⛔ ' + zone.name + '</b><br/>' +
                    '<span style="color:#94a3b8; font-size:11px;">Mã ICAO: ' + zone.code + ' | Loại: ' + zone.category + '</span><hr style="border:0; border-top:1px solid #334155; margin:4px 0;"/>' +
                    '<span style="color:#f87171;">🚫 Vùng cấm bay tuyệt đối: ' + (zone.prohibited_radius_m / 1000) + ' km</span><br/>' +
                    '<span style="color:#fbbf24;">⚠️ Vùng kiểm soát tiếp cận: ' + (zone.restricted_radius_m / 1000) + ' km</span><br/>' +
                    '<p style="margin:4px 0 0 0; color:#cbd5e1; font-size:11px;">' + zone.description + '</p>' +
                    '</div>';

                restrictedCircle.bindPopup(descHtml);

                // Inner Prohibited Zone (Red)
                var prohibitedCircle = L.circle([zone.lat, zone.lon], {{
                    radius: zone.prohibited_radius_m,
                    color: '#ef4444',
                    weight: 2.5,
                    dashArray: '6, 4',
                    fillColor: '#ef4444',
                    fillOpacity: 0.25
                }}).addTo(nfzLayerGroup);

                prohibitedCircle.bindPopup(descHtml);

                // Center Icon Marker
                var centerMarker = L.marker([zone.lat, zone.lon], {{
                    icon: L.divIcon({{
                        html: '<div style="background:#dc2626; color:white; border-radius:50%; width:20px; height:20px; text-align:center; line-height:20px; font-size:10px; font-weight:bold; border:1.5px solid white; box-shadow:0 0 8px rgba(220,38,38,0.8);">⛔</div>',
                        className: 'nfz-center-icon',
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    }})
                }}).addTo(nfzLayerGroup);

                centerMarker.bindPopup(descHtml);
                nfzCircles.push({{ zone: zone, prohibited: prohibitedCircle, restricted: restrictedCircle }});
            }});
        }}
        initNoFlyZones();

        // 4. National Borders Layer Group
        var borderLayerGroup = L.layerGroup().addTo(map);

        function initNationalBorders() {{
            BORDER_DATA.forEach(function(border) {{
                var borderLine = L.polyline(border.coordinates, {{
                    color: '#eab308',
                    weight: 3.5,
                    dashArray: '8, 8',
                    opacity: 0.9,
                    smoothFactor: 1
                }}).addTo(borderLayerGroup);

                borderLine.bindTooltip(border.name, {{
                    className: 'border-tooltip',
                    sticky: true
                }});
            }});
        }}
        initNationalBorders();

        // UAV Icon
        var uavSvg = '<svg width="38" height="38" viewBox="0 0 38 38" fill="none" xmlns="http://www.w3.org/2000/svg" style="overflow:visible;">' +
                     '<polygon points="19,2 34,34 19,26 4,34" fill="#38bdf8" stroke="#ffffff" stroke-width="2.5"/>' +
                     '<circle cx="19" cy="19" r="4" fill="#facc15"/>' +
                     '</svg>';

        var uavIcon = L.divIcon({{
            html: '<div id="uav-marker-icon" class="uav-icon">' + uavSvg + '</div>',
            className: 'custom-uav-icon',
            iconSize: [38, 38],
            iconAnchor: [19, 19]
        }});

        var uavMarker = L.marker([21.028511, 105.804817], {{ icon: uavIcon, zIndexOffset: 1000 }}).addTo(map);
        var homeMarker = null;

        // Flight Trail
        var flightTrail = L.polyline([], {{
            color: '#06b6d4',
            weight: 3,
            opacity: 0.9,
            smoothFactor: 1
        }}).addTo(map);

        // Mission Waypoints Layer
        var missionLine = L.polyline([], {{
            color: '#f59e0b',
            weight: 2.5,
            dashArray: '6, 6',
            opacity: 0.9
        }}).addTo(map);
        var waypointMarkers = [];

        var followDrone = true;
        var pyBridge = null;

        // Distance calculation helper (Haversine in meters)
        function calcDistance(lat1, lon1, lat2, lon2) {{
            var R = 6371000;
            var dLat = (lat2 - lat1) * Math.PI / 180;
            var dLon = (lon2 - lon1) * Math.PI / 180;
            var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                    Math.sin(dLon/2) * Math.sin(dLon/2);
            var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }}

        // WebChannel Setup
        new QWebChannel(qt.webChannelTransport, function(channel) {{
            pyBridge = channel.objects.pyBridge;
        }});

        map.on('click', function(e) {{
            // Check if user clicked inside any Prohibited No-Fly Zone
            var clickedLat = e.latlng.lat;
            var clickedLon = e.latlng.lng;
            var violationMsg = null;

            for (var i = 0; i < NFZ_DATA.length; i++) {{
                var z = NFZ_DATA[i];
                var d = calcDistance(clickedLat, clickedLon, z.lat, z.lon);
                if (d <= z.prohibited_radius_m) {{
                    violationMsg = '⛔ KHÔNG THỂ ĐẶT WAYPOINT: Tọa độ nằm trong VÙNG CẤM BAY của ' + z.name + ' (' + Math.round(d) + 'm)!';
                    break;
                }}
            }}

            if (violationMsg && pyBridge) {{
                pyBridge.onNfzAlert(violationMsg);
            }}

            if (pyBridge) {{
                pyBridge.onMapClick(clickedLat, clickedLon);
            }}
        }});

        // Python Invocation API Methods
        window.updateUavPosition = function(lat, lon, heading, alt) {{
            var latlng = [lat, lon];
            uavMarker.setLatLng(latlng);
            
            var el = document.getElementById('uav-marker-icon');
            if (el) {{
                el.style.transform = 'rotate(' + (heading || 0) + 'deg)';
            }}

            flightTrail.addLatLng(latlng);

            if (followDrone) {{
                map.panTo(latlng, {{ animate: true, duration: 0.2 }});
            }}
        }};

        window.updateUavHeading = function(heading) {{
            var el = document.getElementById('uav-marker-icon');
            if (el) {{
                el.style.transform = 'rotate(' + (heading || 0) + 'deg)';
            }}
        }};

        window.setHomePosition = function(lat, lon) {{
            if (!homeMarker) {{
                var homeIcon = L.divIcon({{
                    html: '<div style="background:#ef4444;color:white;border-radius:50%;width:24px;height:24px;text-align:center;line-height:24px;font-weight:bold;border:2px solid white;box-shadow:0 0 8px rgba(239,68,68,0.8);">H</div>',
                    className: 'home-icon',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                }});
                homeMarker = L.marker([lat, lon], {{ icon: homeIcon, zIndexOffset: 900 }}).addTo(map);
            }} else {{
                homeMarker.setLatLng([lat, lon]);
            }}
        }};

        window.clearFlightTrail = function() {{
            flightTrail.setLatLngs([]);
        }};

        window.setFollowDrone = function(enable) {{
            followDrone = enable;
            if (followDrone && uavMarker) {{
                map.panTo(uavMarker.getLatLng());
            }}
        }};

        window.centerOnUav = function() {{
            if (uavMarker) {{
                map.setView(uavMarker.getLatLng(), map.getZoom());
            }}
        }};

        window.toggleNfzLayer = function(visible) {{
            if (visible) {{
                map.addLayer(nfzLayerGroup);
            }} else {{
                map.removeLayer(nfzLayerGroup);
            }}
        }};

        window.toggleBorderLayer = function(visible) {{
            if (visible) {{
                map.addLayer(borderLayerGroup);
            }} else {{
                map.removeLayer(borderLayerGroup);
            }}
        }};

        window.updateMissionWaypoints = function(waypoints) {{
            waypointMarkers.forEach(function(m) {{ map.removeLayer(m); }});
            waypointMarkers = [];

            var latlngs = [];
            waypoints.forEach(function(wp, i) {{
                var pos = [wp.lat, wp.lon];
                latlngs.push(pos);

                var marker = L.marker(pos, {{
                    icon: L.divIcon({{
                        className: 'waypoint-label',
                        html: 'WP ' + (i + 1) + ' (' + wp.alt + 'm)',
                        iconSize: [60, 20],
                        iconAnchor: [30, 10]
                    }})
                }}).addTo(map);

                waypointMarkers.push(marker);
            }});

            missionLine.setLatLngs(latlngs);
        }};
    </script>
</body>
</html>
"""


class MapWidget(QFrame):
    """Tactical Satellite Map with Live UAV tracking, No-Fly Zone (NFZ), and Border Safety."""

    waypoint_clicked = Signal(float, float)
    nfz_alert = Signal(str)
    trail_cleared = Signal()
    nfz_toggled = Signal(bool)
    border_toggled = Signal(bool)
    follow_toggled = Signal(bool)

    def __init__(self, enable_waypoint_click: bool = True, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.enable_waypoint_click = enable_waypoint_click
        self.setObjectName("MapWidget")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self._follow_drone = True
        self._nfz_visible = True
        self._border_visible = True
        self._last_lat: Optional[float] = None
        self._last_lon: Optional[float] = None
        self._is_loaded = False
        self._pending_waypoints: List[dict] = []
        self._pending_home: Optional[tuple[float, float]] = None
        self._last_state: Any = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top Map Control Bar
        toolbar = QFrame()
        toolbar.setStyleSheet("background:#0d1117; border-bottom:1px solid #1f2937; padding:4px;")
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(8, 4, 8, 4)
        t_layout.setSpacing(8)

        self.coords_label = QLabel("🛰️ SATELLITE MAP | GPS: Standby | Hdg: 000.0°")
        self.coords_label.setStyleSheet(
            "color:#38bdf8; font-weight:bold; font-size:11px; font-family:'Consolas', 'Segoe UI Monospace', monospace;"
        )
        self.coords_label.setMinimumWidth(460)
        t_layout.addWidget(self.coords_label)
        t_layout.addStretch(1)

        # Toggle NFZ Button
        self.btn_nfz = QPushButton("🛡️ Vùng cấm: ON")
        self.btn_nfz.setFixedHeight(24)
        self.btn_nfz.setStyleSheet("color:#ef4444; font-weight:bold;")
        self.btn_nfz.clicked.connect(self._toggle_nfz)
        t_layout.addWidget(self.btn_nfz)

        # Toggle Border Button
        self.btn_border = QPushButton("🗺️ Biên giới: ON")
        self.btn_border.setFixedHeight(24)
        self.btn_border.setStyleSheet("color:#facc15; font-weight:bold;")
        self.btn_border.clicked.connect(self._toggle_border)
        t_layout.addWidget(self.btn_border)

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

        self.mode_indicator = QLabel("🖱️ Click map to add WP" if self.enable_waypoint_click else "✈️ Flight Mode")
        self.mode_indicator.setStyleSheet("color:#94a3b8; font-size:10px; padding:0 4px;")
        t_layout.addWidget(self.mode_indicator)

        layout.addWidget(toolbar)

        # WebEngine View
        self.web_view = QWebEngineView()
        self.channel = QWebChannel(self)
        self.bridge = MapBridge(self)
        self.bridge.map_clicked.connect(self._on_bridge_map_clicked)
        self.bridge.nfz_violation_alert.connect(self._on_nfz_violation_alert)
        self.channel.registerObject("pyBridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)
        self.web_view.loadFinished.connect(self._on_load_finished)

        self.web_view.setHtml(MAP_HTML_TEMPLATE)
        layout.addWidget(self.web_view, 1)

    def _on_load_finished(self, ok: bool) -> None:
        self._is_loaded = ok
        if ok:
            if self._pending_home:
                self.set_home_position(*self._pending_home)
            if self._pending_waypoints:
                self.update_waypoints_display(self._pending_waypoints)
            if self._last_state:
                self.update_uav_telemetry(self._last_state)
            self.refresh_view()

    def refresh_view(self) -> None:
        """Trigger Leaflet size invalidation and re-center on UAV when becoming visible."""
        if not self._is_loaded:
            return
        js = """
        if (typeof map !== 'undefined') {
            map.invalidateSize(true);
            if (typeof uavMarker !== 'undefined' && uavMarker) {
                if (typeof followDrone !== 'undefined' && followDrone) {
                    map.panTo(uavMarker.getLatLng());
                }
            }
        }
        """
        self.web_view.page().runJavaScript(js)

    def _on_bridge_map_clicked(self, lat: float, lon: float) -> None:
        if self.enable_waypoint_click:
            self.waypoint_clicked.emit(lat, lon)

    def _on_nfz_violation_alert(self, message: str) -> None:
        self.nfz_alert.emit(message)

    def update_uav_telemetry(self, state: Any) -> None:
        """Update UAV live marker and path on the map."""
        if state is None:
            return

        self._last_state = state

        lat = getattr(state, "latitude", None)
        lon = getattr(state, "longitude", None)

        # Resolve heading: 1. heading (deg) -> 2. vfr_heading (deg) -> 3. yaw (radians -> deg)
        heading = getattr(state, "heading", None)
        if heading is None:
            heading = getattr(state, "vfr_heading", None)
        if heading is None:
            yaw = getattr(state, "yaw", None)
            if yaw is not None:
                try:
                    heading = math.degrees(float(yaw)) % 360.0
                except (TypeError, ValueError):
                    heading = 0.0
            else:
                heading = 0.0

        alt = getattr(state, "altitude", None) or getattr(state, "relative_altitude", 0.0) or 0.0

        try:
            head_f = float(heading) % 360.0

            if lat is not None and lon is not None and (float(lat) != 0.0 or float(lon) != 0.0):
                lat_f = float(lat)
                lon_f = float(lon)
                alt_f = float(alt)

                if self._last_lat is None or abs(lat_f - self._last_lat) > 1e-7 or abs(lon_f - self._last_lon) > 1e-7:
                    self._last_lat = lat_f
                    self._last_lon = lon_f

                    # Airspace check
                    res = check_airspace(lat_f, lon_f)
                    if res.is_inside_prohibited:
                        status_prefix = "⛔ NFZ VIOLATION!"
                    elif res.is_inside_restricted:
                        status_prefix = "⚠️ RESTRICTED AIRSPACE"
                    else:
                        status_prefix = "🛰️ SATELLITE MAP"

                    self.coords_label.setText(
                        f"{status_prefix} | GPS: {lat_f:9.6f}, {lon_f:10.6f} | Alt: {alt_f:5.1f}m | Hdg: {head_f:05.1f}°"
                    )

                if self._is_loaded:
                    js = f"window.updateUavPosition({lat_f}, {lon_f}, {head_f}, {alt_f});"
                    self.web_view.page().runJavaScript(js)
            else:
                # Even before 3D GPS fix, rotate the drone icon on the map
                self.coords_label.setText(f"🛰️ SATELLITE MAP | GPS: Standby | Hdg: {head_f:05.1f}°")
                if self._is_loaded:
                    js = f"window.updateUavHeading({head_f});"
                    self.web_view.page().runJavaScript(js)
        except (TypeError, ValueError):
            pass

    def set_home_position(self, lat: float, lon: float) -> None:
        """Set home location on map."""
        self._pending_home = (float(lat), float(lon))
        if self._is_loaded:
            js = f"window.setHomePosition({float(lat)}, {float(lon)});"
            self.web_view.page().runJavaScript(js)

    def update_waypoints_display(self, waypoints: List[dict]) -> None:
        """Render waypoints and mission path on map."""
        self._pending_waypoints = list(waypoints) if waypoints else []
        if self._is_loaded:
            data_json = json.dumps(self._pending_waypoints)
            js = f"window.updateMissionWaypoints({data_json});"
            self.web_view.page().runJavaScript(js)

    def clear_flight_trail(self, emit_signal: bool = True) -> None:
        """Clear flight path history on map."""
        if self._is_loaded:
            self.web_view.page().runJavaScript("window.clearFlightTrail();")
        if emit_signal:
            self.trail_cleared.emit()

    def center_on_uav(self) -> None:
        """Pan map to UAV current location."""
        if self._is_loaded:
            self.web_view.page().runJavaScript("window.centerOnUav();")

    def set_follow(self, enable: bool, emit_signal: bool = False) -> None:
        self._follow_drone = enable
        self.btn_follow.setText("📍 Follow: ON" if self._follow_drone else "📍 Follow: OFF")
        if self._is_loaded:
            js = f"window.setFollowDrone({'true' if self._follow_drone else 'false'});"
            self.web_view.page().runJavaScript(js)
        if emit_signal:
            self.follow_toggled.emit(self._follow_drone)

    def set_nfz_visible(self, visible: bool, emit_signal: bool = False) -> None:
        self._nfz_visible = visible
        self.btn_nfz.setText("🛡️ Vùng cấm: ON" if self._nfz_visible else "🛡️ Vùng cấm: OFF")
        self.btn_nfz.setStyleSheet("color:#ef4444; font-weight:bold;" if self._nfz_visible else "color:#64748b;")
        if self._is_loaded:
            js = f"window.toggleNfzLayer({'true' if self._nfz_visible else 'false'});"
            self.web_view.page().runJavaScript(js)
        if emit_signal:
            self.nfz_toggled.emit(self._nfz_visible)

    def set_border_visible(self, visible: bool, emit_signal: bool = False) -> None:
        self._border_visible = visible
        self.btn_border.setText("🗺️ Biên giới: ON" if self._border_visible else "🗺️ Biên giới: OFF")
        self.btn_border.setStyleSheet("color:#facc15; font-weight:bold;" if self._border_visible else "color:#64748b;")
        if self._is_loaded:
            js = f"window.toggleBorderLayer({'true' if self._border_visible else 'false'});"
            self.web_view.page().runJavaScript(js)
        if emit_signal:
            self.border_toggled.emit(self._border_visible)

    def _toggle_follow(self) -> None:
        self.set_follow(not self._follow_drone, emit_signal=True)

    def _toggle_nfz(self) -> None:
        self.set_nfz_visible(not self._nfz_visible, emit_signal=True)

    def _toggle_border(self) -> None:
        self.set_border_visible(not self._border_visible, emit_signal=True)

