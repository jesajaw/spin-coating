r"""
Model 2 -- Meyerhofer (1978): Newtonian liquid with constant solvent evaporation.

Pure physics, no UI. Works on the LAB-unit value dict described in parameters.py
and converts to SI internally.

Emslie, Bonner and Peck solved the flow of a non-volatile liquid (emslie.py);
Meyerhofer added a solvent evaporation rate E (solvent volume removed per
substrate area and time). With the solute volume fraction C and the kinematic
viscosity nu = eta / rho:

    dh/dt = -(2 w^2 h^3 / (3 nu)) (1 - C) - E                                (Eq. 1)

Early on outflow dominates and C stays at its initial value C0; late, the film
is so thin that flow is negligible and only evaporation is left. If the switch
is abrupt, it happens where both terms of Eq. 1 are equal, at the WET thickness

    h_s = ( 3 eta E / (2 (1 - C0) rho w^2) )^(1/3)                           (Eq. 2)

After that point the solute volume per area no longer changes, so with ideal
(additive) mixing volumes the DRY film is

    h_f = C0 * h_s                                                           (Eq. 3)

Eq. 2/3 give h_f ~ eta^(1/3) E^(1/3) w^(-2/3). Meyerhofer measured E ~ sqrt(w)
for spinning photoresist, which turns this into the widely observed
h_f ~ w^(-1/2) (parameters.E_SQRT).

Assumptions/limits: Newtonian liquid, constant and spatially uniform
evaporation rate, abrupt transition, no spin-up phase, uniform concentration
over the film depth, viscosity independent of concentration (see flack.py for
the concentration-dependent variant).

References
----------
[1] D. Meyerhofer, "Characteristics of resist films produced by spinning",
    J. Appl. Phys. 49, 3993-3997 (1978). doi:10.1063/1.325357
[2] A. G. Emslie, F. T. Bonner, L. G. Peck, J. Appl. Phys. 29, 858-862 (1958).
"""

from __future__ import annotations

from . import parameters as P
from .parameters import Result

KEYS = P.MODELS[P.MODEL_MEYERHOFER].keys


def validate(v: dict) -> str | None:
    if v["rpm"] <= 0:
        return "Spin speed must be > 0."
    if v["viscosity_cp"] <= 0:
        return "Viscosity must be > 0."
    if v["density_g_cm3"] <= 0:
        return "Density must be > 0."
    if v["evaporation_um_s"] <= 0:
        return "Evaporation rate must be > 0."
    if not (0.0 < v["solids_fraction"] < 1.0):
        return "Solids volume fraction must be between 0 and 1 (exclusive)."
    return None


def evaporation_m_s(v: dict) -> float:
    """E at the spin speed of this evaluation [m/s], following the chosen E(rpm) law."""
    e = P.evaporation_at(v["evaporation_um_s"], v.get("rpm_ref", v["rpm"]), v["rpm"], v.get("e_scaling", P.E_SQRT))
    return e * P.UM_S_TO_M_S


def transition_thickness_m(omega: float, eta: float, rho: float, evap: float, c0: float) -> float:
    """Eq. 2, SI units: wet thickness where flow and evaporation thin the film equally fast."""
    return (3.0 * eta * evap / (2.0 * rho * omega ** 2 * (1.0 - c0))) ** (1.0 / 3.0)


def _si(v: dict) -> tuple[float, float, float, float, float]:
    return (v["rpm"] * P.RPM_TO_RAD_S, v["viscosity_cp"] * P.CP_TO_PA_S, v["density_g_cm3"] * P.G_CM3_TO_KG_M3,
            evaporation_m_s(v), v["solids_fraction"])


def thickness_nm(v: dict) -> float:
    """Eq. 3 in nm. Raises ValueError on unphysical input."""
    err = validate(v)
    if err:
        raise ValueError(err)
    omega, eta, rho, evap, c0 = _si(v)
    return c0 * transition_thickness_m(omega, eta, rho, evap, c0) * P.M_TO_NM


def compute(v: dict) -> Result:
    err = validate(v)
    if err:
        raise ValueError(err)
    omega, eta, rho, evap, c0 = _si(v)
    h_s = transition_thickness_m(omega, eta, rho, evap, c0)
    details = (rf"Wet transition thickness $h_\mathrm{{s}}$: {h_s * P.M_TO_UM:.3f} $\mu$m",
               rf"$\omega$ = {omega:.1f} rad/s",
               rf"$E$ used: {evap * P.M_TO_UM:.4f} $\mu$m/s",
               rf"$C_0$ used: {c0 * 100:.2f} %")
    return Result(thickness_nm=c0 * h_s * P.M_TO_NM, details=details)
