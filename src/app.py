"""
Orchestrator. This file wires the application together and nothing else:
mark the process DPI-aware (Windows only), create the dpg context, build
the theme, hand off to ui.layout to build the actual window, then run a
manual render loop instead of dpg's blocking start_dearpygui() so the
debounced live-compute in ui.callbacks (see its module docstring) has a
place to be driven from once per frame.

Deliberately contains no UI elements of its own -- no dpg.add_*() widget
calls, no widget tags, no callback bodies, no reading/writing of widget
values. All of that lives in ui/layout.py (what the window looks like)
and ui/callbacks.py (what happens when you interact with it). This file
only ever calls into those two, plus dpg's own lifecycle functions and
the one Windows-only platform quirk below, none of which are UI elements
-- they configure the application/window itself, not something the user
interacts with.
"""

import sys

import dearpygui.dearpygui as dpg

from .ui import layout, settings, theme, callbacks


def _enable_windows_dpi_awareness() -> None:
    """
    Dear PyGui (like Tk) isn't DPI-aware by default. On a scaled Windows
    display (125%/150%/200%, the default on most laptops) that means
    Windows renders the whole window at a smaller internal resolution and
    then stretches the bitmap to fit -- which is exactly the blurry-text
    effect. Marking the process DPI-aware before any window is created
    tells Windows to hand the app real pixels instead. No-op elsewhere.
    """
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)   # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()     # fallback for older Windows
        except Exception:
            pass


def main() -> None:
    _enable_windows_dpi_awareness()

    dpg.create_context()
    dpg.create_viewport(title=settings.WINDOW_TITLE, width=settings.WINDOW_WIDTH, height=settings.WINDOW_HEIGHT)
    dpg.setup_dearpygui()

    dpg.bind_theme(theme.build_global_theme())
    layout.build_ui()
    callbacks.recompute()   # populate the result section with the default inputs

    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()

    # Manual render loop (replaces the usual dpg.start_dearpygui()) so
    # callbacks.maybe_recompute() gets a chance to run once per frame --
    # that's what turns mark_dirty() on an input into an actual debounced
    # recompute() a moment after the user stops dragging/typing.
    while dpg.is_dearpygui_running():
        callbacks.maybe_recompute()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
