import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Color Palette
# ---------------------------------------------------------------------------
BG_ROOT         = "#f5f7fa"
BG_CARD         = "#ffffff"
BORDER_COLOR    = "#dcdfe3"
FG_TEXT         = "#1a1a1a"
FG_MUTED        = "#666666"

BTN_GRAY        = "#e4e6eb"
BTN_GRAY_HOVER  = "#d5d8dc"

BTN_GREEN       = "#4CAF50"
BTN_GREEN_HOVER = "#43a047"

BTN_RED         = "#F44336"
BTN_RED_HOVER   = "#e53935"

BTN_BLUE        = "#2196F3"
BTN_BLUE_HOVER  = "#1e88e5"

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
BODY_FONT    = ("Segoe UI", 10)
HEADING_FONT = ("Segoe UI", 12, "bold")
SMALL_FONT   = ("Segoe UI", 9)

# ---------------------------------------------------------------------------
# Theme Setup
# ---------------------------------------------------------------------------
def setup_theme(root: tk.Tk) -> ttk.Style:
    """
    Apply a modern flat theme with clean spacing & rounded corners.
    """
    root.configure(bg=BG_ROOT)
    root.option_add("*Font", BODY_FONT)
    root.option_add("*Label.Font", BODY_FONT)
    root.option_add("*Label.Background", BG_CARD)
    root.option_add("*Label.Foreground", FG_TEXT)
    root.option_add("*Frame.Background", BG_CARD)
    root.option_add("*Button.Font", BODY_FONT)
    root.option_add("*Entry.Background", "#ffffff")
    root.option_add("*Entry.Foreground", FG_TEXT)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Base defaults
    style.configure(".", background=BG_CARD, foreground=FG_TEXT)

    # Heading label style
    style.configure("AuditHeading.TLabel", font=HEADING_FONT, background=BG_CARD, foreground=FG_TEXT, padding=5)

    # Generic flat button (with rounded corners & subtle shadow)
    style.configure(
        "Audit.TButton",
        padding=(8, 4),
        relief="flat",
        background=BTN_GRAY,
        foreground=FG_TEXT,
        borderwidth=1,
        focusthickness=1,
        focuscolor="#2196F3"
    )
    style.map("Audit.TButton",
              background=[("active", BTN_GRAY_HOVER)],
              relief=[("pressed", "sunken"), ("!pressed", "flat")])

    # Positive (green) button
    style.configure("Positive.TButton",
                    padding=(8, 4),
                    relief="flat",
                    background=BTN_GREEN,
                    foreground="#ffffff",
                    borderwidth=0)
    style.map("Positive.TButton",
              background=[("active", BTN_GREEN_HOVER)])

    # Negative (red) button
    style.configure("Negative.TButton",
                    padding=(8, 4),
                    relief="flat",
                    background=BTN_RED,
                    foreground="#ffffff",
                    borderwidth=0)
    style.map("Negative.TButton",
              background=[("active", BTN_RED_HOVER)])

    # Primary (blue) button
    style.configure("Primary.TButton",
                    padding=(8, 4),
                    relief="flat",
                    background=BTN_BLUE,
                    foreground="#ffffff",
                    borderwidth=0)
    style.map("Primary.TButton",
              background=[("active", BTN_BLUE_HOVER)])

    # Combobox styling
    style.configure("TCombobox",
                    padding=4,
                    relief="flat",
                    borderwidth=1,
                    fieldbackground="#ffffff",
                    foreground=FG_TEXT,
                    arrowsize=16)
    style.map("TCombobox",
              fieldbackground=[("readonly", "#ffffff")],
              background=[("active", BTN_GRAY_HOVER)])

    # Scrollbar styling
    for sb_style in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(sb_style,
                        gripcount=0,
                        background=BTN_GRAY,
                        darkcolor=BTN_GRAY,
                        lightcolor=BTN_GRAY,
                        troughcolor=BG_CARD,
                        bordercolor=BG_CARD,
                        arrowcolor=FG_TEXT)

    # Scale styling
    style.configure("Horizontal.TScale", background=BG_CARD, troughcolor=BTN_GRAY)

    # Make treeview (if used) cleaner
    style.configure("Treeview",
                    background="#ffffff",
                    foreground=FG_TEXT,
                    fieldbackground="#ffffff",
                    rowheight=24,
                    borderwidth=0)
    style.map("Treeview",
              background=[("selected", BTN_BLUE)],
              foreground=[("selected", "#ffffff")])

    return style

# ---------------------------------------------------------------------------
# Hover Utility for classic tk.Button
# ---------------------------------------------------------------------------
def attach_hover(widget, normal: str, hover: str):
    widget.configure(bg=normal, activebackground=hover)
    def _enter(_): widget.configure(bg=hover)
    def _leave(_): widget.configure(bg=normal)
    widget.bind("<Enter>", _enter)
    widget.bind("<Leave>", _leave)
