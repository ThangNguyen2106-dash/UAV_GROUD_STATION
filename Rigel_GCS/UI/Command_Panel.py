import tkinter as tk
from .Styles import Colors, button


class CommandPanel:
    def __init__(self, parent, on_command=None):
        self.on_command = on_command or (lambda command: None)
        self.frame = tk.Frame(parent, bg=Colors.CARD)

        header = tk.Frame(self.frame, bg=Colors.CARD)
        header.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(header, text="FLIGHT COMMANDS", font=("Segoe UI", 9, "bold"),
                 fg=Colors.WHITE, bg=Colors.CARD).pack(side="left")
        tk.Label(header, text="SAFETY", font=("Segoe UI", 7, "bold"),
                 fg=Colors.RED, bg=Colors.CARD).pack(side="right")

        box = tk.Frame(self.frame, bg=Colors.CARD)
        box.pack(fill="x", padx=10, pady=(0, 10))
        self.arm = button(box, "ARM", lambda: self.on_command("ARM"), "#1f6b46", pady=9)
        self.arm.pack(fill="x", pady=2)
        button(box, "TAKEOFF", lambda: self.on_command("TAKEOFF"), "#245b96", pady=8).pack(fill="x", pady=2)
        button(box, "RTL / RETURN", lambda: self.on_command("RTL"), "#5a3d9a", pady=8).pack(fill="x", pady=2)
        button(box, "LAND", lambda: self.on_command("LAND"), "#9a5a21", pady=8).pack(fill="x", pady=2)
        button(box, "PAUSE / HOLD", lambda: self.on_command("PAUSE"), "#8f2937", pady=8).pack(fill="x", pady=2)

    def set_armed(self, armed):
        self.arm.config(
            text="DISARM" if armed else "ARM",
            bg="#9a2e3d" if armed else "#1f6b46",
            activebackground="#9a2e3d" if armed else "#1f6b46",
        )