"""
Main application window. Four sections, top to bottom:

  1. Presets (Resins) -- load/save material properties as a simple JSON
     file (see resins.store).
  2. Input -- the physical parameters of the Meyerhofer model.
  3. Statistical deviation (optional) -- analytic Gaussian error
     propagation or Monte Carlo simulation over the entered uncertainties
     (see stat.deviation).
  4. Result -- nominal value h_f, plus the statistical evaluation if
     section 3 is enabled.

No store/load/save logic for "a dataset" like the rest of the toolset is
needed here -- this is about single numbers, not measurement series.
Presets are the only persistence here and serve a different purpose (a
material library, not work results).
"""

import dearpygui.dearpygui as dpg

from src.model import meyerhofer as model, deviation as stat, physics as cfg_phys

from presets import store as resins_store
from src.ui import ui as cfg_ui, theme

# -- Tags: input --------------------------------------------------------------
T_RPM = "in_rpm"
T_VISCOSITY = "in_viscosity_cp"
T_DENSITY = "in_density"
T_EVAP = "in_evap_rate"
T_MODE = "in_conc_mode"
T_C0_DIRECT = "in_c0_direct"
T_WEIGHT_PCT = "in_weight_pct"
T_DENSITY_SOLUTE = "in_density_solute"
T_DENSITY_SOLVENT = "in_density_solvent"
T_AUTO = "in_auto_calc"

T_GROUP_DIRECT = "grp_c0_direct"
T_GROUP_WEIGHT = "grp_c0_weight"

MODE_DIRECT = "Volume fraction directly"
MODE_WEIGHT = "From weight fraction + densities"

# -- Tags: presets --------------------------------------------------------------
T_PRESET_COMBO = "in_preset_select"
T_PRESET_NAME = "in_preset_name"
T_PRESET_NOTES = "in_preset_notes"
T_PRESET_STATUS = "out_preset_status"

# -- Tags: statistics -----------------------------------------------------------
T_STAT_ENABLE = "in_stat_enable"
T_STAT_METHOD = "in_stat_method"
T_STAT_MC_DIST = "in_stat_mc_dist"
T_STAT_MC_N = "in_stat_mc_n"
T_SIGMA_RPM = "in_sigma_rpm"
T_SIGMA_VISCOSITY = "in_sigma_viscosity"
T_SIGMA_DENSITY = "in_sigma_density"
T_SIGMA_EVAP = "in_sigma_evap"
T_SIGMA_C0 = "in_sigma_c0"

T_GROUP_STAT_BODY = "grp_stat_body"
T_GROUP_MC_OPTIONS = "grp_mc_options"

METHOD_ANALYTIC = "Analytic Gaussian propagation"
METHOD_MC = "Monte Carlo simulation"

# -- Tags: result ---------------------------------------------------------------
T_RESULT_HF_NM = "out_hf_nm"
T_RESULT_HF_UM = "out_hf_um"
T_RESULT_HS_UM = "out_hs_um"
T_RESULT_OMEGA = "out_omega"
T_RESULT_C0 = "out_c0_used"
T_STATUS = "out_status"
T_RESULT_STAT_1 = "out_stat_1"
T_RESULT_STAT_2 = "out_stat_2"
T_RESULT_STAT_3 = "out_stat_3"


# ============================================================================
# Computation
# ============================================================================

def _resolve_solids_fraction() -> float:
    if dpg.get_value(T_MODE) == MODE_DIRECT:
        return dpg.get_value(T_C0_DIRECT) / 100.0
    w = dpg.get_value(T_WEIGHT_PCT) / 100.0
    return model.volume_fraction_from_weight_fraction(
        w, dpg.get_value(T_DENSITY_SOLUTE), dpg.get_value(T_DENSITY_SOLVENT)
    )


def _build_input_uncertainties(c0: float) -> stat.InputUncertainties:
    return stat.InputUncertainties(
        rpm=stat.ParamUncertainty(dpg.get_value(T_RPM), dpg.get_value(T_SIGMA_RPM)),
        viscosity_cp=stat.ParamUncertainty(dpg.get_value(T_VISCOSITY), dpg.get_value(T_SIGMA_VISCOSITY)),
        density_g_cm3=stat.ParamUncertainty(dpg.get_value(T_DENSITY), dpg.get_value(T_SIGMA_DENSITY)),
        evaporation_rate_um_s=stat.ParamUncertainty(dpg.get_value(T_EVAP), dpg.get_value(T_SIGMA_EVAP)),
        solids_fraction=stat.ParamUncertainty(c0, dpg.get_value(T_SIGMA_C0) / 100.0),
    )


def _build_scatter_inputs(c0: float, kind: stat.DistKind) -> stat.ScatterInputs:
    return stat.ScatterInputs(
        rpm=stat.ScatterParam(dpg.get_value(T_RPM), kind, dpg.get_value(T_SIGMA_RPM)),
        viscosity_cp=stat.ScatterParam(dpg.get_value(T_VISCOSITY), kind, dpg.get_value(T_SIGMA_VISCOSITY)),
        density_g_cm3=stat.ScatterParam(dpg.get_value(T_DENSITY), kind, dpg.get_value(T_SIGMA_DENSITY)),
        evaporation_rate_um_s=stat.ScatterParam(dpg.get_value(T_EVAP), kind, dpg.get_value(T_SIGMA_EVAP)),
        solids_fraction=stat.ScatterParam(c0, kind, dpg.get_value(T_SIGMA_C0) / 100.0),
    )


def _clear_stat_output() -> None:
    dpg.set_value(T_RESULT_STAT_1, "")
    dpg.set_value(T_RESULT_STAT_2, "")
    dpg.set_value(T_RESULT_STAT_3, "")


def recompute(sender=None, _data=None) -> None:
    if not dpg.get_value(T_AUTO) and sender not in (None, "btn_compute"):
        return
    try:
        c0 = _resolve_solids_fraction()
        params = model.from_lab_units(
            spin_speed_rpm=dpg.get_value(T_RPM),
            viscosity_cp=dpg.get_value(T_VISCOSITY),
            density_g_cm3=dpg.get_value(T_DENSITY),
            evaporation_rate_um_s=dpg.get_value(T_EVAP),
            solids_fraction=c0,
        )
        result = model.compute(params)
    except ValueError as e:
        dpg.set_value(T_STATUS, f"\u26a0 {e}")
        dpg.bind_item_theme(T_STATUS, theme.error_text_theme())
        _clear_stat_output()
        return

    dpg.set_value(T_RESULT_HF_NM, f"{result.final_thickness_nm:,.1f} nm")
    dpg.set_value(T_RESULT_HF_UM, f"({result.final_thickness_um:.3f} \u00b5m)")
    dpg.set_value(T_RESULT_HS_UM, f"{result.transition_thickness_um:.3f} \u00b5m")
    dpg.set_value(T_RESULT_OMEGA, f"{result.omega:.1f} rad/s")
    dpg.set_value(T_RESULT_C0, f"{c0 * 100:.2f} %")
    dpg.set_value(T_STATUS, "computed \u2713")
    dpg.bind_item_theme(T_STATUS, theme.status_text_theme())

    _clear_stat_output()
    if not dpg.get_value(T_STAT_ENABLE):
        return

    try:
        if dpg.get_value(T_STAT_METHOD) == METHOD_ANALYTIC:
            u = _build_input_uncertainties(c0)
            a = stat.propagate_analytic(u, result.final_thickness_nm)
            dpg.set_value(T_RESULT_STAT_1, f"h_f = {a.mean_nm:.1f} \u00b1 {a.sigma_nm:.1f} nm  (1\u03c3, analytic)")
            dpg.set_value(T_RESULT_STAT_2, f"relative uncertainty: {a.relative_sigma * 100:.1f} %")
            dpg.set_value(T_RESULT_STAT_3,
                          f"\u2248 95% range (\u00b12\u03c3): {a.mean_nm - 2*a.sigma_nm:.1f} \u2013 {a.mean_nm + 2*a.sigma_nm:.1f} nm")
        else:
            kind = stat.DistKind(dpg.get_value(T_STAT_MC_DIST))
            n = int(dpg.get_value(T_STAT_MC_N))
            s = _build_scatter_inputs(c0, kind)
            mc = stat.propagate_monte_carlo(s, n)
            dpg.set_value(T_RESULT_STAT_1, f"h_f = {mc.mean_nm:.1f} nm  (Monte Carlo, n = {mc.n})")
            dpg.set_value(T_RESULT_STAT_2, f"standard deviation: {mc.std_nm:.1f} nm")
            dpg.set_value(T_RESULT_STAT_3, f"P05 / P50 / P95: {mc.p05_nm:.1f} / {mc.p50_nm:.1f} / {mc.p95_nm:.1f} nm")
    except ValueError as e:
        dpg.set_value(T_RESULT_STAT_1, f"\u26a0 {e}")


def _on_mode_change(_sender=None, _data=None) -> None:
    direct = dpg.get_value(T_MODE) == MODE_DIRECT
    dpg.configure_item(T_GROUP_DIRECT, show=direct)
    dpg.configure_item(T_GROUP_WEIGHT, show=not direct)
    recompute(T_MODE)


def _on_stat_enable_change(_sender=None, _data=None) -> None:
    dpg.configure_item(T_GROUP_STAT_BODY, show=dpg.get_value(T_STAT_ENABLE))
    recompute(T_STAT_ENABLE)


def _on_stat_method_change(_sender=None, _data=None) -> None:
    dpg.configure_item(T_GROUP_MC_OPTIONS, show=dpg.get_value(T_STAT_METHOD) == METHOD_MC)
    recompute(T_STAT_METHOD)


# ============================================================================
# Presets
# ============================================================================

def _refresh_preset_combo(select: str | None = None) -> None:
    names = resins_store.list_presets()
    dpg.configure_item(T_PRESET_COMBO, items=names)
    if select and select in names:
        dpg.set_value(T_PRESET_COMBO, select)
    elif names and not dpg.get_value(T_PRESET_COMBO):
        dpg.set_value(T_PRESET_COMBO, names[0])


def _on_load_preset(_sender=None, _data=None) -> None:
    name = dpg.get_value(T_PRESET_COMBO)
    if not name:
        return
    try:
        preset = resins_store.load_preset(name)
    except ValueError as e:
        dpg.set_value(T_PRESET_STATUS, f"\u26a0 {e}")
        dpg.bind_item_theme(T_PRESET_STATUS, theme.error_text_theme())
        return

    dpg.set_value(T_VISCOSITY, preset.viscosity_cp)
    dpg.set_value(T_DENSITY, preset.density_g_cm3)
    dpg.set_value(T_EVAP, preset.evaporation_rate_um_s)
    if preset.concentration_mode == "weight":
        dpg.set_value(T_MODE, MODE_WEIGHT)
        dpg.set_value(T_WEIGHT_PCT, preset.weight_pct or cfg_phys.WEIGHT_PCT_DEFAULT)
        dpg.set_value(T_DENSITY_SOLUTE, preset.density_solute_g_cm3 or cfg_phys.DENSITY_SOLUTE_DEFAULT)
        dpg.set_value(T_DENSITY_SOLVENT, preset.density_solvent_g_cm3 or cfg_phys.DENSITY_SOLVENT_DEFAULT)
    else:
        dpg.set_value(T_MODE, MODE_DIRECT)
        dpg.set_value(T_C0_DIRECT, preset.solids_pct or cfg_phys.SOLIDS_PCT_DEFAULT)
    _on_mode_change()   # shows/hides the right group & recomputes

    note = f" -- {preset.notes}" if preset.notes else ""
    dpg.set_value(T_PRESET_STATUS, f"'{preset.name}' loaded \u2713{note}")
    dpg.bind_item_theme(T_PRESET_STATUS, theme.status_text_theme())


def _on_save_preset(_sender=None, _data=None) -> None:
    name = dpg.get_value(T_PRESET_NAME).strip()
    if not name:
        dpg.set_value(T_PRESET_STATUS, "\u26a0 Please enter a name for the preset.")
        dpg.bind_item_theme(T_PRESET_STATUS, theme.error_text_theme())
        return

    mode = "direct" if dpg.get_value(T_MODE) == MODE_DIRECT else "weight"
    preset = resins_store.ResinPreset(
        name=name,
        viscosity_cp=dpg.get_value(T_VISCOSITY),
        density_g_cm3=dpg.get_value(T_DENSITY),
        evaporation_rate_um_s=dpg.get_value(T_EVAP),
        concentration_mode=mode,
        solids_pct=dpg.get_value(T_C0_DIRECT) if mode == "direct" else None,
        weight_pct=dpg.get_value(T_WEIGHT_PCT) if mode == "weight" else None,
        density_solute_g_cm3=dpg.get_value(T_DENSITY_SOLUTE) if mode == "weight" else None,
        density_solvent_g_cm3=dpg.get_value(T_DENSITY_SOLVENT) if mode == "weight" else None,
        notes=dpg.get_value(T_PRESET_NOTES),
    )
    path = resins_store.save_preset(preset)
    _refresh_preset_combo(select=name)
    dpg.set_value(T_PRESET_STATUS, f"saved as {path.name} \u2713")
    dpg.bind_item_theme(T_PRESET_STATUS, theme.status_text_theme())


# ============================================================================
# UI layout
# ============================================================================

def _section_title(text: str) -> None:
    dpg.add_text(text)
    dpg.bind_item_theme(dpg.last_item(), theme.title_text_theme())
    dpg.add_separator()


def build_ui() -> None:
    with dpg.window(tag="main_window"):
        dpg.add_text("Meyerhofer Model: Spin Coating Final Film Thickness", tag="title")
        dpg.bind_item_theme("title", theme.title_text_theme())

        instructions = (
            "h_f = c0 * (3*eta*E / (2*rho*omega^2))^(1/3)  --  combination of viscous "
            "thinning (Emslie/Bonner/Peck) and a constant evaporation rate E, with an "
            "abrupt transition at h_s. Valid for Newtonian fluids, a constant "
            "evaporation rate, and a single-stage transition from flow to evaporation."
        )
        dpg.add_text(instructions, wrap=700, tag="instructions")
        dpg.bind_item_theme("instructions", theme.status_text_theme())
        dpg.add_spacer(height=8)

        # -- 1. Presets ---------------------------------------------------------
        with dpg.child_window(height=170, border=True):
            _section_title("Presets (Resins)")
            with dpg.group(horizontal=True):
                dpg.add_combo(tag=T_PRESET_COMBO, items=resins_store.list_presets(), width=380)
                dpg.add_button(label="Load", callback=_on_load_preset)
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag=T_PRESET_NAME, hint="Name for new preset", width=300)
                dpg.add_button(label="Save as preset", callback=_on_save_preset)
            dpg.add_input_text(tag=T_PRESET_NOTES, hint="Note (optional, e.g. source/calibration date)", width=-1)
            dpg.add_text("", tag=T_PRESET_STATUS)
            dpg.bind_item_theme(T_PRESET_STATUS, theme.status_text_theme())
            with dpg.tooltip(T_PRESET_COMBO):
                dpg.add_text(
                    "Presets store material properties (viscosity, density,\n"
                    "evaporation rate, solids fraction) -- not the spin speed, since\n"
                    "that is a per-run process choice, not a material property.",
                    wrap=340,
                )

        dpg.add_spacer(height=10)

        # -- 2. Input -------------------------------------------------------------
        with dpg.child_window(height=330, border=True):
            _section_title("Input")

            dpg.add_drag_float(label="Spin speed [rpm]", tag=T_RPM, default_value=cfg_phys.RPM_DEFAULT,
                                min_value=cfg_phys.RPM_MIN, max_value=cfg_phys.RPM_MAX, speed=10.0,
                                callback=recompute)
            dpg.add_drag_float(label="Viscosity [cP = mPa*s]", tag=T_VISCOSITY,
                                default_value=cfg_phys.VISCOSITY_CP_DEFAULT,
                                min_value=cfg_phys.VISCOSITY_CP_MIN, max_value=cfg_phys.VISCOSITY_CP_MAX,
                                speed=0.5, callback=recompute)
            dpg.add_drag_float(label="Solution density [g/cm3]", tag=T_DENSITY,
                                default_value=cfg_phys.DENSITY_DEFAULT,
                                min_value=cfg_phys.DENSITY_MIN, max_value=cfg_phys.DENSITY_MAX,
                                speed=0.01, callback=recompute)
            dpg.add_drag_float(label="Evaporation rate E [\u00b5m/s]", tag=T_EVAP,
                                default_value=cfg_phys.EVAP_UM_S_DEFAULT,
                                min_value=cfg_phys.EVAP_UM_S_MIN, max_value=cfg_phys.EVAP_UM_S_MAX,
                                speed=0.01, format="%.3f", callback=recompute)
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text(
                    "Volume flux of evaporating solvent per unit area.\n"
                    "Typical order of magnitude: 0.01-1 \u00b5m/s. Best calibrated\n"
                    "against reference measurements for the specific solvent.",
                    wrap=320,
                )

            dpg.add_spacer(height=6)
            dpg.add_combo(label="Solids fraction from", tag=T_MODE,
                          items=[MODE_DIRECT, MODE_WEIGHT], default_value=MODE_DIRECT,
                          callback=_on_mode_change)

            with dpg.group(tag=T_GROUP_DIRECT):
                dpg.add_slider_float(label="Solids volume fraction c0 [%]", tag=T_C0_DIRECT,
                                      default_value=cfg_phys.SOLIDS_PCT_DEFAULT,
                                      min_value=cfg_phys.SOLIDS_PCT_MIN, max_value=cfg_phys.SOLIDS_PCT_MAX,
                                      callback=recompute)

            with dpg.group(tag=T_GROUP_WEIGHT, show=False):
                dpg.add_slider_float(label="Solids weight fraction w [%]", tag=T_WEIGHT_PCT,
                                      default_value=cfg_phys.WEIGHT_PCT_DEFAULT,
                                      min_value=cfg_phys.SOLIDS_PCT_MIN, max_value=cfg_phys.SOLIDS_PCT_MAX,
                                      callback=recompute)
                dpg.add_drag_float(label="Solute density (pure) [g/cm3]", tag=T_DENSITY_SOLUTE,
                                    default_value=cfg_phys.DENSITY_SOLUTE_DEFAULT,
                                    min_value=0.1, max_value=10.0, speed=0.01, callback=recompute)
                dpg.add_drag_float(label="Solvent density (pure) [g/cm3]", tag=T_DENSITY_SOLVENT,
                                    default_value=cfg_phys.DENSITY_SOLVENT_DEFAULT,
                                    min_value=0.1, max_value=3.0, speed=0.01, callback=recompute)

            dpg.add_spacer(height=6)
            with dpg.group(horizontal=True):
                dpg.add_checkbox(label="Compute automatically", tag=T_AUTO, default_value=True)
                dpg.add_button(label="Compute", tag="btn_compute", callback=recompute)

        dpg.add_spacer(height=10)

        # -- 3. Statistical deviation --------------------------------------------
        with dpg.child_window(height=290, border=True):
            _section_title("Statistical Deviation (optional)")
            dpg.add_checkbox(label="Include statistical deviation", tag=T_STAT_ENABLE,
                              default_value=False, callback=_on_stat_enable_change)

            with dpg.group(tag=T_GROUP_STAT_BODY, show=False):
                dpg.add_combo(label="Method", tag=T_STAT_METHOD,
                              items=[METHOD_ANALYTIC, METHOD_MC], default_value=METHOD_ANALYTIC,
                              callback=_on_stat_method_change)

                with dpg.group(tag=T_GROUP_MC_OPTIONS, show=False):
                    dpg.add_combo(label="Distribution shape (Monte Carlo)", tag=T_STAT_MC_DIST,
                                  items=[d.value for d in stat.DistKind],
                                  default_value=stat.DistKind.GAUSS.value, callback=recompute)
                    dpg.add_drag_int(label="Number of samples", tag=T_STAT_MC_N,
                                      default_value=cfg_ui.MONTE_CARLO_DEFAULT_N,
                                      min_value=cfg_ui.MONTE_CARLO_MIN_N, max_value=cfg_ui.MONTE_CARLO_MAX_N,
                                      callback=recompute)

                dpg.add_spacer(height=4)
                dpg.add_text("Uncertainties (\u00b1, 0 = no spread for this parameter):")
                dpg.bind_item_theme(dpg.last_item(), theme.status_text_theme())

                dpg.add_drag_float(label="\u00b1 Spin speed [rpm]", tag=T_SIGMA_RPM, default_value=0.0,
                                    min_value=0.0, max_value=cfg_ui.SIGMA_RPM_MAX, callback=recompute)
                dpg.add_drag_float(label="\u00b1 Viscosity [cP]", tag=T_SIGMA_VISCOSITY, default_value=0.0,
                                    min_value=0.0, max_value=cfg_ui.SIGMA_VISCOSITY_CP_MAX, callback=recompute)
                dpg.add_drag_float(label="\u00b1 Density [g/cm3]", tag=T_SIGMA_DENSITY, default_value=0.0,
                                    min_value=0.0, max_value=cfg_ui.SIGMA_DENSITY_MAX, speed=0.005,
                                    callback=recompute)
                dpg.add_drag_float(label="\u00b1 Evaporation rate [\u00b5m/s]", tag=T_SIGMA_EVAP,
                                    default_value=0.0, min_value=0.0, max_value=cfg_ui.SIGMA_EVAP_UM_S_MAX,
                                    speed=0.005, format="%.4f", callback=recompute)
                dpg.add_drag_float(label="\u00b1 Solids fraction [percentage points]", tag=T_SIGMA_C0,
                                    default_value=0.0, min_value=0.0, max_value=cfg_ui.SIGMA_SOLIDS_PP_MAX,
                                    callback=recompute)
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text(
                        "Always interpreted as 1-sigma for the analytic method.\n"
                        "For Monte Carlo, interpreted according to the chosen\n"
                        "distribution shape: sigma (Normal) or half-width (Uniform/Triangular).",
                        wrap=340,
                    )

        dpg.add_spacer(height=10)

        # -- 4. Result --------------------------------------------------------------
        with dpg.child_window(height=230, border=True):
            _section_title("Result")

            dpg.add_text("-- nm", tag=T_RESULT_HF_NM)
            dpg.bind_item_theme(T_RESULT_HF_NM, theme.result_text_theme())
            dpg.add_text("", tag=T_RESULT_HF_UM)
            dpg.bind_item_theme(T_RESULT_HF_UM, theme.status_text_theme())

            dpg.add_spacer(height=4)
            with dpg.group(horizontal=True):
                dpg.add_text("Wet transition thickness h_s:")
                dpg.add_text("--", tag=T_RESULT_HS_UM)
            with dpg.group(horizontal=True):
                dpg.add_text("Omega used:")
                dpg.add_text("--", tag=T_RESULT_OMEGA)
            with dpg.group(horizontal=True):
                dpg.add_text("Volume fraction c0 used:")
                dpg.add_text("--", tag=T_RESULT_C0)

            dpg.add_spacer(height=6)
            dpg.add_separator()
            dpg.add_text("", tag=T_RESULT_STAT_1)
            dpg.bind_item_theme(T_RESULT_STAT_1, theme.result_text_theme())
            dpg.add_text("", tag=T_RESULT_STAT_2)
            dpg.bind_item_theme(T_RESULT_STAT_2, theme.status_text_theme())
            dpg.add_text("", tag=T_RESULT_STAT_3)
            dpg.bind_item_theme(T_RESULT_STAT_3, theme.status_text_theme())

            dpg.add_spacer(height=6)
            dpg.add_text("", tag=T_STATUS)
            dpg.bind_item_theme(T_STATUS, theme.status_text_theme())

        dpg.add_spacer(height=8)
        dpg.add_text(
            "D. Meyerhofer, J. Appl. Phys. 49, 3993 (1978)  --  "
            "A. G. Emslie, F. T. Bonner, L. G. Peck, J. Appl. Phys. 29, 858 (1958).\n"
            "Semi-empirical model, real values can deviate by ~10-20% -- calibrate "
            "against your own measurements (ellipsometry/profilometry). The "
            "statistical deviation only reflects the entered parameter "
            "uncertainties, not the systematic model error of the Meyerhofer model itself.",
            wrap=700,
        )
        dpg.bind_item_theme(dpg.last_item(), theme.status_text_theme())


def main() -> None:
    dpg.create_context()
    dpg.create_viewport(title=cfg_ui.WINDOW_TITLE, width=cfg_ui.WINDOW_WIDTH, height=cfg_ui.WINDOW_HEIGHT)
    dpg.setup_dearpygui()

    dpg.bind_theme(theme.build_global_theme())
    build_ui()
    recompute()

    dpg.set_primary_window("main_window", True)
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()
