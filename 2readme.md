# Spin Coating Thickness Calculator

Desktop tool (Python / tkinter) that estimates the film thickness of a spin-coated resin with three physical
models and an optional statistical uncertainty for every input parameter.

```
pip install -r requirements.txt     # matplotlib (formatted formulas + spin-curve plot)
python main.py
```

## The physics

**Emslie, Bonner and Peck** (1958) [[1](https://www.ossila.com/pages/spin-coating)] solved the earliest description of
the outward flow of a **Newtonian, non-volatile** liquid film on a spinning disk. The film thins according to

$$ \frac{\partial h}{\partial t} + \frac{\rho\omega^2 r h^2}{\eta}\frac{\partial h}{\partial r} = -\frac{2\rho\omega^2}{3\eta}h^3 $$

Here $t$ is the elapsed process time, $\omega$ the angular velocity, $r$ the radial distance from the centre of
rotation, $\rho$ the fluid density, $\eta$ the dynamic viscosity and $h$ the thickness of the liquid film (as opposed
to the dry thin film). $\partial h/\partial t$ is the rate of change of the thickness, $\partial h/\partial r$ describes
the spreading.

For a uniform film this leads to

$$ h = h_0\left(1+\frac{4\rho\omega^2}{3\eta}h_0^2\,t\right)^{-1/2} $$

with $h_0$ the film thickness at the start of the process, $h(t=0)$. This is the first and simplest model of the
tool. Because evaporation is not accounted for, it cannot give the thickness of the final *dry* film.

**Meyerhofer** (1978) [[1](https://www.ossila.com/pages/spin-coating)] closed this gap by adding a **solvent
evaporation rate** $E$ (solvent volume removed per substrate area and time):

$$ 0 = \frac{\mathrm{d}h}{\mathrm{d}t} + \frac{2\rho\omega^2}{3\eta}h^3 + E $$

Meyerhofer proposed that spin coating passes from early flow-dominated to late evaporation-dominated thinning. The
final film thickness can then be estimated at the transition point, where the thinning rates by flow and by
evaporation are equal. Written for the solvent volume per area this reads $E = \frac{(1-C)\,2\omega^2\rho}{3\eta}h^3$,
with $C$ the volume fraction of solute in the film. Solving for the **wet** thickness $h_\mathrm{s}$ at that point:

$$ h_\mathrm{s} = {\left(\frac{3\eta_0E}{2(1-C_0)\rho\omega^2}\right)}^{1/3} $$

$C_0$ is the initial solute concentration and $\eta_0 = \eta(C_0)$. The solute no longer leaves the film afterwards,
so the **dry** film thickness is

$$ h_\mathrm{f} = C_0\,h_\mathrm{s} $$

Meyerhofer measured $E \propto \sqrt{\omega}$ for spinning photoresist, which turns $h_\mathrm{f}\propto\omega^{-2/3}$
(constant $E$) into the widely observed $h_\mathrm{f}\propto\omega^{-1/2}$. Both options are available in the tool.

**Non-Newtonian resins.** In some cases the resin changes its mechanical behaviour while it dries -- it behaves
*non-Newtonian*, which costs accuracy. In 1984, Flack et al. [[2](https://www.researchgate.net/publication/224533748_A_mathematical_model_for_spin_coating_of_polymer_resists)]
published a mathematical model that accounts for this: viscosity and solvent diffusivity change with the polymer
concentration. It is far more complex than the previous ones and needs more data to be accurate; the original paper
requires five parameters:

* diffusion pre-exponential coefficient $D_0$
* $A$
* $B$
* $\eta_0$
* $\kappa_0$

> **Status of the third model in this tool.** The constitutive equations and fitted constants of the paper are
> paywalled and were not available while writing the code. The tool therefore solves the *depth-averaged* version of
> the same mechanism numerically, with two generic laws, $\eta(\varphi)=\eta_0 e^{k_\eta\varphi}$ and
> $E(\varphi)=E_0(1-\varphi)^n$ (coefficients $k_\eta$, $n$), see `src/model/flack.py`. It reproduces "viscosity
> rises and evaporation slows as the film concentrates", but has no depth profile (solid skin) and no shear thinning,
> and the values of the paper are **not** used. To get the best or an exact result for a modern resin, an empirical
> measurement of that resin is needed anyway.

### References

1. Ossila, *"Spin Coating: A Complete Guide"*, Ossila Ltd. https://www.ossila.com/pages/spin-coating
2. W. W. Flack, D. S. Soong, A. T. Bell and D. W. Hess, *"A mathematical model for spin coating of polymer resists"*,
   Journal of Applied Physics, Vol. 56, No. 4, 1199-1206 (15 August 1984).
   https://www.researchgate.net/publication/224533748_A_mathematical_model_for_spin_coating_of_polymer_resists
3. D. Meyerhofer, *"Characteristics of resist films produced by spinning"*, J. Appl. Phys. 49, 3993-3997 (1978).
4. A. G. Emslie, F. T. Bonner, L. G. Peck, *"Flow of a viscous liquid on a rotating disk"*, J. Appl. Phys. 29, 858-862 (1958).

## Using the tool

| Element | What it does |
|---|---|
| **Model** dropdown | Emslie-Bonner-Peck -> $h(t)$ (wet film), Meyerhofer -> $h_\mathrm{f}$, Flack-type -> $h_\mathrm{f}$. The input fields follow the model. |
| **Physics** | Window with the equations, sources and disclaimer of the selected model (first version, partly placeholders). |
| **Parameters** | Window explaining what is practically typed into every field of the selected model, with default and range. |
| **Resin presets...** | Separate window: list of saved presets plus an editor with *all* parameters, E(rpm) law, how $C_0$ is entered, the uncertainties and a note. Stored as JSON in `data/`, including the model. |
| **Input / Uncertainty** tabs | Parameter values; uncertainty method (None, Gauss, Monte Carlo) with an absolute $\pm$ for every parameter of the model. |

Fields: click-drag across a box sets the value, double-click types an exact number.

**Uncertainty** works for all three models and every parameter. *Gauss* is linearised error propagation with numerical
derivatives; *Monte Carlo* draws normal / uniform / triangular samples through the full non-linear model (fixed seed,
percentiles P05 / P50 / P95). For the ODE model Monte Carlo is not live: use "Run Monte Carlo". Only the entered
uncertainties are propagated, not the systematic error of the model itself.

## Project structure

```
main.py
src/
  settings.py          app settings (Monte Carlo defaults, plot range, preset folder)
  store.py             presets as JSON (model + all values + uncertainties), reads the old flat format too
  model/
    parameters.py      units, parameter specs incl. DEFAULT VALUES, model list, data shapes
    emslie.py          physics: Emslie-Bonner-Peck       h(t)
    meyerhofer.py      physics: Meyerhofer               h_f
    flack.py           physics: concentration-dependent  h_f (numerical, depth-averaged)
    deviation.py       Gauss + Monte Carlo for any model
ui/                    tkinter (app, forms, presets, info windows, plot, widgets, style, mathtext rendering)
data/                  preset files (*.json)
tests/                 python -m pytest tests     (the UI tests run without a display)
```
