"""
Main application window, as a 2x2 grid of sections:

    Input               | Resin Presets
    Statistical Deviation | Result

Input pairs with Presets (both are about setting up what to compute with);
Deviation pairs with Result (Deviation configures what the Result section
shows alongside the nominal value). Statistical deviation is always
visible -- a single None / Gauss / Monte Carlo selector decides what (if
anything) gets computed, see model/deviation.py.

No formula explanation or citation text lives here on purpose -- that's
in README.md, which doesn't fight for the same vertical space and can
say more about it than a wrapped label ever could.

Every input/output widget gets an explicit width=settings.CONTENT_WIDTH
instead of stretching to fill its column -- otherwise resizing the window
stretches every field too, shoving its label far to the right with a
large empty gap in between. Each column's child_window has a fixed
settings.COLUMN_WIDTH for the same reason, and no_scrollbar=True with a
height sized generously for its section's worst case (e.g. Monte Carlo
selected in Deviation, showing every extra widget it can) so nothing
inside a section is ever clipped or requires scrolling to reach. See
settings.WINDOW_HEIGHT for why the *outer* window is nonetheless left
scrollable, as a fallback rather than a first resort.

This file only describes what the window looks like: which widgets
exist, their tags (from tags.py), their default values (from
model/parameters.py and ui/settings.py), and which callback (from
callbacks.py) fires when they change. It contains no computation and no
widget-value reading of its own. Continuous inputs (drag floats/ints,
sliders) wire to callbacks.mark_dirty, which is debounced (see
callbacks.py's module docstring); discrete ones (combos, checkboxes,
buttons) wire straight to their handler since there's no burst to
coalesce for a single click.
"""

import dearpygui.dearpygui as dpg

from ..model import parameters, deviation
from .. import store as resins_store
from . import tags, settings, theme, callbacks

W = settings.CONTENT_WIDTH
COL = settings.COLUMN_WIDTH


def _section_title(text: str) -> None:
    dpg.add_text(text)
    dpg.bind_item_theme(dpg.last_item(), theme.title_text_theme())
    dpg.add_separator()


def _build_input() -> None:
    _section_title("Input")

    dpg.add_drag_float(label="Spin speed [rpm]", tag=tags.T_RPM, default_value=parameters.RPM_DEFAULT,
                        min_value=parameters.RPM_MIN, max_value=parameters.RPM_MAX, speed=10.0,
                        width=W, callback=callbacks.mark_dirty)
    dpg.add_drag_float(label="Viscosity [cP = mPa*s]", tag=tags.T_VISCOSITY,
                        default_value=parameters.VISCOSITY_CP_DEFAULT,
                        min_value=parameters.VISCOSITY_CP_MIN, max_value=parameters.VISCOSITY_CP_MAX,
                        speed=0.5, width=W, callback=callbacks.mark_dirty)
    dpg.add_drag_float(label="Solution density [g/cm3]", tag=tags.T_DENSITY,
                        default_value=parameters.DENSITY_DEFAULT,
                        min_value=parameters.DENSITY_MIN, max_value=parameters.DENSITY_MAX,
                        speed=0.01, width=W, callback=callbacks.mark_dirty)
    dpg.add_drag_float(label="Evaporation rate E [\u00b5m/s]", tag=tags.T_EVAP,
                        default_value=parameters.EVAP_UM_S_DEFAULT,
                        min_value=parameters.EVAP_UM_S_MIN, max_value=parameters.EVAP_UM_S_MAX,
                        speed=0.01, format="%.3f", width=W, callback=callbacks.mark_dirty)
    with dpg.tooltip(dpg.last_item()):
        dpg.add_text(
            "Volume flux of evaporating solvent per unit area.\n"
            "Typical order of magnitude: 0.01-1 \u00b5m/s. Best calibrated\n"
            "against reference measurements for the specific solvent.",
            wrap=320,
        )

    dpg.add_spacer(height=6)
    dpg.add_combo(label="Solids fraction from", tag=tags.T_MODE,
                  items=[tags.MODE_DIRECT, tags.MODE_WEIGHT], default_value=tags.MODE_DIRECT,
                  width=W, callback=callbacks.on_mode_change)

    with dpg.group(tag=tags.T_GROUP_DIRECT):
        dpg.add_slider_float(label="Solids volume fraction c0 [%]", tag=tags.T_C0_DIRECT,
                              default_value=parameters.SOLIDS_PCT_DEFAULT,
                              min_value=parameters.SOLIDS_PCT_MIN, max_value=parameters.SOLIDS_PCT_MAX,
                              width=W, callback=callbacks.mark_dirty)

    with dpg.group(tag=tags.T_GROUP_WEIGHT, show=False):
        dpg.add_slider_float(label="Solids weight fraction w [%]", tag=tags.T_WEIGHT_PCT,
                              default_value=parameters.WEIGHT_PCT_DEFAULT,
                              min_value=parameters.SOLIDS_PCT_MIN, max_value=parameters.SOLIDS_PCT_MAX,
                              width=W, callback=callbacks.mark_dirty)
        dpg.add_drag_float(label="Solute density (pure) [g/cm3]", tag=tags.T_DENSITY_SOLUTE,
                            default_value=parameters.DENSITY_SOLUTE_DEFAULT,
                            min_value=0.1, max_value=10.0, speed=0.01, width=W, callback=callbacks.mark_dirty)
        dpg.add_drag_float(label="Solvent density (pure) [g/cm3]", tag=tags.T_DENSITY_SOLVENT,
                            default_value=parameters.DENSITY_SOLVENT_DEFAULT,
                            min_value=0.1, max_value=3.0, speed=0.01, width=W, callback=callbacks.mark_dirty)


def _build_presets() -> None:
    _section_title("Resin Presets")
    with dpg.group(horizontal=True):
        dpg.add_combo(tag=tags.T_PRESET_COMBO, items=resins_store.list_presets(), width=W - 70)
        dpg.add_button(label="Load", callback=callbacks.on_load_preset)
    with dpg.group(horizontal=True):
        dpg.add_input_text(tag=tags.T_PRESET_NAME, hint="Name for new preset", width=W - 130)
        dpg.add_button(label="Save as preset", callback=callbacks.on_save_preset)
    dpg.add_input_text(tag=tags.T_PRESET_NOTES, hint="Note (optional, e.g. source/calibration date)", width=W)
    dpg.add_text("", tag=tags.T_PRESET_STATUS)
    dpg.bind_item_theme(tags.T_PRESET_STATUS, theme.status_text_theme())
    with dpg.tooltip(tags.T_PRESET_COMBO):
        dpg.add_text(
            "Presets store material properties (viscosity, density,\n"
            "evaporation rate, solids fraction) -- not the spin speed, since\n"
            "that is a per-run process choice, not a material property.",
            wrap=300,
        )


def _build_deviation() -> None:
    _section_title("Statistical Deviation")

    dpg.add_combo(label="Method", tag=tags.T_STAT_METHOD,
                  items=[tags.METHOD_NONE, tags.METHOD_GAUSS, tags.METHOD_MC],
                  default_value=tags.METHOD_NONE, width=W, callback=callbacks.on_stat_method_change)

    with dpg.group(tag=tags.T_GROUP_UNCERTAINTY, show=False):
        with dpg.group(tag=tags.T_GROUP_MC_OPTIONS, show=False):
            dpg.add_combo(label="Distribution shape (Monte Carlo)", tag=tags.T_STAT_MC_DIST,
                          items=[d.value for d in deviation.DistKind],
                          default_value=deviation.DistKind.GAUSS.value, width=W,
                          callback=callbacks.on_stat_method_change)
            dpg.add_drag_int(label="Number of samples", tag=tags.T_STAT_MC_N,
                              default_value=settings.MONTE_CARLO_DEFAULT_N,
                              min_value=settings.MONTE_CARLO_MIN_N, max_value=settings.MONTE_CARLO_MAX_N,
                              width=W, callback=callbacks.mark_dirty)

        dpg.add_spacer(height=4)
        dpg.add_text("Uncertainties (\u00b1, 0 = none):")
        dpg.bind_item_theme(dpg.last_item(), theme.status_text_theme())

        dpg.add_drag_float(label="\u00b1 Spin speed [rpm]", tag=tags.T_SIGMA_RPM, default_value=0.0,
                            min_value=0.0, max_value=settings.SIGMA_RPM_MAX, width=W,
                            callback=callbacks.mark_dirty)
        dpg.add_drag_float(label="\u00b1 Viscosity [cP]", tag=tags.T_SIGMA_VISCOSITY, default_value=0.0,
                            min_value=0.0, max_value=settings.SIGMA_VISCOSITY_CP_MAX, width=W,
                            callback=callbacks.mark_dirty)
        dpg.add_drag_float(label="\u00b1 Density [g/cm3]", tag=tags.T_SIGMA_DENSITY, default_value=0.0,
                            min_value=0.0, max_value=settings.SIGMA_DENSITY_MAX, speed=0.005, width=W,
                            callback=callbacks.mark_dirty)
        dpg.add_drag_float(label="\u00b1 Evaporation rate [\u00b5m/s]", tag=tags.T_SIGMA_EVAP,
                            default_value=0.0, min_value=0.0, max_value=settings.SIGMA_EVAP_UM_S_MAX,
                            speed=0.005, format="%.4f", width=W, callback=callbacks.mark_dirty)
        dpg.add_drag_float(label="\u00b1 Solids fraction [pp]", tag=tags.T_SIGMA_C0,
                            default_value=0.0, min_value=0.0, max_value=settings.SIGMA_SOLIDS_PP_MAX,
                            width=W, callback=callbacks.mark_dirty)
        with dpg.tooltip(dpg.last_item()):
            dpg.add_text(
                "Always interpreted as 1-sigma for Gauss.\n"
                "For Monte Carlo, interpreted according to the chosen\n"
                "distribution shape: sigma (Normal) or half-width (Uniform/Triangular).",
                wrap=300,
            )


def _build_result() -> None:
    _section_title("Result")

    dpg.add_text("-- nm", tag=tags.T_RESULT_HF_NM)
    dpg.bind_item_theme(tags.T_RESULT_HF_NM, theme.result_text_theme())
    dpg.add_text("", tag=tags.T_RESULT_HF_UM)
    dpg.bind_item_theme(tags.T_RESULT_HF_UM, theme.status_text_theme())

    dpg.add_spacer(height=4)
    with dpg.group(horizontal=True):
        dpg.add_text("Wet transition thickness h_s:")
        dpg.add_text("--", tag=tags.T_RESULT_HS_UM)
    with dpg.group(horizontal=True):
        dpg.add_text("Omega used:")
        dpg.add_text("--", tag=tags.T_RESULT_OMEGA)
    with dpg.group(horizontal=True):
        dpg.add_text("Volume fraction c0 used:")
        dpg.add_text("--", tag=tags.T_RESULT_C0)

    dpg.add_spacer(height=6)
    dpg.add_separator()
    dpg.add_text("", tag=tags.T_RESULT_STAT_1)
    dpg.bind_item_theme(tags.T_RESULT_STAT_1, theme.result_text_theme())
    dpg.add_text("", tag=tags.T_RESULT_STAT_2)
    dpg.bind_item_theme(tags.T_RESULT_STAT_2, theme.status_text_theme())
    dpg.add_text("", tag=tags.T_RESULT_STAT_3)
    dpg.bind_item_theme(tags.T_RESULT_STAT_3, theme.status_text_theme())

    dpg.add_spacer(height=6)
    dpg.add_text("", tag=tags.T_STATUS)
    dpg.bind_item_theme(tags.T_STATUS, theme.status_text_theme())


def build_ui() -> None:
    with dpg.window(tag="main_window"):
        dpg.add_text("Meyerhofer Model: Spin Coating Final Film Thickness", tag="title")
        dpg.bind_item_theme("title", theme.title_text_theme())
        dpg.add_spacer(height=8)

        # -- Row 1: Input | Resin Presets --------------------------------------
        with dpg.group(horizontal=True):
            with dpg.child_window(width=COL, height=350, border=True, no_scrollbar=True):
                _build_input()
            with dpg.child_window(width=COL, height=350, border=True, no_scrollbar=True):
                _build_presets()

        dpg.add_spacer(height=10)

        # -- Row 2: Statistical Deviation | Result -----------------------------
        with dpg.group(horizontal=True):
            with dpg.child_window(width=COL, height=400, border=True, no_scrollbar=True):
                _build_deviation()
            with dpg.child_window(width=COL, height=400, border=True, no_scrollbar=True):
                _build_result()
