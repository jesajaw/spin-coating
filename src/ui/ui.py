"""
App- and UI-level settings that have nothing to do with the physics: window
size, Monte Carlo defaults, bounds for the uncertainty inputs, path to the
presets directory.
"""

from pathlib import Path

WINDOW_TITLE = "Spin Coating -- Meyerhofer Model"
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 900

# -- Monte Carlo --------------------------------------------------------------
MONTE_CARLO_DEFAULT_N = 2000
MONTE_CARLO_MIN_N = 100
MONTE_CARLO_MAX_N = 20000

# -- Bounds for the uncertainty inputs (+/- in lab units) --------------------
SIGMA_RPM_MAX = 2000.0
SIGMA_VISCOSITY_CP_MAX = 1000.0
SIGMA_DENSITY_MAX = 1.0
SIGMA_EVAP_UM_S_MAX = 5.0
SIGMA_SOLIDS_PP_MAX = 20.0          # percentage points, not fraction

# -- Presets (resins) ----------------------------------------------------------
RESINS_DIR = Path(__file__).resolve().parent.parent / "resins" / "presets"
