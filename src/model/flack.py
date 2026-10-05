r"""
Model 3 -- concentration-dependent viscosity and evaporation (Flack et al. 1984
idea), solved by numerical integration instead of a closed form.

Pure physics, no UI. Works on the LAB-unit value dict described in parameters.py
and converts to SI internally.

IMPORTANT -- what this is and is not
------------------------------------
Flack, Soong, Bell & Hess (1984) [1] account for the non-Newtonian behaviour of
a resist and for viscosity and solvent diffusivity that change with polymer
concentration (a spatial model through the film depth; their fitted constants
-- D0, A, B, eta0, kappa0 -- are NOT available to this code, the paper is
paywalled). This module instead solves the "well-mixed" (depth-averaged)
version of the same mechanism with two GENERIC, illustrative constitutive laws:

    eta(phi) = eta0 * exp(k_eta * (phi - C0))   eta0 = eta(C0): the viscosity of the solution as
                                                dispensed, same meaning as in meyerhofer.py;
                                                k_eta = 0 -> constant viscosity
    E(phi)   = E0 * (1 - phi)^n                 E0 = rate of the pure solvent (phi = 0);
                                                n     = 0 -> constant E

It captures "viscosity rises and evaporation slows as the film concentrates",
but no depth profile, no solid skin, no shear thinning. Calibrate k_eta and n
against your own viscosity-vs-concentration and thickness data.

Governing ODEs
--------------
State: solute and solvent volumes per area q and s (h = q + s, phi = q / h),
which makes solute conservation and the finite solvent budget explicit:

    Q_flow = 2 rho w^2 h^3 / (3 eta(phi))      (Emslie flow rate)
    dq/dt  = -phi * Q_flow                     (solute is non-volatile)
    ds/dt  = -(1 - phi) * Q_flow - E(phi)      (flow AND evaporation remove solvent)

Integration stops once s is negligible; q is then the dry film thickness.
With k_eta = n = 0 this is Meyerhofer's Eq. 1 before the closed-form
approximation (tests/test_model.py checks that it agrees with meyerhofer.py).

Limitation: the exponential eta(phi) stays finite as phi -> 1, unlike real resin
rheology (divergence near vitrification).

References
----------
[1] W. W. Flack, D. S. Soong, A. T. Bell, D. W. Hess, "A mathematical model for
    spin coating of polymer resists", J. Appl. Phys. 56, 1199 (1984).
    doi:10.1063/1.334049
[2] D. E. Bornside, C. W. Macosko, L. E. Scriven, "Spin coating: one-dimensional
    model", J. Appl. Phys. 66, 5185 (1989). doi:10.1063/1.343754
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import meyerhofer
from . import parameters as P
from .parameters import Result

KEYS = P.MODELS[P.MODEL_FLACK].keys
SOLVENT_DEPLETION_TOL = 1e-7   # fraction of the initial solvent volume counted as "gone"


@dataclass(frozen=True)
class SimResult:
    final_thickness: float   # h_f [m]: solute volume per area once the solvent has run out
    final_phi: float
    steps_used: int
    h0_used: float           # the internal initial wet thickness
    converged: bool


def validate(v: dict) -> str | None:
    err = meyerhofer.validate(v)
    if err:
        return err
    if v["k_eta"] < 0:
        return "Viscosity growth k_eta must be >= 0."
    if v["n_evap"] < 0:
        return "Evaporation slowdown n must be >= 0."
    return None


def _derivatives(q: float, s: float, omega: float, eta0: float, rho: float, e0: float,
                 k_eta: float, n_evap: float, c0: float) -> tuple[float, float]:
    h = q + s
    phi = q / h if h > 0 else 1.0
    eta = eta0 * math.exp(k_eta * (phi - c0))      # eta(C0) = eta0, rises for phi > C0
    q_flow = (2.0 * rho * omega ** 2 * h ** 3) / (3.0 * eta)
    evap = e0 * max(1.0 - phi, 0.0) ** n_evap if n_evap > 0 else e0
    return -phi * q_flow, -(1.0 - phi) * q_flow - evap


def _rk4_step(q: float, s: float, dt: float, args: tuple) -> tuple[float, float]:
    """One classic RK4 step; each stage clamps q, s >= 0 so an overshooting trial can't go negative."""
    k1q, k1s = _derivatives(q, s, *args)
    k2q, k2s = _derivatives(max(q + 0.5 * dt * k1q, 0.0), max(s + 0.5 * dt * k1s, 0.0), *args)
    k3q, k3s = _derivatives(max(q + 0.5 * dt * k2q, 0.0), max(s + 0.5 * dt * k2s, 0.0), *args)
    k4q, k4s = _derivatives(max(q + dt * k3q, 0.0), max(s + dt * k3s, 0.0), *args)
    return (dt / 6.0) * (k1q + 2 * k2q + 2 * k3q + k4q), (dt / 6.0) * (k1s + 2 * k2s + 2 * k3s + k4s)


def simulate(omega: float, eta0: float, rho: float, e0: float, c0: float, k_eta: float, n_evap: float,
             headroom: float = 20.0, max_steps: int = 4000, rel_tol: float = 1e-7) -> SimResult:
    """
    Adaptive-step RK4 (step doubling) on (q, s), SI units. The initial wet thickness is
    `headroom` times Meyerhofer's transition thickness, so large that the result no longer
    depends on it (tests check this). Stops when the solvent is gone (see module docstring).
    """
    if omega <= 0 or eta0 <= 0 or rho <= 0 or e0 <= 0:
        raise ValueError("Spin speed, viscosity, density and evaporation rate must all be > 0.")
    if not (0.0 < c0 < 1.0):
        raise ValueError("Initial solids volume fraction must be between 0 and 1 (exclusive).")

    args = (omega, eta0, rho, e0, k_eta, n_evap, c0)
    h0 = headroom * meyerhofer.transition_thickness_m(omega, eta0, rho, e0, c0)
    q, s = h0 * c0, h0 * (1.0 - c0)
    s_floor = s * SOLVENT_DEPLETION_TOL

    tau0 = 3.0 * eta0 / (4.0 * rho * omega ** 2 * h0 ** 2)
    dt = tau0 * 0.05
    accepted, converged, err = 0, False, 0.0
    s_half = s

    for _ in range(max_steps):
        for _retry in range(40):
            dq_full, _ds_full = _rk4_step(q, s, dt, args)
            dq1, ds1 = _rk4_step(q, s, dt * 0.5, args)
            q_mid, s_mid = max(q + dq1, 0.0), max(s + ds1, 0.0)
            dq2, ds2 = _rk4_step(q_mid, s_mid, dt * 0.5, args)
            q_half, q_full = max(q_mid + dq2, 0.0), max(q + dq_full, 0.0)
            err = abs(q_half - q_full) / max(q_half, 1e-30)
            if err <= rel_tol or dt < tau0 * 1e-10:
                break
            dt *= 0.5
        s_half = max(s_mid + ds2, 0.0)

        if s_half <= s_floor:
            # bisect the last accepted step so we land on s == s_floor instead of the overshoot
            lo_dt, hi_dt, q_at, s_at = 0.0, dt, q, s
            for _bisect in range(30):
                mid_dt = 0.5 * (lo_dt + hi_dt)
                dq_m, ds_m = _rk4_step(q, s, mid_dt, args)
                s_try = max(s + ds_m, 0.0)
                if s_try > s_floor:
                    lo_dt = mid_dt
                else:
                    hi_dt, q_at, s_at = mid_dt, max(q + dq_m, 0.0), s_try
            q, s = q_at, s_at
            accepted += 1
            converged = True
            break

        q, s = q_half, s_half
        accepted += 1
        if err <= rel_tol / 8.0:
            dt *= 1.3

    return SimResult(final_thickness=q, final_phi=(q / (q + s) if (q + s) > 0 else 1.0),
                     steps_used=accepted, h0_used=h0, converged=converged)


def _run(v: dict) -> tuple[SimResult, float, float]:
    err = validate(v)
    if err:
        raise ValueError(err)
    omega = v["rpm"] * P.RPM_TO_RAD_S
    evap = meyerhofer.evaporation_m_s(v)
    res = simulate(omega, v["viscosity_cp"] * P.CP_TO_PA_S, v["density_g_cm3"] * P.G_CM3_TO_KG_M3,
                   evap, v["solids_fraction"], v["k_eta"], v["n_evap"])
    if not res.converged:
        raise ValueError("Integration did not converge (solvent never fully depleted) -- "
                         "try a smaller n or check the inputs.")
    return res, omega, evap


def thickness_nm(v: dict) -> float:
    return _run(v)[0].final_thickness * P.M_TO_NM


def compute(v: dict) -> Result:
    res, omega, evap = _run(v)
    details = (rf"$k_\eta$ = {v['k_eta']:.2f},  $n$ = {v['n_evap']:.2f}",
               rf"$\omega$ = {omega:.1f} rad/s",
               rf"$E$ used: {evap * P.M_TO_UM:.4f} $\mu$m/s",
               rf"$C_0$ used: {v['solids_fraction'] * 100:.2f} %",
               rf"Final solute fraction: {res.final_phi * 100:.2f} %")
    return Result(thickness_nm=res.final_thickness * P.M_TO_NM, details=details)
