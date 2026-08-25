import tkinter as tk
from .Styles import Colors


class MapContainer:
    """Visual shell around MAP_INTERFACE; map logic stays outside UI."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Colors.CARD)
        self.mounted_widget = None

        toolbar = tk.Frame(self.frame, bg=Colors.CARD, height=46)
        toolbar.pack(fill="x", padx=10, pady=(8, 6))
        toolbar.pack_propagate(False)

        title = tk.Frame(toolbar, bg=Colors.CARD)
        title.pack(side="left", fill="y")
        tk.Label(title, text="MISSION MAP", font=("Segoe UI", 10, "bold"),
                 fg=Colors.WHITE, bg=Colors.CARD).pack(side="left", pady=3)
        self.provider_label = tk.Label(title, text="  • NOT CONNECTED", font=("Segoe UI", 7, "bold"),
                                       fg=Colors.MUTED, bg=Colors.CARD)
        self.provider_label.pack(side="left", pady=3)

        controls = tk.Frame(toolbar, bg=Colors.CARD)
        controls.pack(side="right")
        self._map_button(controls, "+", self.zoom_in).pack(side="left", padx=2)
        self._map_button(controls, "−", self.zoom_out).pack(side="left", padx=2)
        self._map_button(controls, "HOME", self.go_home, width=6).pack(side="left", padx=2)
        self._map_button(controls, "UAV", self.center_uav, width=5).pack(side="left", padx=2)

        self.host = tk.Frame(self.frame, bg=Colors.BLACK, highlightthickness=1,
                             highlightbackground=Colors.BORDER)
        self.host.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.placeholder_title = tk.Label(self.host, text="MAP INTERFACE", font=("Segoe UI", 18, "bold"),
                                          fg=Colors.CYAN, bg=Colors.BLACK)
        self.placeholder_title.place(relx=.5, rely=.46, anchor="center")
        self.placeholder_text = tk.Label(self.host, text="Waiting for map module…", font=("Segoe UI", 9),
                                         fg=Colors.MUTED, bg=Colors.BLACK)
        self.placeholder_text.place(relx=.5, rely=.54, anchor="center")

    def _map_button(self, parent, text, command, width=4):
        return tk.Button(parent, text=text, command=command, width=width,
                         font=("Segoe UI", 8, "bold"), bg=Colors.CARD_ALT, fg=Colors.WHITE,
                         activebackground=Colors.BORDER, activeforeground=Colors.WHITE,
                         bd=0, relief="flat", cursor="hand2", pady=5)

    def mount(self, widget):
        for placeholder in (self.placeholder_title, self.placeholder_text):
            try:
                placeholder.destroy()
            except tk.TclError:
                pass
        if self.mounted_widget is not None and self.mounted_widget != widget:
            try: self.mounted_widget.destroy()
            except tk.TclError: pass
        self.mounted_widget = widget
        widget.pack(fill="both", expand=True)
        self.provider_label.config(text="  • READY", fg=Colors.GREEN)

    def _map_call(self, method_name, *args):
        if self.mounted_widget is None:
            return
        try:
            if self.mounted_widget.winfo_exists():
                getattr(self.mounted_widget, method_name)(*args)
        except (tk.TclError, AttributeError):
            pass

    def zoom_in(self): self._map_call("zoom_in")
    def zoom_out(self): self._map_call("zoom_out")
    def go_home(self): self._map_call("go_home")
    def center_uav(self): self._map_call("go_home")

    def set_provider_status(self, text):
        self.provider_label.config(text=f"  • {text}", fg=Colors.GREEN if "CONNECTED" in text.upper() or "ESRI" in text.upper() else Colors.TEXT)