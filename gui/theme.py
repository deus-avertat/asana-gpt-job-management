import tkinter as tk
from tkinter import ttk

# Hyprland-inspired dark palette with cool accents.
BG_PRIMARY = "#11111B"
BG_SECONDARY = "#181825"
BG_ELEVATED = "#1E1E2E"
BORDER = "#313244"
TEXT_PRIMARY = "#CDD6F4"
TEXT_MUTED = "#A6ADC8"
ACCENT = "#89B4FA"
ACCENT_ACTIVE = "#74C7EC"
SUCCESS = "#A6E3A1"

FONT_FAMILY = "Segoe UI"


def _configure_classic_tk_defaults(root: tk.Misc) -> None:
    """Style classic tk widgets so they blend with ttk components."""
    root.option_add("*Font", f"{FONT_FAMILY} 10")
    root.option_add("*Background", BG_PRIMARY)
    root.option_add("*Foreground", TEXT_PRIMARY)

    # Input/readable widgets
    root.option_add("*Entry.Background", BG_SECONDARY)
    root.option_add("*Entry.Foreground", TEXT_PRIMARY)
    root.option_add("*Entry.InsertBackground", TEXT_PRIMARY)

    root.option_add("*Text.Background", BG_SECONDARY)
    root.option_add("*Text.Foreground", TEXT_PRIMARY)
    root.option_add("*Text.InsertBackground", TEXT_PRIMARY)

    # Buttons and checkboxes
    root.option_add("*Button.Background", BG_ELEVATED)
    root.option_add("*Button.Foreground", TEXT_PRIMARY)
    root.option_add("*Button.ActiveBackground", BORDER)
    root.option_add("*Button.ActiveForeground", TEXT_PRIMARY)

    root.option_add("*Checkbutton.Background", BG_PRIMARY)
    root.option_add("*Checkbutton.Foreground", TEXT_PRIMARY)
    root.option_add("*Checkbutton.ActiveBackground", BG_PRIMARY)
    root.option_add("*Checkbutton.ActiveForeground", TEXT_PRIMARY)


def _configure_ttk_styles(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)

    preferred_themes = ("vista", "clam", "alt", "default")
    available = style.theme_names()
    for theme in preferred_themes:
        if theme in available:
            style.theme_use(theme)
            break

    style.configure(
        ".",
        background=BG_PRIMARY,
        foreground=TEXT_PRIMARY,
        fieldbackground=BG_SECONDARY,
        bordercolor=BORDER,
        font=(FONT_FAMILY, 10),
    )

    style.configure("App.TFrame", background=BG_PRIMARY)
    style.configure("Card.TFrame", background=BG_ELEVATED, relief="flat")

    style.configure(
        "Header.TLabel",
        background=BG_PRIMARY,
        foreground=TEXT_PRIMARY,
        font=(FONT_FAMILY, 10, "bold"),
    )
    style.configure(
        "Muted.TLabel",
        background=BG_PRIMARY,
        foreground=TEXT_MUTED,
        font=(FONT_FAMILY, 9),
    )

    style.configure(
        "TButton",
        background=BG_ELEVATED,
        foreground=TEXT_PRIMARY,
        padding=8,
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "TButton",
        background=[("active", BORDER), ("pressed", BORDER)],
        foreground=[("disabled", TEXT_MUTED)],
    )

    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground=BG_PRIMARY,
        padding=8,
        relief="flat",
        borderwidth=0,
        font=(FONT_FAMILY, 10, "bold"),
    )
    style.map(
        "Primary.TButton",
        background=[("active", ACCENT_ACTIVE), ("pressed", ACCENT_ACTIVE)],
        foreground=[("disabled", TEXT_MUTED)],
    )

    style.configure("TMenubutton", background=BG_ELEVATED, foreground=TEXT_PRIMARY)
    style.map("TMenubutton", background=[("active", BORDER)])

    style.configure(
        "TCheckbutton",
        background=BG_PRIMARY,
        foreground=TEXT_PRIMARY,
    )
    style.map("TCheckbutton", background=[("active", BG_PRIMARY)])

    style.configure(
        "TProgressbar",
        troughcolor=BG_SECONDARY,
        background=ACCENT,
        bordercolor=BORDER,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
    )

    return style


def apply_hyprland_theme(root: tk.Misc) -> ttk.Style:
    """Apply a dark, modern, Hyprland-inspired look to Tk/ttk widgets."""
    try:
        root.configure(bg=BG_PRIMARY)
    except tk.TclError:
        pass

    _configure_classic_tk_defaults(root)
    return _configure_ttk_styles(root)
