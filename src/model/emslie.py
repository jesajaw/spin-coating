r"""
Model 1 -- Emslie, Bonner and Peck (1958): Newtonian, NON-volatile liquid film.

Pure physics, no UI. Works on the LAB-unit value dict described in parameters.py
and converts to SI internally.

Governing equation (thin film on a rotating disk, lubrication approximation):

    dh/dt + (rho w^2 r h^2 / eta) dh/dr = -(2 rho w^2 / (3 eta)) h^3

For a film that is uniform in r this reduces to an ODE with the closed-form solution

    h(t) = h0 * (1 + 4 rho w^2 h0^2 t / (3 eta))^(-1/2)                     (Eq. 1)

For long times (or a thick initial film) the memory of h0 is lost and

    h(t) -> sqrt( 3 eta / (4 rho w^2 t) )                                    (Eq. 2)

There is no evaporation, so h(t) keeps shrinking as t^(-1/2) and never reaches
a final dry-film value -- use Meyerhofer (meyerhofer.py) for that.

Reference
---------
A. G. Emslie, F. T. Bonner, L. G. Peck, "Flow of a viscous liquid on a rotating
disk", J. Appl. Phys. 29, 858-862 (1958).
"""

from __future__ import annotations

import math

from . import parameters as P
from .parameters import Result

KEYS = P.MODELS[P.MODEL_EMSLIE].keys


def validate(v: dict) -> str | None:
    if v["rpm"] <= 0:
        return "Spin speed must be > 0."
    if v["viscosity_cp"] <= 0:
        return "Viscosity must be > 0."
    if v["density_g_cm3"] <= 0:
        return "Density must be > 0."
    if v["h0_um"] <= 0:
        return "Initial film thickness must be > 0."
    if v["time_s"] < 0:
        return "Spin time must be >= 0."
    return None


def _si(v: dict) -> tuple[float, float, float, float, float]:
    return (v["rpm"] * P.RPM_TO_RAD_S, v["viscosity_cp"] * P.CP_TO_PA_S, v["density_g_cm3"] * P.G_CM3_TO_KG_M3,
            v["h0_um"] * P.UM_TO_M, v["time_s"])


def thickness_m(omega: float, eta: float, rho: float, h0: float, t: float) -> float:
    """Eq. 1, SI units."""
    return h0 / math.sqrt(1.0 + 4.0 * rho * omega ** 2 * h0 ** 2 * t / (3.0 * eta))


def long_time_limit_m(omega: float, eta: float, rho: float, t: float) -> float:
    """Eq. 2, SI units: the thickness that does not depend on h0 any more."""
    return math.sqrt(3.0 * eta / (4.0 * rho * omega ** 2 * t)) if t > 0 else float("inf")


def thickness_nm(v: dict) -> float:
    err = validate(v)
    if err:
        raise ValueError(err)
    return thickness_m(*_si(v)) * P.M_TO_NM


def compute(v: dict) -> Result:
    err = validate(v)
    if err:
        raise ValueError(err)
    omega, eta, rho, h0, t = _si(v)
    h = thickness_m(omega, eta, rho, h0, t)
    lim = long_time_limit_m(omega, eta, rho, t)
    details = [rf"$\omega$ = {omega:.1f} rad/s", rf"$h/h_0$ = {h / h0:.4f}"]
    if math.isfinite(lim):
        details.append(rf"Limit for $h_0\to\infty$: {lim * P.M_TO_NM:,.1f} nm")
    return Result(thickness_nm=h * P.M_TO_NM, details=tuple(details))
