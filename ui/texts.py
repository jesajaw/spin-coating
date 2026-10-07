r"""
Texts for the parameter window, kept apart from the window code so they are easy to extend.

PARAM_HELP[key]    -> dict(default=..., <model_id>=...): what is practically entered; the model-specific
                      entry wins if present.
PARAM_FORMULA[key] -> optional equation (mathtext, no $) that explains how the parameter is used.
"""

from __future__ import annotations

from src.model import parameters as P

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
    "visc_law": {
        "default": "How the viscosity rises while the film concentrates. 'Exponential' is a one-number generic law "
                   r"(see $k_\eta$ below). 'Flack Table I' uses the measured zero-shear law of PMMA in chlorobenzene "
                   r"from the 1984 paper; only its shape is used, $\eta_0$ still anchors the solution as dispensed. It "
                   "ignores shear thinning and the depth profile, so treat it as a realistic shape, not a PMMA "
                   "prediction for other polymers.",
    },
    "k_eta": {
        "default": r"How sharply viscosity rises as the solute fraction $\varphi$ grows beyond $C_0$. 0 = constant viscosity. "
                   "Generic and illustrative; about 18 matches the PMMA curve of the Flack paper (10-50 wt%). Calibrate "
                   r"against your own viscosity-vs-concentration data (slope of $\ln\eta$ over $\varphi$). "
                   "Unused when the Flack Table I law is selected.",
    },
    "n_evap": {
        "default": "How sharply evaporation slows down as the solvent is used up. 0 = $E$ stays at $E_0$ until the "
                   r"solvent is gone. Generic and illustrative, same caveat as $k_\eta$.",
    },
}

PARAM_FORMULA: dict[str, str] = {
    "visc_law": r"\eta_{p0}(w)\propto e^{-c/(0.043+0.040c)}\,w^{2.33},\; c=1-w",
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
