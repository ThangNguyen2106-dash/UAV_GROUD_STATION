"""
RIGEL Ground Station entry point.

Current scope:
    - Start the existing Tkinter UI.
    - Create and mount the MapWidget.
    - Mount the CameraWidget inside the fixed VideoPanel.
    - Connect MapWidget to MapManager / MapProvider.

Telemetry, MAVLink and mission control are intentionally
not wired here yet.
"""

import tkinter as tk

from Rigel_GCS.UI.Main_Window import MainWindow
from Rigel_GCS.Telemetry.Telemetry_Manager import TelemetryManager

from Rigel_GCS.MAP_INTERFACE.Map_Widget import MapWidget
from Rigel_GCS.MAP_INTERFACE.Map_Manager import MapManager

from Rigel_GCS.Module.Mapping.CAMERA_INTERFACE.CAMERA_Widget import (
    CameraWidget
)


def main():

    # =========================================================
    # ROOT
    # =========================================================

    root = tk.Tk()

    # =========================================================
    # RIGEL UI
    # =========================================================

    ui = MainWindow(root)

    # =========================================================
    # MAP
    # =========================================================

    map_widget = MapWidget(
        ui.map_container.host
    )

    map_manager = MapManager(
        map_widget
    )

    # =========================================================
    # MOUNT MAP
    # =========================================================

    ui.mount_map_interface(
        map_widget
    )

    # =========================================================
    # MAP CONFIGURATION
    # =========================================================

    map_manager.set_map_provider(
        "esri_satellite"
    )

    map_manager.set_center(
        10.8231,
        106.6297
    )

    map_manager.set_zoom(
        12
    )

    # =========================================================
    # KEEP MAP REFERENCES
    # =========================================================

    ui.map_widget = map_widget
    ui.map_manager = map_manager

    # ---------------------------------------------------------
    # WAYPOINT <-> UI
    # ---------------------------------------------------------
    map_widget.set_waypoint_callback(
        lambda waypoint: ui.update_waypoints(
            map_widget.get_waypoints()
        )
    )
    map_widget.set_waypoint_select_callback(
        lambda index: ui.update_waypoints(
            map_widget.get_waypoints(),
            index,
        )
    )

    # Waypoint mode is OFF at startup. The right-side button
    # enables click-to-add mode; keep the UI synchronized.
    ui.waypoint_panel.set_waypoint_mode(
        map_widget.is_waypoint_mode_enabled()
    )

    ui.map_container.set_provider_status(
        f"MAP: {map_manager.get_map_provider()}"
    )

    ui.log(
        "MAP: interface initialized."
    )

    # =========================================================
    # TELEMETRY
    # =========================================================
    telemetry_manager = TelemetryManager(
        on_data=lambda data: root.after(
            0,
            ui._on_telemetry_data,
            data,
        ),
        on_status=lambda status: root.after(
            0,
            ui.log,
            f"TELEMETRY: {status}",
        ),
        on_error=lambda error: root.after(
            0,
            ui.log,
            f"TELEMETRY ERROR: {error}",
        ),
    )

    ui.mount_telemetry_module(
        telemetry_manager
    )

    # =========================================================
    # CAMERA
    # =========================================================
    camera_widget = CameraWidget(
        ui.video_panel.host,
        width=256,
        height=160,
    )

    # =========================================================
    # MOUNT CAMERA
    # =========================================================
    ui.mount_video_module(
        camera_widget
    )
    # Keep reference
    ui.camera_widget = camera_widget

    # =========================================================
    # MAIN LOOP
    # =========================================================
    try:

        root.mainloop()

    finally:

        # =====================================================
        # STOP TELEMETRY
        # =====================================================
        try:
            telemetry_manager.close()
        except Exception:
            pass

        # =====================================================
        # STOP CAMERA
        # =====================================================
        try:
            camera_widget.stop_camera()
        except Exception:
            pass

        # =====================================================
        # DESTROY CAMERA
        # =====================================================
        try:
            camera_widget.destroy()
        except Exception:
            pass

        # =====================================================
        # DESTROY MAP
        # =====================================================
        try:
            map_widget.destroy()
        except Exception:
            pass

        # =====================================================
        # DESTROY ROOT
        # =====================================================
        try:
            root.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    main()