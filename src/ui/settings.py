"""
App- and UI-level settings that have nothing to do with the physics: window
size, Monte Carlo defaults, bounds for the uncertainty inputs, path to the
presets directory.

Named settings.py (not ui.py) deliberately -- a file called ui.py inside a
folder called ui/ made `from .ui import ui` read strangely and invited the
kind of import mistakes that broke this project after the last reshuffle.
"""

from pathlib import Path

WINDOW_TITLE = "Spin Coating -- Meyerhofer Model"
# Two columns side by side (Input|Presets on top, Deviation|Result below),
# so the viewport needs to be wide enough for both columns plus the gap
# between them and the window's own padding.
WINDOW_WIDTH = 1100
# Each row's height only needs to fit the taller of its two cells (Input
# is the tall one in row 1, Deviation and Result are roughly equal in row
# 2) rather than all four sections stacked, so this is noticeably smaller
# than the single-column layout needed. Left a bit of slack below as a
# fallback in case a field wraps differently than expected -- see
# ui/layout.py's module docstring for why the outer window stays
# scrollable rather than being forced to fit exactly.
WINDOW_HEIGHT = 900

# Width of one grid cell (child window). Two of these plus the gap between
# them and outer window padding need to fit inside WINDOW_WIDTH.
COLUMN_WIDTH = 500
# Fixed pixel width for the actual input/output widgets inside a column,
# narrower than COLUMN_WIDTH so there's room left for the widget's label
# (dearpygui draws a widget's label immediately to its right, not wrapped).
CONTENT_WIDTH = 300

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

# -- Presets --------------------------------------------------------------------
# src/ui/settings.py -> parent = src/ui, .parent.parent = src/, .parent.parent.parent
# is the project root, where data/ actually lives (sibling of src/, not inside it).
PRESETS_DIR = Path(__file__).resolve().parent.parent.parent / "data"
