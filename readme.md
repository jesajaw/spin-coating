# 🌀 Spin Coating Approximation Tool
> ⚠️ **Status: Under Development**
---

Standalone desktop tool (Dear PyGui): predicts the final dry film
thickness in spin coating analytically, using the Meyerhofer model
(1978) -- live, with an optional statistical deviation (Gauss or Monte
Carlo), plus a simple preset library for resins.

## Start

```bash
pip install -r requirements.txt
python main.py
```

`python main.py` from the project root is the only supported way to
start this.

## Window layout

Top to bottom: **Input** -> **Statistical Deviation** (always visible,
a None / Gauss / Monte Carlo selector) -> **Result** -> **Resin
Presets** (last -- it's the section used least once a resin is dialled
in).

Computation is always live: every input recomputes the result, no
"compute" button or "auto" toggle. Continuous inputs (drag boxes,
sliders) are debounced by ~120ms (see "Live compute & debounce" below)
so dragging a slider or typing a number doesn't spam the model or let
an older, slower computation overwrite a newer result.

There's no formula explanation or citation text in the window itself --
see "Model" below instead. Keeping that out of the UI is what makes the
whole thing fit on screen without its own scrollbar.

## If the UI looks blurry on Windows

Dear PyGui, like Tk, isn't DPI-aware by default. On a scaled display
(125%/150%/200%, the default on most Windows laptops), Windows then
renders the window at a smaller internal resolution and stretches the
bitmap to fit -- that's the blur. `src/app.py` marks the process
DPI-aware (`SetProcessDpiAwareness`) before creating the viewport, which
fixes this on Windows 8.1+. If it's still blurry on your system: check
Windows' per-app "Override high DPI scaling behavior" setting
(`right-click main.py's python.exe / Properties / Compatibility /
Change high DPI settings`) isn't forcing OS scaling over the app's own
handling, and let us know your Windows/Python version if it persists --
DPI handling has enough platform-specific edge cases that another one
could exist.

## Architecture

```
main.py                         thin entry point

data/
  *.json                         bundled example presets (placeholder values)

src/
  app.py                          orchestrator -- ONLY wires things together
  store.py                        presets: simple JSON load/save
  model/
    parameters.py                  ALL physical constants, ranges, and the
                                    Input/Result data shapes -- the single
                                    place "what is a parameter" is defined
    compute.py                      the Meyerhofer formula itself, encapsulated:
                                    pure functions in, plain dataclasses out
    deviation.py                     optional statistical deviation: analytic
                                    Gaussian propagation + Monte Carlo simulation
  ui/
    tags.py                          every dpg widget tag and UI-facing string
                                     constant, in one place
    theme.py                         Dear PyGui theme (dark_purple palette)
    settings.py                      pure app/UI settings (window, Monte Carlo
                                     defaults, presets path) -- nothing physical
    callbacks.py                     the glue: reads widget values via tags.py,
                                     calls model.compute / model.deviation /
                                     store, writes results back. Also owns the
                                     live-compute debounce (see below). No
                                     computation of its own.
    layout.py                        builds the window: which widgets exist,
                                     their tags and defaults, which callback
                                     fires. No widget-value reading, no logic --
                                     every callback= points into callbacks.py.
```

### The four-way split, and why

- **`app.py` has no UI elements.** It marks the process DPI-aware,
  creates the dpg context/viewport, binds the theme, calls
  `layout.build_ui()`, runs one `callbacks.recompute()` so the result
  section isn't blank on first sight, and then drives a manual render
  loop (see "Live compute & debounce"). No `dpg.add_*()` call, no widget
  tag, and no callback body live here -- verify with `grep dpg.add_
  src/app.py` (only the docstring mentions the phrase).
- **`ui/layout.py` only calls compute -- never does it.** Every
  interactive widget's `callback=` points at a function in
  `callbacks.py`. `layout.py` itself never calls `dpg.get_value()` or
  `dpg.set_value()` -- it only *declares* widgets and *wires* them to
  callbacks, it never reads or writes widget state itself.
- **`model/parameters.py` is the single home for "what is a parameter".**
  Constants, unit conversions, valid ranges, and the `Input`/`Result`
  data shapes all live here -- nothing physical is defined a second time
  anywhere else.
- **`model/compute.py` is the compute step, encapsulated.** It takes
  plain values (an `Input`), returns a plain value (a `Result`), and
  never touches dpg, a widget tag, or global state. It can be unit-tested,
  reused in a different UI, or called from a script with zero changes.
- **`ui/tags.py` is the single source of truth for widget identity.**
  Both `layout.py` (which creates the widgets) and `callbacks.py` (which
  reads/writes them) import the same tag constants, so a rename can't
  silently drift between the two files.

### Live compute & debounce

There is no "compute" button and no "auto-compute" toggle -- every
change recomputes the result. But a drag box or slider fires its
callback on every pixel of movement (and a text field on every
keystroke), so running the model on every single one of those would
make dragging feel laggy, and could let an old, slower computation
finish after a newer one and overwrite it with a stale result.

`callbacks.mark_dirty()` / `callbacks.maybe_recompute()` fix that:
continuous widgets call `mark_dirty()`, which only records that
something changed and when; `app.py`'s manual render loop calls
`maybe_recompute()` once per frame, which runs the real `recompute()`
only once ~120ms have passed with no further change -- so a fast drag or
a burst of keystrokes becomes exactly one recompute, not dozens.
Discrete, infrequent inputs (a combo, a button) skip this and call
`recompute()` directly -- there's no burst to coalesce for a single
click. This is why `app.py` uses a manual `while
dpg.is_dearpygui_running(): ...` loop instead of the usual
`dpg.start_dearpygui()` one-liner: `maybe_recompute()` needs a place to
run once per frame.

### On `__init__.py`

Every package (`src/`, `src/model/`, `src/ui/`) has an empty
`__init__.py`. This is a convention for predictability, not a fix for
anything -- Python 3 doesn't require `__init__.py` for a folder to be
importable.

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

## Statistical deviation

Three choices in the "Statistical Deviation" section (`None` by
default), backed by `model/deviation.py`:

- **None.** Only the nominal h_f is computed. Fastest, and the default.
- **Gauss (analytic).** h_f is a pure power-law product of its inputs
  (`h_f = c0^1 * eta^(1/3) * E^(1/3) * rho^(-1/3) * omega^(-2/3)`), so
  for independent, normally distributed inputs the relative variance is
  simply the sum of the squared relative uncertainties of each input,
  weighted by its exponent. Fast, closed form, but only a first-order
  linearization.
- **Monte Carlo.** Each parameter gets its own distribution
  (Normal/Uniform/Triangular), and thousands of draws are propagated
  through the full (non-linearized) model. Additionally yields
  percentiles (P05/P50/P95) instead of just a sigma value.

Gauss and Monte Carlo were cross-validated against each other: given the
same input uncertainties, they produce practically identical relative
spread.

Important: the statistical deviation only reflects the manually entered
parameter uncertainties -- not the systematic model error of the
Meyerhofer model itself (the aforementioned +-10-20%).

## Presets

`store.py` stores material properties (viscosity, density, evaporation
rate, solids fraction) as one JSON file per preset under `data/` at the
project root. Deliberately kept simple: no schema versioning, no
database -- plain load/save is enough for a hand-maintained material
library. Spin speed is **not** part of a preset, since it's a per-run
process choice, not a material property.

The two bundled presets contain **placeholder values for orientation**,
not real datasheet values -- replace with your own measurements before
use.

## License

Not yet chosen -- add a `LICENSE` file once you've decided (MIT and
Apache-2.0 are the common permissive choices for a small tool like this;
happy to add whichever you pick).

## If this logic is later folded into your own tool suite

`model/compute.py` and `model/deviation.py` are deliberately kept free of
UI dependencies, so `compute()` and `propagate_*()` can be dropped
directly into a `ComputeToolWindow` (tkinter, see your existing
`widgets.py`) or any other frontend.
