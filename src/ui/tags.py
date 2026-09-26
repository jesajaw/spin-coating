"""
All dpg widget tags and the string constants tied to them (dropdown option
labels, etc.), collected in one place.

Pulled out of app.py/layout.py on purpose: layout.py needs these to build
widgets, callbacks.py needs the same names to read/write those widgets --
keeping them in a third file means both import the same source of truth
instead of one silently drifting from the other after a rename.
"""

# -- Input ----------------------------------------------------------------------
T_RPM = "in_rpm"
T_VISCOSITY = "in_viscosity_cp"
T_DENSITY = "in_density"
T_EVAP = "in_evap_rate"
T_MODE = "in_conc_mode"
T_C0_DIRECT = "in_c0_direct"
T_WEIGHT_PCT = "in_weight_pct"
T_DENSITY_SOLUTE = "in_density_solute"
T_DENSITY_SOLVENT = "in_density_solvent"

T_GROUP_DIRECT = "grp_c0_direct"
T_GROUP_WEIGHT = "grp_c0_weight"

MODE_DIRECT = "Volume fraction directly"
MODE_WEIGHT = "From weight fraction + densities"

# -- Statistical deviation --------------------------------------------------------
# One selector, always visible ("always open") -- no separate enable
# checkbox anymore. NONE skips deviation entirely, GAUSS and MC each show
# their own extra widgets below the selector.
T_STAT_METHOD = "in_stat_method"
T_STAT_MC_DIST = "in_stat_mc_dist"
T_STAT_MC_N = "in_stat_mc_n"
T_SIGMA_RPM = "in_sigma_rpm"
T_SIGMA_VISCOSITY = "in_sigma_viscosity"
T_SIGMA_DENSITY = "in_sigma_density"
T_SIGMA_EVAP = "in_sigma_evap"
T_SIGMA_C0 = "in_sigma_c0"

T_GROUP_UNCERTAINTY = "grp_uncertainty"    # shown whenever method != NONE
T_GROUP_MC_OPTIONS = "grp_mc_options"      # shown only when method == MC

METHOD_NONE = "None"
METHOD_GAUSS = "Gauss (analytic)"
METHOD_MC = "Monte Carlo"

# -- Result -----------------------------------------------------------------------
T_RESULT_HF_NM = "out_hf_nm"
T_RESULT_HF_UM = "out_hf_um"
T_RESULT_HS_UM = "out_hs_um"
T_RESULT_OMEGA = "out_omega"
T_RESULT_C0 = "out_c0_used"
T_STATUS = "out_status"
T_RESULT_STAT_1 = "out_stat_1"
T_RESULT_STAT_2 = "out_stat_2"
T_RESULT_STAT_3 = "out_stat_3"

# -- Presets (section moved to the end of the window, tags grouped here to match) --
T_PRESET_COMBO = "in_preset_select"
T_PRESET_NAME = "in_preset_name"
T_PRESET_NOTES = "in_preset_notes"
T_PRESET_STATUS = "out_preset_status"
