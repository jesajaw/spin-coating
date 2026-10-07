"""
Central theme for the app (same palette architecture as mtools): several
schemes are available, the active one is chosen via COLOR_SCHEME. Every
window (main + plot) calls apply_style() once and shares the same style
names (Cell.TFrame, CellTitle.TLabel, Status.TLabel, ...).
"""

import os
import sys
import ctypes
from dataclasses import dataclass
from tkinter import ttk


_SCHEMES = {
    "dark_purple": dict(BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0", ACCENT="#9b59d9", ACCENT_DARK="#6c3fa0", STATUS_TEXT="#c9a6f5", GRID="#3c3c48"),
    "dark_blue": dict(BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0", ACCENT="#4a90d9", ACCENT_DARK="#2f5f9e", STATUS_TEXT="#a6c9f5", GRID="#3c3c48"),
    "black_white": dict(BG="#000000", BG_LIGHT="#1a1a1a", FG="#ffffff", ACCENT="#ffffff", ACCENT_DARK="#5a5a5a", STATUS_TEXT="#d9d9d9", GRID="#333333"),
}

_FONT_SCHEMES = {
    "segoe": dict(UI="Segoe UI", MONO="Consolas", SIZE_NORMAL=9, SIZE_HEADER=10, SIZE_TITLE=13),
    "system": dict(UI="TkDefaultFont", MONO="TkFixedFont", SIZE_NORMAL=9, SIZE_HEADER=10, SIZE_TITLE=13),
}

DEFAULT_COLOR_SCHEME = "dark_purple"
# The scheme can be chosen without editing code: set SPIN_COATING_THEME=dark_blue (or black_white) before starting.
COLOR_SCHEME = os.environ.get("SPIN_COATING_THEME", DEFAULT_COLOR_SCHEME)
if COLOR_SCHEME not in _SCHEMES:
    raise ValueError(f"Unknown theme {COLOR_SCHEME!r} (SPIN_COATING_THEME). Available: {', '.join(_SCHEMES)}")
FONT_SCHEME = "segoe"

_active = _SCHEMES[COLOR_SCHEME]
COLOR_BG = _active["BG"]
COLOR_BG_LIGHT = _active["BG_LIGHT"]
COLOR_FG = _active["FG"]
COLOR = _active["ACCENT"]
COLOR_DARK = _active["ACCENT_DARK"]
COLOR_STATUS_TEXT = _active["STATUS_TEXT"]
COLOR_GRID = _active["GRID"]
COLOR_ERROR = "#e06666"

_active_font = _FONT_SCHEMES[FONT_SCHEME]
FONT_UI = _active_font["UI"]
FONT_MONO = _active_font["MONO"]
FONT_SIZE_NORMAL = _active_font["SIZE_NORMAL"]
FONT_SIZE_HEADER = _active_font["SIZE_HEADER"]
FONT_SIZE_TITLE = _active_font["SIZE_TITLE"]

FONT_NORMAL = (FONT_UI, FONT_SIZE_NORMAL)
FONT_BOLD = (FONT_UI, FONT_SIZE_NORMAL, "bold")
FONT_HEADER = (FONT_UI, FONT_SIZE_HEADER, "bold")
FONT_TITLE = (FONT_UI, FONT_SIZE_TITLE, "bold")
FONT_MONO_NORMAL = (FONT_MONO, FONT_SIZE_NORMAL)
FONT_SMALL = (FONT_UI, 8)

CELL_WIDTH = 260
CELL_HEIGHT = 70
FIELD_HEIGHT = 26


TEX_SIZE = 9.5            # pt, size of rendered mathtext labels (see ui/tex.py)
_tex_dpi = 96.0


def tex_dpi() -> float:
    """Pixels per inch of the screen (set by apply_style); mathtext is rendered at this resolution."""
    return _tex_dpi


@dataclass(frozen=True)
class Layout:
    outer_padding: int = 12
    col_gap: int = 12
    row_gap: int = 10
    left_col_width: int = 470       # model selection + input/uncertainty tabs

LAYOUT = Layout()


def apply_style(root) -> None:
    global _tex_dpi
    root.configure(bg=COLOR_BG)
    apply_dark_titlebar(root)
    try:
        _tex_dpi = float(root.winfo_fpixels("1i"))
    except Exception:
        _tex_dpi = 96.0

    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=COLOR_BG, foreground=COLOR_FG, font=FONT_NORMAL)
    style.configure("TFrame", background=COLOR_BG)
    style.configure("TLabelframe", background=COLOR_BG, foreground=COLOR_FG, bordercolor=COLOR_DARK)
    style.configure("TLabelframe.Label", background=COLOR_BG, foreground=COLOR, font=FONT_HEADER)
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG)
    style.configure("TSeparator", background=COLOR_DARK)

    style.configure("TButton", background=COLOR_BG_LIGHT, foreground=COLOR_FG, bordercolor=COLOR_DARK, focusthickness=1, padding=6)
    style.map("TButton", background=[("active", COLOR_DARK), ("pressed", COLOR)], foreground=[("active", COLOR_FG)])
    style.configure("Accent.TButton", background=COLOR_DARK, foreground=COLOR_FG, font=FONT_BOLD, padding=6)
    style.map("Accent.TButton", background=[("active", COLOR)])

    style.configure("TEntry", fieldbackground=COLOR_BG_LIGHT, foreground=COLOR_FG, insertcolor=COLOR_FG, bordercolor=COLOR_DARK)
    style.configure("TCombobox", fieldbackground=COLOR_BG_LIGHT, background=COLOR_BG_LIGHT, foreground=COLOR_FG, arrowcolor=COLOR)
    style.map("TCombobox", fieldbackground=[("readonly", COLOR_BG_LIGHT), ("disabled", COLOR_BG)],
              background=[("active", COLOR_BG_LIGHT), ("readonly", COLOR_BG_LIGHT)],
              foreground=[("readonly", COLOR_FG)], selectbackground=[("readonly", COLOR_BG_LIGHT)],
              selectforeground=[("readonly", COLOR_FG)], arrowcolor=[("active", COLOR_FG)])
    # the drop-down list of a combobox is a plain tk Listbox: colour it through the option database
    root.option_add("*TCombobox*Listbox.background", COLOR_BG_LIGHT)
    root.option_add("*TCombobox*Listbox.foreground", COLOR_FG)
    root.option_add("*TCombobox*Listbox.selectBackground", COLOR_DARK)
    root.option_add("*TCombobox*Listbox.selectForeground", COLOR_FG)
    # The clam theme turns the label of a hovered check/radio button almost white (its "lighter" colour) while
    # the foreground stays light -> unreadable. Pin background/foreground for every state instead.
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, background=COLOR_BG, foreground=COLOR_FG, focuscolor=COLOR_BG,
                        indicatorbackground=COLOR_BG_LIGHT, indicatorforeground=COLOR,
                        upperbordercolor=COLOR_DARK, lowerbordercolor=COLOR_DARK)
        style.map(name,
                  background=[("active", COLOR_BG), ("pressed", COLOR_BG), ("disabled", COLOR_BG)],
                  foreground=[("active", COLOR), ("pressed", COLOR), ("disabled", COLOR_DARK)],
                  indicatorbackground=[("pressed", COLOR_BG_LIGHT), ("active", COLOR_BG_LIGHT),
                                       ("disabled", COLOR_BG)],
                  indicatorforeground=[("disabled", COLOR_DARK)],
                  upperbordercolor=[("active", COLOR)], lowerbordercolor=[("active", COLOR)])

    style.configure("TNotebook", background=COLOR_BG, bordercolor=COLOR_DARK, tabmargins=(0, 2, 0, 0))
    style.configure("TNotebook.Tab", background=COLOR_BG_LIGHT, foreground=COLOR_FG, padding=(14, 5),
                    bordercolor=COLOR_DARK)
    # clam makes the selected tab bigger (padding + expand map) -> pin both so selected/unselected tabs are equal
    style.map("TNotebook.Tab", background=[("selected", COLOR_DARK), ("active", COLOR_BG_LIGHT)],
              foreground=[("selected", COLOR_FG), ("active", COLOR)],
              padding=[("selected", (14, 5)), ("!selected", (14, 5))],
              expand=[("selected", (0, 0, 0, 0)), ("!selected", (0, 0, 0, 0))])
    style.configure("Vertical.TScrollbar", background=COLOR_BG_LIGHT, troughcolor=COLOR_BG,
                    bordercolor=COLOR_BG, arrowcolor=COLOR_FG, lightcolor=COLOR_BG_LIGHT, darkcolor=COLOR_BG_LIGHT)
    style.map("Vertical.TScrollbar", background=[("active", COLOR_DARK)])

    style.configure("Cell.TFrame", background=COLOR_BG_LIGHT, bordercolor=COLOR_DARK)
    style.configure("Status.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR_STATUS_TEXT, font=FONT_MONO_NORMAL)
    style.configure("CellTitle.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR_FG, font=FONT_BOLD)
    style.configure("CellHover.TFrame", background=COLOR_DARK, bordercolor=COLOR)
    style.configure("StatusHover.TLabel", background=COLOR_DARK, foreground=COLOR_STATUS_TEXT, font=FONT_MONO_NORMAL)
    style.configure("CellTitleHover.TLabel", background=COLOR_DARK, foreground=COLOR_FG, font=FONT_BOLD)

    style.configure("CategoryHeader.TLabel", background=COLOR_BG, foreground=COLOR, font=FONT_HEADER)
    style.configure("Help.TLabel", background=COLOR_BG, foreground=COLOR_STATUS_TEXT, font=FONT_SMALL)
    style.configure("FieldLabel.TLabel", background=COLOR_BG, foreground=COLOR_FG, font=FONT_NORMAL)
    style.configure("ResultBig.TLabel", background=COLOR_BG, foreground=COLOR, font=(FONT_UI, 24, "bold"))
    style.configure("Heading.TLabel", background=COLOR_BG, foreground=COLOR, font=(FONT_UI, 12, "bold"))
    style.configure("Body.TLabel", background=COLOR_BG, foreground=COLOR_FG, font=FONT_NORMAL)
    style.configure("Note.TLabel", background=COLOR_BG, foreground=COLOR_STATUS_TEXT, font=(FONT_UI, 9, "italic"))
    style.configure("ResultSmall.TLabel", background=COLOR_BG, foreground=COLOR_STATUS_TEXT, font=FONT_NORMAL)
    style.configure("Error.TLabel", background=COLOR_BG, foreground=COLOR_ERROR, font=FONT_BOLD)

    style.configure("Icon.TButton", background=COLOR_BG, foreground=COLOR_FG, borderwidth=0, padding=2)
    style.map("Icon.TButton", background=[("active", COLOR_BG)], foreground=[("active", COLOR)])


def _is_win() -> bool:
    return sys.platform == "win32"

def enable_dpi_awareness() -> None:
    if not _is_win():
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def apply_dark_titlebar(window) -> None:
    if not _is_win():
        return
    window.update_idletasks()
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        for attribute in (20, 19):
            value = ctypes.c_int(1)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass

def force_dark_titlebar(window) -> None:
    if not _is_win():
        return
    window.update()
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        rendering_policy = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(rendering_policy), ctypes.sizeof(rendering_policy))
    except Exception:
        pass
