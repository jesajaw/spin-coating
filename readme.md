# 🌀 Spin Coating Approximation Tool
> ⚠️ **Status: Under Development**  
---

Standalone desktop tool (Dear PyGui): predicts the final dry film
thickness in spin coating analytically, using the Meyerhofer model
(1978) -- optionally with statistical deviation, plus a simple preset
library for resins.

## Start

```bash
pip install -r requirements.txt
python main.py
```

## Architecture

```
main.py                     thin entry point

src/
  config/
    physics.py               constants, unit conversion factors, physical default/range values
    ui.py                     pure app/UI settings (window, Monte Carlo defaults, presets path)
  calc/
    meyerhofer.py             the actual model -- pure physics, no UI import
  stat/
    deviation.py              optional statistical deviation: analytic
                               Gaussian propagation + Monte Carlo simulation
  ui/
    theme.py                  Dear PyGui theme (same dark_purple palette as style.py)
    app.py                    main window: presets, input, statistics, result
  resins/
    store.py                  presets (resins) as simple JSON files: load/save
    presets/*.json             bundled example presets (placeholder values)
```

The separation is deliberate: `calc/` and `stat/` know nothing about
`dearpygui` and are independently testable; `config/` is the single place
for constants and value ranges so nothing is maintained twice; `ui/` and
`resins/` depend on `config`/`calc`/`stat`, but not the other way around.

## Model

```
h_f = c0 * (3 * eta * E / (2 * rho * omega^2)) ^ (1/3)
```

- `c0`     -- initial solute volume fraction of the solution (0..1)
- `eta`    -- dynamic viscosity of the solution [Pa*s]
- `E`      -- solvent evaporation rate [m/s] (volume/area/time)
- `rho`    -- density of the solution [kg/m^3]
- `omega`  -- angular velocity [rad/s]

Derivation: viscous thinning per Emslie/Bonner/Peck plus a constant
evaporation rate; the transition from flow-dominated to
evaporation-dominated thinning is assumed to be abrupt, at the point
where both rates are equal. References: D. Meyerhofer, *J. Appl. Phys.*
49, 3993 (1978); A. G. Emslie, F. T. Bonner, L. G. Peck, *J. Appl. Phys.*
29, 858 (1958).

**Assumptions/limits:** Newtonian fluid, spatially constant evaporation
rate, single-stage abrupt transition, no acceleration phase. Real values
can deviate by roughly +-10-20% -- `E` is usually the most uncertain
parameter and should be calibrated against your own measurements
(ellipsometry/profilometry).

## Statistical deviation (optional)

Two independently selectable methods in `stat/deviation.py`:

1. **Analytic Gaussian error propagation.** h_f is a pure power-law
   product of its inputs (`h_f = c0^1 * eta^(1/3) * E^(1/3) *
   rho^(-1/3) * omega^(-2/3)`), so for independent, normally distributed
   inputs the relative variance is simply the sum of the squared relative
   uncertainties of each input, weighted by its exponent. Fast, closed
   form, but only a first-order linearization.
2. **Monte Carlo simulation.** Each parameter gets its own distribution
   (Normal/Uniform/Triangular), and thousands of draws are propagated
   through the full (non-linearized) model. Additionally yields
   percentiles (P05/P50/P95) instead of just a sigma value.

Both methods were cross-validated: given the same input uncertainties,
they produce practically identical relative spread.

Important: the statistical deviation only reflects the manually entered
parameter uncertainties -- not the systematic model error of the
Meyerhofer model itself (the aforementioned +-10-20%).

## Presets (resins)

`resins/store.py` stores material properties (viscosity, density,
evaporation rate, solids fraction) as one JSON file per preset under
`src/resins/presets/`. Deliberately kept simple: no schema versioning, no
database -- plain load/save is enough for a hand-maintained material
library. Spin speed is **not** part of a preset, since it's a per-run
process choice, not a material property.

The two bundled presets contain **placeholder values for orientation**,
not real datasheet values -- replace with your own measurements before
use.

## If this logic is later folded into your own tool suite

`calc/meyerhofer.py` and `stat/deviation.py` are deliberately kept free
of UI dependencies, so `compute()` and `propagate_*()` can be dropped
directly into a `ComputeToolWindow` (tkinter, see your existing
`widgets.py`) or any other frontend.
