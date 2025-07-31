import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# 🎨 Color Palette (change to fit your taste)
# ---------------------------------------------------------------------------
BG_ROOT         = "#2e2e2e"     # Root background (dark gray)
BG_PANEL        = "#383838"     # Left & right panels
BG_CARD         = "#ffffff"     # Center white cards / tables
FG_TEXT         = "#ffffff"     # White text
FG_MUTED        = "#cccccc"     # Slightly lighter text

BTN_GRAY        = "#4e4e4e"
BTN_GRAY_HOVER  = "#5c5c5c"
BTN_ACCENT      = "#2196F3"     # Blue accent button
BTN_ACCENT_HOVER= "#1976D2"

# ---------------------------------------------------------------------------
# 📝 Fonts
# ---------------------------------------------------------------------------
BODY_FONT       = ("Segoe UI", 10)
HEADING_FONT    = ("Segoe UI", 12, "bold")
SMALL_FONT      = ("Segoe UI", 9)

# ---------------------------------------------------------------------------
# 🌱 Theme Setup Function
# ---------------------------------------------------------------------------
def setup_theme(root: tk.Tk):
    """
    Apply a modern flat theme with rounded buttons, clean dark panels,
    and consistent colors.
    """
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Root window background
    root.configure(bg=BG_ROOT)

    # Global defaults
    root.option_add("*Font", BODY_FONT)
    root.option_add("*Label.Font", BODY_FONT)
    root.option_add("*Label.Foreground", FG_TEXT)
    root.option_add("*Label.Background", BG_PANEL)
    root.option_add("*Frame.Background", BG_PANEL)
    root.option_add("*Button.Font", BODY_FONT)

    # -----------------------------------------------------------------------
    # 🪟 Panels & Labels
    # -----------------------------------------------------------------------
    style.configure("LeftPanel.TFrame", background=BG_PANEL)
    style.configure("RightPanel.TFrame", background=BG_PANEL)
    style.configure("CenterPanel.TFrame", background=BG_ROOT)
    style.configure("Title.TLabel", font=HEADING_FONT, background=BG_PANEL, foreground=FG_TEXT, padding=5)
    style.configure("VideoLabel.TLabel", background=BG_PANEL, foreground=FG_TEXT, font=BODY_FONT)

    # -----------------------------------------------------------------------
    # 🔘 Buttons
    # -----------------------------------------------------------------------
    # Flat gray control button (⏯ ⏸ etc)
    style.configure("Control.TButton",
                    font=BODY_FONT, padding=6,
                    background=BTN_GRAY, foreground=FG_TEXT,
                    borderwidth=0)
    style.map("Control.TButton",
              background=[("active", BTN_GRAY_HOVER)])

    # Accent blue button (Zoom etc)
    style.configure("Accent.TButton",
                    font=BODY_FONT, padding=6,
                    background=BTN_ACCENT, foreground="#fff",
                    borderwidth=0)
    style.map("Accent.TButton",
              background=[("active", BTN_ACCENT_HOVER)])

    # -----------------------------------------------------------------------
    # 🧰 Combobox
    # -----------------------------------------------------------------------
    style.configure("TCombobox",
                    padding=4, borderwidth=0,
                    background="#fff", foreground="#000",
                    fieldbackground="#fff")
    style.map("TCombobox",
              fieldbackground=[("readonly", "#fff")],
              background=[("active", BTN_GRAY_HOVER)])

    # -----------------------------------------------------------------------
    # 📜 Scrollbar
    # -----------------------------------------------------------------------
    for sb in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(sb,
                        gripcount=0,
                        background=BTN_GRAY,
                        darkcolor=BTN_GRAY,
                        lightcolor=BTN_GRAY,
                        troughcolor=BG_PANEL,
                        bordercolor=BG_PANEL,
                        arrowcolor=FG_TEXT)

    # -----------------------------------------------------------------------
    # 🌳 Treeview (table)
    # -----------------------------------------------------------------------
    style.configure("Treeview",
                    background="#ffffff",
                    foreground="#000000",
                    rowheight=24,
                    fieldbackground="#ffffff",
                    borderwidth=0)
    style.map("Treeview",
              background=[("selected", BTN_ACCENT)],
              foreground=[("selected", "#ffffff")])

    # -----------------------------------------------------------------------
    # 🎚 Scale
    # -----------------------------------------------------------------------
    style.configure("Horizontal.TScale", background=BG_PANEL, troughcolor=BTN_GRAY)

    return style
