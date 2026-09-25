"""
Dear PyGui theme mirroring the dark-purple palette from the existing
tkinter style.py (COLOR_SCHEME = "dark_purple") -- same colors, same idea
of a single apply()-style theme call, just expressed via dpg's theme API
instead of ttk styles.
"""

import dearpygui.dearpygui as dpg

# -- Palette (identical to style.py._SCHEMES["dark_purple"]) ---------------
BG = (30, 30, 36)
BG_LIGHT = (42, 42, 51)
BG_LIGHTER = (56, 56, 68)
FG = (224, 223, 240)
ACCENT = (155, 89, 217)
ACCENT_DARK = (108, 63, 160)
ACCENT_HOVER = (176, 122, 230)
STATUS_TEXT = (201, 166, 245)
ERROR = (230, 100, 100)

WINDOW_ROUNDING = 6
FRAME_ROUNDING = 4
FRAME_PADDING = (10, 8)


def build_global_theme() -> int:
    """One theme for all standard widgets -- set globally once via dpg.bind_theme()."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, BG_LIGHT)
            dpg.add_theme_color(dpg.mvThemeCol_Text, FG)
            dpg.add_theme_color(dpg.mvThemeCol_Border, ACCENT_DARK)

            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, BG_LIGHTER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, ACCENT_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, ACCENT_DARK)

            dpg.add_theme_color(dpg.mvThemeCol_Button, BG_LIGHTER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_Header, ACCENT_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, ACCENT)

            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, BG_LIGHT)

            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, WINDOW_ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, FRAME_ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, WINDOW_ROUNDING)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, *FRAME_PADDING)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 8)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 16, 16)
    return theme


def _solid_text_theme(color) -> int:
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, color)
    return theme


def status_text_theme() -> int:
    """Muted status line, equivalent to Status.TLabel in the tkinter original."""
    return _solid_text_theme(STATUS_TEXT)


def error_text_theme() -> int:
    return _solid_text_theme(ERROR)


def title_text_theme() -> int:
    """Accent-colored heading, equivalent to CategoryHeader.TLabel."""
    return _solid_text_theme(ACCENT)


def result_text_theme() -> int:
    """For the actual result (h_f) -- strongest text color."""
    return _solid_text_theme(FG)
