import tkinter as tk
from tkinter import ttk
from .Styles import Colors, button


class WaypointPanel:
    """
    UI chỉ hiển thị/chỉnh sửa danh sách waypoint.
    Dữ liệu waypoint thực tế sau này lấy từ MAP_INTERFACE.
    """

    def __init__(self, parent, on_delete=None, on_clear=None, on_select=None, on_toggle_mode=None):
        self.on_delete = on_delete or (lambda: None)
        self.on_clear = on_clear or (lambda: None)
        self.on_select = on_select or (lambda index: None)
        self.on_toggle_mode = on_toggle_mode or (lambda: False)

        self.frame = tk.Frame(parent, bg=Colors.CARD)

        header = tk.Frame(self.frame, bg=Colors.CARD)
        header.pack(fill="x", padx=8, pady=(6, 3))

        tk.Label(
            header,
            text="WAYPOINT",
            font=("Segoe UI", 10, "bold"),
            fg=Colors.CYAN,
            bg=Colors.CARD,
        ).pack(side="left")

        self.mode_button = tk.Button(
            header,
            text="📍 Thiết lập đường bay",
            command=self._toggle_mode,
            font=("Segoe UI", 8, "bold"),
            bg="#1565c0",
            fg=Colors.WHITE,
            activebackground="#1976d2",
            activeforeground=Colors.WHITE,
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=7,
            pady=3,
        )
        self.mode_button.pack(side="right")

        self.mode_status = tk.Label(
            self.frame,
            text="Click bản đồ để thêm WP",
            font=("Segoe UI", 7),
            fg=Colors.TEXT,
            bg=Colors.CARD,
        )
        self.mode_status.pack(anchor="w", padx=8, pady=(0, 4))

        self.home_status = tk.Label(
            self.frame,
            text="HOME: chưa chọn",
            font=("Segoe UI", 7, "bold"),
            fg=Colors.AMBER,
            bg=Colors.CARD,
        )
        self.home_status.pack(anchor="w", padx=8, pady=(0, 4))

        table = tk.Frame(self.frame, bg=Colors.CARD)
        table.pack(fill="x", padx=7, pady=(0, 3))

        self.tree = ttk.Treeview(
            table,
            columns=("id", "lat", "lon", "alt", "speed"),
            show="headings",
            height=10,
            style="Rigel.Treeview",
            )

        self.scrollbar = ttk.Scrollbar(
            table,
            orient="vertical",
            command=self.tree.yview,
            )

        self.tree.configure(
            yscrollcommand=self.scrollbar.set
            )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True,
            )

        self.scrollbar.pack(
            side="right",
            fill="y",
            )

        headers = {
            "id": "WP",
            "lat": "LAT",
            "lon": "LON",
            "alt": "ALT",
            "speed": "SPD",
        }

        widths = {
            "id": 34,
            "lat": 64,
            "lon": 64,
            "alt": 40,
            "speed": 40,
        }

        for col in headers:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center")

        self.tree.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self._select)

        buttons = tk.Frame(self.frame, bg=Colors.CARD)
        buttons.pack(fill="x", padx=7, pady=4)

        self.delete_button = button(
            buttons,
            "Xóa",
            self.on_delete,
            "#c62828",
            pady=4,
        )
        self.delete_button.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.clear_button = button(
            buttons,
            "Xóa tất cả",
            self.on_clear,
            "#37474f",
            pady=4,
        )
        self.clear_button.pack(side="right", fill="x", expand=True, padx=(2, 0))

        # Chỉ cho phép thay đổi mission khi đang ở chế độ thiết lập.
        self.set_edit_mode(False)

    def set_edit_mode(self, enabled):
        """Enable/disable mission editing controls.

        Waypoint creation, deletion and clearing are considered
        mission-editing operations and are only available while
        WAYPOINT MODE / THIẾT LẬP is ON.
        """
        state = "normal" if enabled else "disabled"
        self.delete_button.configure(state=state)
        self.clear_button.configure(state=state)

    def _toggle_mode(self):
        """Ask the map/controller to flip waypoint mode, then sync the UI."""
        enabled = bool(self.on_toggle_mode())
        self.set_waypoint_mode(enabled)

    def set_waypoint_mode(self, enabled):
        """Update the button/status without toggling the map mode."""
        self.set_edit_mode(enabled)
        if enabled:
            self.mode_button.configure(
                text="⛔ Kết thúc thiết lập",
                bg="#c62828",
                activebackground="#d32f2f",
            )
            self.mode_status.configure(
                text="THIẾT LẬP: ON — Click bản đồ để chọn HOME, sau đó thêm WP1, WP2...",
                fg=Colors.GREEN,
            )
        else:
            self.mode_button.configure(
                text="📍 Thiết lập đường bay",
                bg="#1565c0",
                activebackground="#1976d2",
            )
            self.mode_status.configure(
                text="THIẾT LẬP: OFF — Chỉ xem mission",
                fg=Colors.TEXT,
            )

    def set_home_status(self, home):
        """Show the current HOME point, or prompt to place one.

        ``home`` is a {"lat": ..., "lon": ...} dict, or None if HOME
        has not been placed yet (e.g. right after a mission clear).
        """
        if home:
            self.home_status.configure(
                text=f"HOME: {home['lat']:.6f}, {home['lon']:.6f}",
                fg=Colors.GREEN,
            )
        else:
            self.home_status.configure(
                text="HOME: chưa chọn — click bản đồ để đặt điểm home",
                fg=Colors.AMBER,
            )

    def _select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        self.on_select(self.tree.index(selected[0]))

    def set_waypoints(self, waypoints, selected_index=None):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for i, wp in enumerate(waypoints):
            self.tree.insert(
                "",
                "end",
                values=(
                    wp.get("id", f"WP{i+1}"),
                    f"{wp.get('lat', 0):.6f}",
                    f"{wp.get('lon', 0):.6f}",
                    f"{wp.get('alt', 0):.1f}",
                    f"{wp.get('speed', 0):.1f}",
                ),
            )

        if selected_index is not None and 0 <= selected_index < len(waypoints):
            items = self.tree.get_children()
            if selected_index < len(items):
                self.tree.selection_set(items[selected_index])