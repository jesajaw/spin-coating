# 🌀 Spin Coating Approximation Tool
> ⚠️ **Status: Under Development**
---

This is an approximation script with UI for spin-coating processes with different models for different application fields. From a simple model to a far more complex describtion to even account non-newtonian fluiddynamic. It should predicts the final dry film thickness of a spin-coated layer, and how it changes with spin speed, offers Gaussian and Monte-Carlo Derivation and tries to simplify this theoretical, physical PDE into a lab-useable or daily use tool.

---

## Features

* **Live results**: every field recomputes the result and the plot, debounced so dragging a value doesn't spam the model.
* **Thickness-rpm plot**: $h(\omega)$ over a chosen range, with the current operating point marked
* **Two ways to enter the solids fraction**: directly as a volume fraction or from a weight fraction plus the two pure-component densities.
* **Presets**: save/load parameters (esspecially materials viscosity, density, evaporation rate and solids fraction)
* **Statistical deviation** on the result and the plot
  * *Gauss (analytic)*: closed-form linearised error propagation -- instant, first-order only.
  * *Monte Carlo*: samples every uncertain parameter from a normal, uniform or triangular distribution and propagates it through the full, non-linearised model; also reports P05/P50/P95. See the caveat in `src/model/deviation.py` about the mean/std under large relative uncertainties -- the percentiles stay reliable regardless.
* **Different themes**: (`dark_purple`, `dark_blue`, `black_white`) in `ui/style.py`.

---

## Physic

**Emslie, Bonner and Peck** (1958) [[1](https://www.ossila.com/pages/spin-coating)] solved the earliest way of describing the outward flow of a **Newtonian, non-volatile** liquid film on a spinning disk: it thins at the rate:


$$ \frac{\partial h}{\partial t} + \frac{\rho\omega^2rh^2}{\eta}\frac{\partial h}{\partial r} = -\frac{2\rho\omega^2}{3\eta}h^3 $$

Here, $t$ denotes the elapsed process time, $\omega$ the angular velocity, $r$ the radial distance from the center of rotation, $\rho$ the fluid density, $\eta$ the dynamic viscosity, and $h$ the thickness of the liquid film (as opposed to the dry thin film). The temporal derivative $\frac{\partial h}{\partial t}$ represents the rate of change of the layer thickness, while the radial derivative $\frac{\partial h}{\partial r}$ describes the rate of spreading.

For considering a uniform film, this leads to:

$$h=h_0{\left(1+\frac{4\rho\omega^2}{3\eta}h_0^2t\right)}^{-1/2}$$

with $h_0$ as the filmthickness at the beginning of the process $h(t=0, ...)$. This is the first and simplest Model in this spin-coating tool. Due not accounting evaporation, it cant be used for calculating the exact thickness of the final dry film.

This problem got solved by **Meyerhofer** (1978) [[1](https://www.ossila.com/pages/spin-coating)] who modefied this equation by adding a a **solvent evaporation rate** $E$ (solvent volume removed per substrate area and time):

$$ 0 = \frac{\mathrm{d} h}{\mathrm{d} t} + \frac{2\rho\omega^2}{3\eta}h^3 + E $$

Meyerhofer proposed that spin coating transitions from early flow-dominated thinning to later evaporation-dominated thinning, enabling analytical estimation of final film thickness at the transition point where both thinning rates by flow and evaporation are equal:

$$ E = \frac{(1-C)2\omega^2\rho}{3\eta}h_0^3$$

Where $C$ is the volume fraction of solute in the film. Following some math steps leads to the solution:

$$h={\left(\frac{3\eta_0E}{2(1-C_0)\rho\omega^2}\right)}^{1/3}$$

Where $C_0$ is the initial concentration of solute, and $\eta_0$ equates to $\eta(C_0)$.

But there is still one issue: in some cases, the resin / fluid changing his mechanical characteristics -- or be more accurate **behaives non newtonian**. This costs actual value accurency. But in 1984 [[2](https://www.researchgate.net/publication/224533748_A_mathematical_model_for_spin_coating_of_polymer_resists)] puplished a mathematical model with accounting this issue.

But it is far more complexe than the previous once: more data is needed to be accurate! To be more qlearly, this theoretical model requires to identify five parameters:
* Diffusion Preexponential Coefficient $D_0$
* $A$
* $B$
* $\eta_0$
* $\kappa_0$

In this tool, I used the given numerical values given in the articel [[2](https://www.researchgate.net/publication/224533748_A_mathematical_model_for_spin_coating_of_polymer_resists)] which may are not suitable for modern resins. To get to the best or exact result, empirical measurement of the eventually new resin is needed.

---

## References

1. Ossila, *"Spin Coating: A Complete Guide"*, Ossila Ltd. https://www.ossila.com/pages/spin-coating

2. W. W. Flack, D. S. Soong, A. Bell and D. W. Hess, *"A mathematical model for spin coating of polymer resists"*, Journal of Applied Physics. Vol. 56, No. 4, 1199-1206 (15 August 1984). https://www.researchgate.net/publication/224533748_A_mathematical_model_for_spin_coating_of_polymer_resists

---

## Project Structure

```text
spin-coating/
├── index.html              # web version (single self-contained file, served by GitHub Pages)
├── main.py                 # desktop entry point
├── src/
│   ├── settings.py         # app-level defaults (Monte Carlo, plot range, preset location)
│   ├── store.py            # resin presets (read/write data/*.json)
│   └── model/
│       ├── parameters.py   # constants, unit conversions, Input/Result/LabInput/Sigmas
│       ├── compute.py      # Meyerhofer model (Eq. 2/3), spin_curve()
│       ├── advanced.py     # concentration-dependent viscosity/evaporation (numerical ODE)
│       └── deviation.py    # Gauss propagation + Monte Carlo (both models)
├── ui/
│   ├── app.py               # tkinter main window (3-column layout, live recompute)
│   ├── widgets.py           # Cell, NumberField, Dropdown, ResultDisplay, SpinCurvePlot
│   ├── dialogs.py           # themed popups
│   └── style.py             # theme colors, fonts, ttk styles
├── data/                    # saved resin presets (JSON, one file each)
├── tests/
│   └── test_model.py        # sanity tests for src/model (no framework needed)
├── LICENSE
```

The `index.html` mirrors `src/model/*.py` line-for-line (see the
`LOGIC_START`/`LOGIC_END` block in the file) so both versions give the same
numbers; a random cross-check between the two is what `tests/test_model.py`'s
Python side is checked against during development.

---

## Usage

### Web (GitHub Pages)

The web version needs no build step and no server -- it's a single HTML file. Presets you save there are stored in your browser (`localStorage`), not shared with anyone else; the two example presets ship built in.

### Desktop

No installation needed beyond Python 3.9+

```bash
python main.py
```

Presets are read/written as JSON files under `data/`.

### Running the tests

This is actually far more complex to do, but I tried implementing some basic tests, bash

```bash
python tests/test_model.py
python tests/test_advanced.py
```
for testing.

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.
