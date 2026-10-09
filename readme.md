# 🌀 Spin Coating Approximation Tool
> ⚠️ **Status: Under Development**

Predicts the **final dry film thickness** of a spin-coated layer and how it changes with spin speed.
Three models of increasing realism, live plot, statistical deviation (Gauss and Monte Carlo) and saveable
parameter presets. It tries to turn the theoretical thin-film PDE into a tool that is usable in the lab.

Available as a **desktop app** (Python / tkinter) and as a **single-file web version** (`index.html`).
Both use the same models and give the same numbers.

---

## 🧭 At a glance

| Model | Computes | Evaporation | Viscosity | Typical use |
|---|---|---|---|---|
| **Emslie-Bonner-Peck** (1958) | wet film thickness $h(t)$ after a spin time | none | constant | understanding the flow-driven thinning |
| **Meyerhofer** (1978) | final dry film thickness $h_\mathrm{f}$ (closed form) | constant rate $E$ | constant | quick estimate, first guess |
| **Flack et al.** (1984), *depth-averaged* | final dry film thickness $h_\mathrm{f}$ (numerical ODE) | slows down as the film concentrates | rises with solids content | resins whose viscosity changes a lot while drying |

**Rule of thumb:** start with Meyerhofer. Switch to Flack if the result is clearly off and you can calibrate
$k_\eta$ and $n$ against your own measurements.

---

## 🚀 Quick start

### Desktop

```bash
pip install -r requirements.txt     # matplotlib
python main.py
```

* Python 3.9+ (tested with 3.12). tkinter ships with Python on Windows/macOS; on Linux install it first
  (e.g. `sudo apt install python3-tk`).
* Pick a colour theme without editing code: `SPIN_COATING_THEME=dark_blue python main.py`
  (`dark_purple`, `dark_blue`, `black_white`).
* Presets are read from / written to `data/*.json`.

### Web

Open `index.html` in a browser, no build step and no server needed (it is also served by GitHub Pages).
Presets you save there live in your browser (`localStorage`); the two example presets are built in.

---

## ✨ Features

* **Live results**: every field recomputes result and plot (debounced, dragging a value does not spam the model).
* **Thickness-rpm plot**: $h(\omega)$ over a chosen range, current operating point marked.
* **Two ways to enter the solids fraction**: directly as volume fraction, or from weight fraction plus the two pure-component densities.
* **Evaporation vs. spin speed**: $E$ grows with $\sqrt{\omega}$ (Meyerhofer's observation) or stays constant.
* **Statistical deviation** on result and plot:
  * *Gauss (analytic)*: linearised error propagation, instant, first order only.
  * *Monte Carlo*: samples every uncertain parameter (normal, uniform or triangular) and propagates it through the full, non-linear model; reports P05 / P50 / P95. See the caveat in `src/model/deviation.py` about mean/std under large relative uncertainties, the percentiles stay reliable regardless.
  * The Flack model solves an ODE per sample, so its Monte Carlo runs **on demand** (button *Run Monte Carlo*, about 4 s for 3000 samples).
* **Parameter presets**: save/load a complete parameter set (model, values, uncertainties, note), e.g. one per resin.
* **Parameters window**: explains what to type into every field of the selected model (meaning, default, range).
* **Themes**: `dark_purple`, `dark_blue`, `black_white` (`ui/style.py`).

---

## 🔬 Physics

### 1. Emslie, Bonner and Peck (1958): Newtonian, non-volatile

Outward flow of a Newtonian liquid film on a spinning disk [[1](#references)]:

$$ \frac{\partial h}{\partial t} + \frac{\rho\omega^2 r h^2}{\eta}\frac{\partial h}{\partial r} = -\frac{2\rho\omega^2}{3\eta}h^3 $$

$t$ time, $\omega$ angular velocity, $r$ radius, $\rho$ density, $\eta$ viscosity, $h$ thickness of the *liquid* film.
For a film that is uniform in $r$:

$$ h(t) = h_0\left(1 + \frac{4\rho\omega^2}{3\eta}h_0^2\,t\right)^{-1/2} $$

Without evaporation the film keeps thinning (about $t^{-1/2}$) and never reaches a dry value, so this model
gives the wet thickness after a given spin time only.

### 2. Meyerhofer (1978): constant evaporation

Adds a solvent evaporation rate $E$ (solvent volume removed per substrate area and time) [[1](#references)]:

$$ 0 = \frac{\mathrm{d}h}{\mathrm{d}t} + \frac{2\rho\omega^2}{3\eta}h^3 + E $$

Early on, flow dominates; late, evaporation does. Where both solvent losses are equal, the film freezes:

$$ E = \frac{(1-C_0)\,2\rho\omega^2}{3\eta_0}\,h_s^3 \quad\Rightarrow\quad h_s = \left(\frac{3\eta_0 E}{2(1-C_0)\rho\omega^2}\right)^{1/3} $$

$h_s$ is the **wet** thickness at that point ($C_0$ = initial solids volume fraction). The solute volume stays
constant afterwards, so the **dry** film is

$$ h_\mathrm{f} = C_0\,h_s $$

With $E\propto\sqrt{\omega}$ this gives the widely observed $h_\mathrm{f}\propto\omega^{-1/2}$; with constant $E$ it is $\omega^{-2/3}$.
The closed form assumes an abrupt switch; integrating the full ODE gives a dry film about 3 % thinner at $C_0=10$ %.

### 3. Flack et al. (1984): concentration-dependent viscosity (depth-averaged)

Flack, Soong, Bell and Hess [[2](#references)] model a resist whose viscosity and solvent diffusivity change strongly
with polymer concentration, resolved through the film depth and with non-Newtonian behaviour.

> **What this tool implements is the depth-averaged ("well-mixed") version of that mechanism**, not the full paper model.
> It keeps *"viscosity rises and evaporation slows as the film concentrates"*, but has **no depth profile, no solid skin,
> no shear thinning and no Fujita-Doolittle diffusivity**, so the paper's five parameters ($D_0$, $A$, $B$, $\eta_0$, $\kappa_0$) are not used.

State: solute and solvent volume per area $q$, $s$ (so $h=q+s$, $\varphi=q/h$):

$$ Q = \frac{2\rho\omega^2h^3}{3\eta(\varphi)},\qquad \frac{\mathrm{d}q}{\mathrm{d}t} = -\varphi\,Q,\qquad \frac{\mathrm{d}s}{\mathrm{d}t} = -(1-\varphi)\,Q - E(\varphi) $$

solved with an adaptive RK4 until the solvent is gone; $q$ is then the dry film thickness.

| Law | Formula | Parameters |
|---|---|---|
| Evaporation | $E(\varphi) = E_0\,(1-\varphi)^n$ | $E_0$ = rate of the *pure* solvent, $n$ = slowdown ($n=0$: constant) |
| Viscosity, **exponential** (default, generic) | $\eta(\varphi) = \eta_0\,e^{k_\eta(\varphi - C_0)}$ | $k_\eta$ (0 = constant; about 18 reproduces the paper's PMMA/chlorobenzene curve between 10 and 50 wt %) |
| Viscosity, **Flack Table I** (measured PMMA, zero shear) | $\eta_{p0}(w)=\eta_\mathrm{ref}\,e^{-c/(0.043+0.040c)}\,w^{2.33}$, $c=1-w$ | only the *shape* is used, $\eta_0$ still anchors the solution as dispensed; $k_\eta$ ignored |

With $k_\eta = n = 0$ the model collapses to Meyerhofer's equation before the closed-form approximation.
Both viscosity laws stay finite for $\varphi\to1$, unlike real resins (divergence near vitrification).
The defaults come from one literature system, so **absolute numbers for other resins need calibration**
($k_\eta$, $n$ against your own ellipsometry / profilometry data).

---

## 🎛️ Using the app

1. Choose the **model** (dropdown, bottom left). Only the fields of that model are shown.
2. Fill the **Input** tab. Open **Parameters** if you are unsure what a field means.
3. Optional: **Uncertainty** tab, set a method (None / Gauss / Monte Carlo) and the $\pm\sigma$ of the parameters you are unsure about.
4. Result and plot update live. For Flack + Monte Carlo press **Run Monte Carlo**.
5. **Parameter presets...** saves the whole setup so you can come back to it.

Note: $E$ is the evaporation rate **at the spin speed you typed in**. In the plot it follows its law ($\sqrt{\omega}$ or constant) from there.

---

## 🗂️ Project structure

```text
spin-coating/
├── index.html              # web version (single self-contained file; mirrors src/model line by line)
├── main.py                 # desktop entry point
├── requirements.txt
├── data/                   # parameter presets (JSON, one file each)
├── src/
│   ├── settings.py         # app defaults: Monte Carlo, plot range, preset folder
│   ├── store.py            # read/write presets
│   └── model/              # pure physics, no UI
│       ├── parameters.py   # units, parameter specs + defaults, data shapes
│       ├── emslie.py       # model 1
│       ├── meyerhofer.py   # model 2
│       ├── flack.py        # model 3 (numerical ODE)
│       ├── deviation.py    # Gauss propagation + Monte Carlo for every model
│       └── __init__.py     # dispatch by model id, spin curves
├── ui/                     # tkinter desktop app
│   ├── app.py              # main window, live recompute
│   ├── widgets.py  plot.py  # fields, dropdowns, result display, thickness-rpm plot
│   ├── forms.py  presets.py  info.py  dialogs.py   # input forms, preset window, parameter help, popups
│   └── style.py  tex.py  texts.py   # themes, formula rendering, UI texts
├── tests/                  # see below
└── *.pdf                   # reference papers
```

`index.html` contains the same logic as `src/model/*.py` between the `LOGIC_START` / `LOGIC_END` markers.

---

## 🧪 Tests

```bash
python tests/test_model.py      # models, deviation, unit conversion (no framework needed)
python tests/test_store.py      # presets
python tests/test_themes.py     # theme palettes (needs tkinter)
python tests/test_ui_smoke.py   # app runs through all models/methods (tkinter stub, no display needed)
pytest tests/test_web_matches_python.py     # index.html == Python models (needs node + pytest)
```

Optional checks that need more setup:

* `xvfb-run -a python tests/gui_theme_check.py dark_blue [screenshot_dir]` runs the real GUI on a (virtual) display.
* `node tests/web/dom_check.js` clicks through `index.html` in a simulated browser (`npm install jsdom`).

---

## 📚 References

1. Ossila, *"Spin Coating: A Complete Guide"*. https://www.ossila.com/pages/spin-coating  
   (original: A. G. Emslie, F. T. Bonner, L. G. Peck, J. Appl. Phys. 29, 858 (1958); D. Meyerhofer, J. Appl. Phys. 49, 3993 (1978))
2. W. W. Flack, D. S. Soong, A. T. Bell and D. W. Hess, *"A mathematical model for spin coating of polymer resists"*, J. Appl. Phys. 56, 1199-1206 (1984). https://www.researchgate.net/publication/224533748_A_mathematical_model_for_spin_coating_of_polymer_resists

---

## 📄 License

Distributed under the MIT License.
