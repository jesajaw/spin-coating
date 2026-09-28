"""
Central theme manager for the Spin-Coating app.
Adapted pattern from mtools / Compass style architecture.
"""
import sys
import ctypes
from dataclasses import dataclass
from tkinter import ttk

# -- DPI Awareness -----------------------------------------------------------
def enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

enable_dpi_awareness()

def _detect_scale() -> float:
    if sys.platform != "win32":
        return 1.0
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0

SCALE = _detect_scale()

def px(value: float) -> int:
    return round(value * SCALE)

# -- Themes & Palettes -------------------------------------------------------
_SCHEMES = {
    "dark_purple": dict(
        BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0",
        ACCENT="#9b59d9", ACCENT_DARK="#6c3fa0", STATUS_TEXT="#c9a6f5"
    ),
    "dark_blue": dict(
        BG="#1e1e24", BG_LIGHT="#2a2a33", FG="#e0dff0",
        ACCENT="#4a90d9", ACCENT_DARK="#2f5f9e", STATUS_TEXT="#a6c9f5"
    ),
    "black_white": dict(
        BG="#000000", BG_LIGHT="#1a1a1a", FG="#ffffff",
        ACCENT="#ffffff", ACCENT_DARK="#808080", STATUS_TEXT="#d9d9d9"
    ),
}

_FONT_SCHEMES = {
    "segoe": dict(UI="Segoe UI", MONO="Consolas", SIZE_NORMAL=9, SIZE_HEADER=10, SIZE_TITLE=12),
    "system": dict(UI="TkDefaultFont", MONO="TkFixedFont", SIZE_NORMAL=9, SIZE_HEADER=10, SIZE_TITLE=12),
}

COLOR_SCHEME = "dark_purple"
FONT_SCHEME = "segoe"

_active = _SCHEMES[COLOR_SCHEME]
COLOR_BG = _active["BG"]
COLOR_BG_LIGHT = _active["BG_LIGHT"]
COLOR_FG = _active["FG"]
COLOR = _active["ACCENT"]
COLOR_DARK = _active["ACCENT_DARK"]
COLOR_STATUS_TEXT = _active["STATUS_TEXT"]

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

CELL_WIDTH = px(260)
CELL_HEIGHT = px(110)

@dataclass(frozen=True)
class Layout:
    grid_columns: int = 3
    cell_gap: int = px(12)
    outer_padding: int = px(20)
    control_height: int = px(40)

LAYOUT = Layout()

def apply_style(root) -> None:
    root.configure(bg=COLOR_BG)
    apply_dark_titlebar(root)
    
    style = ttk.Style(root)
    style.theme_use("clam")
    
    style.configure(".", background=COLOR_BG, foreground=COLOR_FG, font=FONT_NORMAL)
    style.configure("TFrame", background=COLOR_BG)
    style.configure("TLabelframe", background=COLOR_BG, foreground=COLOR_FG, bordercolor=COLOR_DARK)
    style.configure("TLabelframe.Label", background=COLOR_BG, foreground=COLOR, font=FONT_HEADER)
    style.configure("TLabel", background=COLOR_BG, foreground=COLOR_FG)
    style.configure("TButton", background=COLOR_BG_LIGHT, foreground=COLOR_FG, bordercolor=COLOR_DARK, padding=6)
    style.map("TButton", background=[("active", COLOR_DARK), ("pressed", COLOR)], foreground=[("active", COLOR_FG)])
    style.configure("Accent.TButton", background=COLOR_DARK, foreground=COLOR_FG, font=FONT_BOLD)
    style.map("Accent.TButton", background=[("active", COLOR)])
    
    style.configure("TEntry", fieldbackground=COLOR_BG_LIGHT, foreground=COLOR_FG, insertcolor=COLOR_FG)
    style.configure("TCombobox", fieldbackground=COLOR_BG_LIGHT, background=COLOR_BG_LIGHT, foreground=COLOR_FG, arrowcolor=COLOR)
    
    style.configure("Cell.TFrame", background=COLOR_BG_LIGHT, bordercolor=COLOR_DARK)
    style.configure("Status.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR_STATUS_TEXT, font=FONT_MONO_NORMAL)
    style.configure("CellTitle.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR_FG, font=FONT_BOLD)
    
    style.configure("CellHover.TFrame", background=COLOR_DARK, bordercolor=COLOR)
    style.configure("StatusHover.TLabel", background=COLOR_DARK, foreground=COLOR_STATUS_TEXT, font=FONT_MONO_NORMAL)
    style.configure("CellTitleHover.TLabel", background=COLOR_DARK, foreground=COLOR_FG, font=FONT_BOLD)
    
    style.configure("ResultText.TLabel", background=COLOR_BG_LIGHT, foreground=COLOR, font=FONT_HEADER)
    style.configure("Icon.TButton", background=COLOR_BG_LIGHT, foreground=COLOR_FG, borderwidth=0, padding=2)

def apply_dark_titlebar(window) -> None:
    if sys.platform != "win32":
        return
    window.update_idletasks()
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        for attr in (20, 19):
            val = ctypes.c_int(1)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val)) == 0:
                break
    except Exception:
        pass