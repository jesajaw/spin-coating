"""
The glue between the UI and the model: every function here reads current
widget values via dpg.get_value(), hands them to model.compute /
model.deviation / store, and writes the result back via dpg.set_value() /
dpg.configure_item(). None of them do any actual computation themselves --
that always lives in model/ -- these are strictly "read widgets, call
compute, write widgets" wiring, which is what layout.py's widgets call as
their `callback=`.

Kept separate from layout.py so layout.py only has to describe *what the
window looks like*, not *what happens when you interact with it*.

Compute is always live now (no "auto-compute" toggle) -- but a slider or
drag box fires its callback on every pixel of movement, and typing a
number fires it on every keystroke. Running the full model (potentially
including a several-thousand-sample Monte Carlo run) on every single one
of those would make dragging feel laggy and could let an old, slower
computation finish after a newer one and overwrite it with a stale
result. mark_dirty()/maybe_recompute() below debounce that: every input
widget's callback is mark_dirty(), which only records that something
changed and when; the render loop (see app.py) calls maybe_recompute()
once per frame, which actually runs recompute() only once no further
change has come in for _DEBOUNCE_SECONDS. Discrete, infrequent choices
(a combo, a checkbox, a button) skip the debounce and call recompute()
directly -- there's no burst to coalesce for a single click.
"""

import time

import dearpygui.dearpygui as dpg

from ..model import compute as model, deviation, parameters
from .. import store as resins_store
from . import tags, theme

_DEBOUNCE_SECONDS = 0.12   # short enough to feel live, long enough to coalesce a drag/typing burst
_dirty = False
_last_change_at = 0.0


def mark_dirty(sender=None, data=None) -> None:
    """Callback for continuous inputs (drag floats/ints, sliders): records
    that something changed, but does not compute anything itself."""
    global _dirty, _last_change_at
    _dirty = True
    _last_change_at = time.monotonic()


def maybe_recompute() -> None:
    """Call once per frame from the render loop. Only runs the real
    recompute() once _DEBOUNCE_SECONDS have passed since the last change,
    so a fast drag or a burst of keystrokes triggers one compute, not one
    per event."""
    global _dirty
    if _dirty and (time.monotonic() - _last_change_at) >= _DEBOUNCE_SECONDS:
        _dirty = False
        recompute()


# ============================================================================
# Reading widget state into model inputs
# ============================================================================

def _resolve_solids_fraction() -> float:
    if dpg.get_value(tags.T_MODE) == tags.MODE_DIRECT:
        return dpg.get_value(tags.T_C0_DIRECT) / 100.0
    w = dpg.get_value(tags.T_WEIGHT_PCT) / 100.0
    return model.volume_fraction_from_weight_fraction(
        w, dpg.get_value(tags.T_DENSITY_SOLUTE), dpg.get_value(tags.T_DENSITY_SOLVENT)
    )


def _build_input_uncertainties(c0: float) -> deviation.InputUncertainties:
    return deviation.InputUncertainties(
        rpm=deviation.ParamUncertainty(dpg.get_value(tags.T_RPM), dpg.get_value(tags.T_SIGMA_RPM)),
        viscosity_cp=deviation.ParamUncertainty(dpg.get_value(tags.T_VISCOSITY), dpg.get_value(tags.T_SIGMA_VISCOSITY)),
        density_g_cm3=deviation.ParamUncertainty(dpg.get_value(tags.T_DENSITY), dpg.get_value(tags.T_SIGMA_DENSITY)),
        evaporation_rate_um_s=deviation.ParamUncertainty(dpg.get_value(tags.T_EVAP), dpg.get_value(tags.T_SIGMA_EVAP)),
        solids_fraction=deviation.ParamUncertainty(c0, dpg.get_value(tags.T_SIGMA_C0) / 100.0),
    )


def _build_scatter_inputs(c0: float, kind: deviation.DistKind) -> deviation.ScatterInputs:
    return deviation.ScatterInputs(
        rpm=deviation.ScatterParam(dpg.get_value(tags.T_RPM), kind, dpg.get_value(tags.T_SIGMA_RPM)),
        viscosity_cp=deviation.ScatterParam(dpg.get_value(tags.T_VISCOSITY), kind, dpg.get_value(tags.T_SIGMA_VISCOSITY)),
        density_g_cm3=deviation.ScatterParam(dpg.get_value(tags.T_DENSITY), kind, dpg.get_value(tags.T_SIGMA_DENSITY)),
        evaporation_rate_um_s=deviation.ScatterParam(dpg.get_value(tags.T_EVAP), kind, dpg.get_value(tags.T_SIGMA_EVAP)),
        solids_fraction=deviation.ScatterParam(c0, kind, dpg.get_value(tags.T_SIGMA_C0) / 100.0),
    )


def _clear_stat_output() -> None:
    dpg.set_value(tags.T_RESULT_STAT_1, "")
    dpg.set_value(tags.T_RESULT_STAT_2, "")
    dpg.set_value(tags.T_RESULT_STAT_3, "")


# ============================================================================
# The main compute callback
# ============================================================================

def recompute(sender=None, _data=None) -> None:
    try:
        c0 = _resolve_solids_fraction()
        params = model.from_lab_units(
            spin_speed_rpm=dpg.get_value(tags.T_RPM),
            viscosity_cp=dpg.get_value(tags.T_VISCOSITY),
            density_g_cm3=dpg.get_value(tags.T_DENSITY),
            evaporation_rate_um_s=dpg.get_value(tags.T_EVAP),
            solids_fraction=c0,
        )
        result = model.compute(params)
    except ValueError as e:
        dpg.set_value(tags.T_STATUS, f"\u26a0 {e}")
        dpg.bind_item_theme(tags.T_STATUS, theme.error_text_theme())
        _clear_stat_output()
        return

    dpg.set_value(tags.T_RESULT_HF_NM, f"{result.final_thickness_nm:,.1f} nm")
    dpg.set_value(tags.T_RESULT_HF_UM, f"({result.final_thickness_um:.3f} \u00b5m)")
    dpg.set_value(tags.T_RESULT_HS_UM, f"{result.transition_thickness_um:.3f} \u00b5m")
    dpg.set_value(tags.T_RESULT_OMEGA, f"{result.omega:.1f} rad/s")
    dpg.set_value(tags.T_RESULT_C0, f"{c0 * 100:.2f} %")
    dpg.set_value(tags.T_STATUS, "computed \u2713")
    dpg.bind_item_theme(tags.T_STATUS, theme.status_text_theme())

    _clear_stat_output()
    method = dpg.get_value(tags.T_STAT_METHOD)
    if method == tags.METHOD_NONE:
        return

    try:
        if method == tags.METHOD_GAUSS:
            u = _build_input_uncertainties(c0)
            a = deviation.propagate_analytic(u, result.final_thickness_nm)
            dpg.set_value(tags.T_RESULT_STAT_1, f"h_f = {a.mean_nm:.1f} \u00b1 {a.sigma_nm:.1f} nm  (1\u03c3, Gauss)")
            dpg.set_value(tags.T_RESULT_STAT_2, f"relative uncertainty: {a.relative_sigma * 100:.1f} %")
            dpg.set_value(tags.T_RESULT_STAT_3,
                          f"\u2248 95% range (\u00b12\u03c3): {a.mean_nm - 2*a.sigma_nm:.1f} \u2013 {a.mean_nm + 2*a.sigma_nm:.1f} nm")
        else:  # METHOD_MC
            kind = deviation.DistKind(dpg.get_value(tags.T_STAT_MC_DIST))
            n = int(dpg.get_value(tags.T_STAT_MC_N))
            s = _build_scatter_inputs(c0, kind)
            mc = deviation.propagate_monte_carlo(s, n)
            dpg.set_value(tags.T_RESULT_STAT_1, f"h_f = {mc.mean_nm:.1f} nm  (Monte Carlo, n = {mc.n})")
            dpg.set_value(tags.T_RESULT_STAT_2, f"standard deviation: {mc.std_nm:.1f} nm")
            dpg.set_value(tags.T_RESULT_STAT_3, f"P05 / P50 / P95: {mc.p05_nm:.1f} / {mc.p50_nm:.1f} / {mc.p95_nm:.1f} nm")
    except ValueError as e:
        dpg.set_value(tags.T_RESULT_STAT_1, f"\u26a0 {e}")


# ============================================================================
# Visibility toggles -- discrete, infrequent, so these skip the debounce
# and call recompute() directly
# ============================================================================

def on_mode_change(_sender=None, _data=None) -> None:
    direct = dpg.get_value(tags.T_MODE) == tags.MODE_DIRECT
    dpg.configure_item(tags.T_GROUP_DIRECT, show=direct)
    dpg.configure_item(tags.T_GROUP_WEIGHT, show=not direct)
    recompute()


def on_stat_method_change(_sender=None, _data=None) -> None:
    method = dpg.get_value(tags.T_STAT_METHOD)
    dpg.configure_item(tags.T_GROUP_UNCERTAINTY, show=method != tags.METHOD_NONE)
    dpg.configure_item(tags.T_GROUP_MC_OPTIONS, show=method == tags.METHOD_MC)
    recompute()


# ============================================================================
# Presets
# ============================================================================

def refresh_preset_combo(select: str | None = None) -> None:
    names = resins_store.list_presets()
    dpg.configure_item(tags.T_PRESET_COMBO, items=names)
    if select and select in names:
        dpg.set_value(tags.T_PRESET_COMBO, select)
    elif names and not dpg.get_value(tags.T_PRESET_COMBO):
        dpg.set_value(tags.T_PRESET_COMBO, names[0])


def on_load_preset(_sender=None, _data=None) -> None:
    name = dpg.get_value(tags.T_PRESET_COMBO)
    if not name:
        return
    try:
        preset = resins_store.load_preset(name)
    except ValueError as e:
        dpg.set_value(tags.T_PRESET_STATUS, f"\u26a0 {e}")
        dpg.bind_item_theme(tags.T_PRESET_STATUS, theme.error_text_theme())
        return

    dpg.set_value(tags.T_VISCOSITY, preset.viscosity_cp)
    dpg.set_value(tags.T_DENSITY, preset.density_g_cm3)
    dpg.set_value(tags.T_EVAP, preset.evaporation_rate_um_s)
    if preset.concentration_mode == "weight":
        dpg.set_value(tags.T_MODE, tags.MODE_WEIGHT)
        dpg.set_value(tags.T_WEIGHT_PCT, preset.weight_pct or parameters.WEIGHT_PCT_DEFAULT)
        dpg.set_value(tags.T_DENSITY_SOLUTE, preset.density_solute_g_cm3 or parameters.DENSITY_SOLUTE_DEFAULT)
        dpg.set_value(tags.T_DENSITY_SOLVENT, preset.density_solvent_g_cm3 or parameters.DENSITY_SOLVENT_DEFAULT)
    else:
        dpg.set_value(tags.T_MODE, tags.MODE_DIRECT)
        dpg.set_value(tags.T_C0_DIRECT, preset.solids_pct or parameters.SOLIDS_PCT_DEFAULT)
    on_mode_change()   # shows/hides the right group & recomputes

    note = f" -- {preset.notes}" if preset.notes else ""
    dpg.set_value(tags.T_PRESET_STATUS, f"'{preset.name}' loaded \u2713{note}")
    dpg.bind_item_theme(tags.T_PRESET_STATUS, theme.status_text_theme())


def on_save_preset(_sender=None, _data=None) -> None:
    name = dpg.get_value(tags.T_PRESET_NAME).strip()
    if not name:
        dpg.set_value(tags.T_PRESET_STATUS, "\u26a0 Please enter a name for the preset.")
        dpg.bind_item_theme(tags.T_PRESET_STATUS, theme.error_text_theme())
        return

    mode = "direct" if dpg.get_value(tags.T_MODE) == tags.MODE_DIRECT else "weight"
    preset = resins_store.ResinPreset(
        name=name,
        viscosity_cp=dpg.get_value(tags.T_VISCOSITY),
        density_g_cm3=dpg.get_value(tags.T_DENSITY),
        evaporation_rate_um_s=dpg.get_value(tags.T_EVAP),
        concentration_mode=mode,
        solids_pct=dpg.get_value(tags.T_C0_DIRECT) if mode == "direct" else None,
        weight_pct=dpg.get_value(tags.T_WEIGHT_PCT) if mode == "weight" else None,
        density_solute_g_cm3=dpg.get_value(tags.T_DENSITY_SOLUTE) if mode == "weight" else None,
        density_solvent_g_cm3=dpg.get_value(tags.T_DENSITY_SOLVENT) if mode == "weight" else None,
        notes=dpg.get_value(tags.T_PRESET_NOTES),
    )
    path = resins_store.save_preset(preset)
    refresh_preset_combo(select=name)
    dpg.set_value(tags.T_PRESET_STATUS, f"saved as {path.name} \u2713")
    dpg.bind_item_theme(tags.T_PRESET_STATUS, theme.status_text_theme())
