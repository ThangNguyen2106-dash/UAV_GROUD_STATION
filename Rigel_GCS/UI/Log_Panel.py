import time
import tkinter as tk
from .Styles import Colors


class LogPanel:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=Colors.CARD)

        tk.Label(
            self.frame,
            text="LOG",
            font=("Segoe UI", 9, "bold"),
            fg=Colors.TEXT,
            bg=Colors.CARD,
        ).pack(anchor="w", padx=10, pady=(6, 2))

        self.text = tk.Text(
            self.frame,
            bg="#101419",
            fg=Colors.CYAN,
            font=("Consolas", 8),
            bd=1,
            relief="solid",
            height=5,
        )
        self.text.pack(fill="both", expand=True, padx=7, pady=(2, 6))

    def write(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.text.insert("end", f"[{timestamp}] {message}\n")
        self.text.see("end")
