"""
App-level settings that have nothing to do with the physics: defaults for the
Monte Carlo run, the plot range and the location of the preset files.
(Parameter defaults live in src/model/parameters.py.)
"""

from pathlib import Path

APP_TITLE = "Spin Coating Thickness Calculator"

# -- Monte Carlo --------------------------------------------------------------
MONTE_CARLO_DEFAULT_N = 2000
MONTE_CARLO_MIN_N = 100
MONTE_CARLO_MAX_N = 20000
MONTE_CARLO_SEED = 12345        # fixed seed: unrelated re-computes must not make the numbers "jitter"
BAND_SAMPLES = 500              # samples per plot point for the live Monte Carlo band

# Models that need a numerical ODE solve per evaluation (ModelInfo.fast == False): Monte Carlo is run on
# demand, and bands are evaluated on a few spin speeds and interpolated.
SLOW_MC_DEFAULT_N = 300
SLOW_MC_MAX_N = 3000
SLOW_BAND_POINTS = 12
SLOW_BAND_SAMPLES = 120

# -- Plot -----------------------------------------------------------------------
PLOT_POINTS = 60
PLOT_RPM_DEFAULT_MIN = 500.0
PLOT_RPM_DEFAULT_MAX = 8000.0

# -- Presets --------------------------------------------------------------------
# src/settings.py -> parent = src/, .parent.parent = project root, where data/ lives
PRESETS_DIR = Path(__file__).resolve().parent.parent / "data"
