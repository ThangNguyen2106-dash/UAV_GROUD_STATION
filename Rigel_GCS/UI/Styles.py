import tkinter as tk
from tkinter import ttk


class Colors:
    # RIGEL dark mission-control palette
    BG = "#0b1016"
    PANEL = "#111821"
    CARD = "#151e28"
    CARD_ALT = "#18232e"
    BORDER = "#263443"
    BORDER_SOFT = "#1e2a36"
    TEXT = "#91a0b2"
    MUTED = "#617184"
    WHITE = "#f4f7fb"
    CYAN = "#22d3ee"
    GREEN = "#35e58c"
    AMBER = "#f6c453"
    RED = "#ff5c6c"
    BLUE = "#4ea1ff"
    PURPLE = "#a78bfa"
    ORANGE = "#ff9f43"
    DARK = "#0d141c"
    BLACK = "#070b10"


def setup_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        "Rigel.Treeview",
        background=Colors.DARK,
        fieldbackground=Colors.DARK,
        foreground=Colors.WHITE,
        rowheight=29,
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 9),
    )
    style.configure(
        "Rigel.Treeview.Heading",
        background=Colors.CARD_ALT,
        foreground=Colors.TEXT,
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 8, "bold"),
        padding=(5, 6),
    )
    style.map(
        "Rigel.Treeview",
        background=[("selected", "#21445a")],
        foreground=[("selected", Colors.WHITE)],
    )
    style.configure(
        "TScrollbar",
        background=Colors.CARD_ALT,
        troughcolor=Colors.DARK,
        bordercolor=Colors.DARK,
        arrowcolor=Colors.TEXT,
    )
    style.configure(
        "Rigel.TCombobox",
        fieldbackground=Colors.DARK,
        background=Colors.CARD_ALT,
        foreground=Colors.WHITE,
        bordercolor=Colors.BORDER,
        arrowcolor=Colors.CYAN,
        padding=5,
    )


def button(parent, text, command, bg, fg=Colors.WHITE, **kwargs):
    options = dict(
        font=("Segoe UI", 9, "bold"),
        bg=bg,
        fg=fg,
        activebackground=bg,
        activeforeground=fg,
        bd=0,
        relief="flat",
        cursor="hand2",
        pady=8,
        padx=10,
    )
    options.update(kwargs)
    return tk.Button(parent, text=text, command=command, **options)


def section_title(parent, title, subtitle=None):
    box = tk.Frame(parent, bg=Colors.CARD)
    tk.Label(
        box,
        text=title,
        font=("Segoe UI", 9, "bold"),
        fg=Colors.WHITE,
        bg=Colors.CARD,
    ).pack(anchor="w")
    if subtitle:
        tk.Label(
            box,
            text=subtitle,
            font=("Segoe UI", 7),
            fg=Colors.MUTED,
            bg=Colors.CARD,
        ).pack(anchor="w", pady=(1, 0))
    return box