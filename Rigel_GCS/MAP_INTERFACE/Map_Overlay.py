class MapOverlayManager:

    def __init__(self, map_widget):

        self.map_widget = map_widget

        self.overlays = []

    def add_overlay(self, overlay):

        self.overlays.append(
            overlay
        )

    def clear(self):

        for overlay in self.overlays:

            try:
                overlay.delete()

            except Exception:
                pass

        self.overlays.clear()