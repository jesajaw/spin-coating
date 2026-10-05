r"""
Texts for the two info windows, kept apart from the window code so they are easy to extend.

PHYSICS[model_id]  -> list of blocks (kind, content):
    ("title", text)  heading           ("text", text)  paragraph        ("note", text)  italic note
    ("tex", tex)     centred equation (mathtext, written WITHOUT surrounding $)
    ("ref", text)    reference line

PARAM_HELP[key]    -> dict(default=..., <model_id>=...): what is practically entered; the model-specific
                      entry wins if present.
PARAM_FORMULA[key] -> optional equation (mathtext, no $) that explains how the parameter is used.

PHYSICS is deliberately a first version: the long explanation, sources and disclaimer will be filled in later
(see PLACEHOLDER_*), the equations are the ones of the README.
"""

from __future__ import annotations

from src.model import parameters as P

PLACEHOLDER_PHYSICS = ("Placeholder: the detailed physical explanation (derivation, assumptions, range of validity) "
                       "will be added here.")
PLACEHOLDER_SOURCES = "Placeholder: sources and disclaimer will be added here."

REFERENCES = {
    "ossila": "Ossila, \"Spin Coating: A Complete Guide\", Ossila Ltd. https://www.ossila.com/pages/spin-coating",
    "emslie": "A. G. Emslie, F. T. Bonner, L. G. Peck, \"Flow of a viscous liquid on a rotating disk\", "
              "J. Appl. Phys. 29, 858-862 (1958).",
    "meyerhofer": "D. Meyerhofer, \"Characteristics of resist films produced by spinning\", "
                  "J. Appl. Phys. 49, 3993-3997 (1978). doi:10.1063/1.325357",
    "flack": "W. W. Flack, D. S. Soong, A. T. Bell, D. W. Hess, \"A mathematical model for spin coating of polymer "
             "resists\", J. Appl. Phys. 56, 1199-1206 (1984). doi:10.1063/1.334049",
    "bornside": "D. E. Bornside, C. W. Macosko, L. E. Scriven, \"Spin coating: one-dimensional model\", "
                "J. Appl. Phys. 66, 5185 (1989). doi:10.1063/1.343754",
}

PHYSICS: dict[str, list[tuple[str, str]]] = {
    P.MODEL_EMSLIE: [
        ("title", "Emslie, Bonner and Peck (1958)"),
        ("text", "Outward flow of a Newtonian, non-volatile liquid film on a spinning disk. Without evaporation the "
                 "film keeps thinning; there is no final dry-film thickness."),
        ("tex", r"\frac{\partial h}{\partial t} + \frac{\rho\omega^2 r h^2}{\eta}\frac{\partial h}{\partial r} "
                r"= -\frac{2\rho\omega^2}{3\eta}h^3"),
        ("text", "For a uniform film this gives the thickness $h(t)$ after the spin time $t$, starting from the initial "
                 "thickness $h_0$:"),
        ("tex", r"h = h_0\left(1+\frac{4\rho\omega^2}{3\eta}h_0^2\,t\right)^{-1/2}"),
        ("text", "For long times or thick starting films the memory of $h_0$ is lost and $h(t)$ approaches "
                 r"$\sqrt{3\eta/(4\rho\omega^2 t)}$."),
        ("note", PLACEHOLDER_PHYSICS),
        ("ref", REFERENCES["emslie"]), ("ref", REFERENCES["ossila"]),
        ("note", PLACEHOLDER_SOURCES),
    ],
    P.MODEL_MEYERHOFER: [
        ("title", "Meyerhofer (1978)"),
        ("text", "Adds a constant solvent evaporation rate $E$ (solvent volume removed per substrate area and time) to "
                 "the Emslie-Bonner-Peck flow term."),
        ("tex", r"0 = \frac{\mathrm{d}h}{\mathrm{d}t} + \frac{2\rho\omega^2}{3\eta}h^3 + E"),
        ("text", "Spin coating passes from flow-dominated to evaporation-dominated thinning. The film thickness at "
                 "which both rates are equal is estimated by ($C$ is the solute volume fraction):"),
        ("tex", r"E = \frac{(1-C)\,2\omega^2\rho}{3\eta}\,h^3"),
        ("text", r"Solved for the wet thickness $h_\mathrm{s}$ at that point, with the initial concentration $C_0$ and "
                 r"viscosity $\eta_0 = \eta(C_0)$:"),
        ("tex", r"h_\mathrm{s}={\left(\frac{3\eta_0E}{2(1-C_0)\rho\omega^2}\right)}^{1/3}"),
        ("text", "The solute no longer leaves the film afterwards, so the dry film is:"),
        ("tex", r"h_\mathrm{f} = C_0\,h_\mathrm{s}"),
        ("text", "Meyerhofer found $E$ to grow with the square root of the spin speed; this turns "
                 r"$h_\mathrm{f}\propto\omega^{-2/3}$ into the commonly observed $h_\mathrm{f}\propto\omega^{-1/2}$ "
                 "(option on the input tab)."),
        ("note", PLACEHOLDER_PHYSICS),
        ("ref", REFERENCES["meyerhofer"]), ("ref", REFERENCES["ossila"]),
        ("note", PLACEHOLDER_SOURCES),
    ],
    P.MODEL_FLACK: [
        ("title", "Flack et al. (1984) -- depth-averaged approximation"),
        ("text", "Real resins behave non-Newtonian: viscosity rises, and evaporation slows, as the film "
                 "concentrates. Flack et al. model this with concentration-dependent viscosity and solvent "
                 "diffusivity. This tool solves the well-mixed (depth-averaged) version of that mechanism "
                 "numerically, with generic constitutive laws:"),
        ("tex", r"\frac{\mathrm{d}q}{\mathrm{d}t} = -\varphi\,Q,\qquad "
                r"\frac{\mathrm{d}s}{\mathrm{d}t} = -(1-\varphi)\,Q - E(\varphi),\qquad "
                r"Q=\frac{2\rho\omega^2h^3}{3\,\eta(\varphi)}"),
        ("text", r"$q$ and $s$ are the solute and solvent volumes per area, $h = q + s$ and $\varphi = q/h$. Integration ends "
                 r"when the solvent is used up; $q$ is then the dry film thickness $h_\mathrm{f}$."),
        ("tex", r"\eta(\varphi)=\eta_0\,e^{k_\eta(\varphi-C_0)},\qquad E(\varphi)=E_0\,(1-\varphi)^n"),
        ("note", "Not included: depth profile of the concentration (solid skin), shear thinning, and the fitted "
                 r"constants of the original paper. Calibrate $k_\eta$ and $n$ against your own data."),
        ("note", PLACEHOLDER_PHYSICS),
        ("ref", REFERENCES["flack"]), ("ref", REFERENCES["bornside"]),
        ("note", PLACEHOLDER_SOURCES),
    ],
}

_UNCERTAINTY = ("Every parameter can carry an uncertainty (Uncertainty tab); it is propagated by Gaussian error "
                "propagation or Monte Carlo.")

_E_NOTE = (" It is also the reference speed at which the evaporation rate E is specified.")

PARAM_HELP: dict[str, dict[str, str]] = {
    "rpm": {
        "default": "Rotation speed of the chuck during the thinning step (the constant-speed phase). Use the speed "
                   "the spin coater actually holds, not the ramp target. Typical: 500-6000 rpm.",
        P.MODEL_MEYERHOFER: "Rotation speed of the chuck during the thinning step (the constant-speed phase). "
                            "Typical: 500-6000 rpm." + _E_NOTE,
        P.MODEL_FLACK: "Rotation speed of the chuck during the thinning step (the constant-speed phase). "
                       "Typical: 500-6000 rpm." + _E_NOTE,
    },
    "viscosity_cp": {
        "default": "Dynamic viscosity of the solution you actually dispense (resin + solvent), not of the pure "
                   "solvent. 1 cP = 1 mPa*s; water is about 1 cP, typical resins and inks 1-1000 cP. Take it from "
                   "the datasheet at your process temperature or measure it.",
        P.MODEL_MEYERHOFER: r"Dynamic viscosity $\eta_0$ of the solution you dispense (resin + solvent) at the initial "
                            "concentration $C_0$, not of the pure solvent. 1 cP = 1 mPa*s; typical resins and inks "
                            "1-1000 cP. Take it from the datasheet at your process temperature or measure it.",
        P.MODEL_FLACK: r"Dynamic viscosity $\eta_0 = \eta(C_0)$ of the solution you dispense, at the INITIAL concentration "
                       r"(resin + solvent). The model lets it grow from there as the film concentrates, through "
                       r"$k_\eta$. 1 cP = 1 mPa*s.",
    },
    "density_g_cm3": {
        "default": "Density of the full solution (solvent + solute), not of the pure solvent or the pure solute. "
                   "Typical: 0.8-1.3 g/cm3. Datasheets often give it directly.",
    },
    "h0_um": {
        P.MODEL_EMSLIE: "Wet film thickness at the start of the thinning step, in micrometres. If it is much "
                        "larger than what the film thins to, the result hardly depends on it (see the limit "
                        "shown in the result). Estimate: dispensed volume divided by substrate area.",
        "default": "Initial wet film thickness in micrometres.",
    },
    "time_s": {
        P.MODEL_EMSLIE: "Duration of the constant-speed step in seconds. Evaporation is not part of this model, so "
                        "the film keeps thinning with time; use it for short times or non-volatile liquids.",
        "default": "Spin time in seconds.",
    },
    "evaporation_um_s": {
        "default": "Solvent volume evaporated per substrate area and time, in micrometres per second, at the spin "
                   "speed above. Typical order of magnitude: 0.01-1 um/s. It depends strongly on solvent, "
                   "temperature and airflow -- best calibrated against your own thickness measurements "
                   "(ellipsometry / profilometry).",
        P.MODEL_FLACK: r"Evaporation rate $E_0$ of the pure solvent (solute fraction $\varphi = 0$), in micrometres per second, "
                       "at the spin speed above. It slows down as the film concentrates (parameter $n$). Typical "
                       "order of magnitude: 0.01-1 um/s; calibrate against your own thickness measurements.",
    },
    "e_scaling": {
        "default": "How $E$ away from the reference spin speed is estimated for the plot. Meyerhofer measured "
                   r"$E\propto\sqrt{\omega}$ for spinning photoresist; that turns $h_\mathrm{f}\propto\omega^{-2/3}$ into the "
                   r"$h_\mathrm{f}\propto\omega^{-1/2}$ usually reported. The point at the reference speed itself is "
                   "unaffected either way.",
    },
    "solids_fraction": {
        "default": "Volume of solute divided by total solution volume before spinning ($C_0$), in percent. Either type it "
                   "directly, or enter the weight fraction from the datasheet ('20 wt% solution') together with "
                   "both pure-component densities; the conversion assumes ideal (additive) mixing volumes.",
    },
    "k_eta": {
        "default": r"How sharply viscosity rises as the solute fraction $\varphi$ grows beyond $C_0$. 0 = constant viscosity. "
                   "Generic and illustrative -- calibrate against your own viscosity-vs-concentration data "
                   r"(slope of $\ln\eta$ over $\varphi$).",
    },
    "n_evap": {
        "default": "How sharply evaporation slows down as the solvent is used up. 0 = $E$ stays at $E_0$ until the "
                   r"solvent is gone. Generic and illustrative, same caveat as $k_\eta$.",
    },
}

PARAM_FORMULA: dict[str, str] = {
    "k_eta": r"\eta(\varphi)=\eta_0\,e^{k_\eta(\varphi-C_0)}",
    "n_evap": r"E(\varphi)=E_0\,(1-\varphi)^n",
    "e_scaling": r"E(\omega)=E_\mathrm{ref}\sqrt{\omega/\omega_\mathrm{ref}}",
    "solids_fraction": r"C_0=\frac{w/\rho_\mathrm{solute}}{w/\rho_\mathrm{solute}+(1-w)/\rho_\mathrm{solvent}}",
}


def param_help(key: str, model_id: str) -> str:
    entry = PARAM_HELP[key]
    return entry.get(model_id, entry["default"])


def uncertainty_note() -> str:
    return _UNCERTAINTY
