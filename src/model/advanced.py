"""
Advanced model: concentration-dependent viscosity and evaporation rate,
solved by direct numerical integration instead of Meyerhofer's closed form.

Why this exists
----------------
Meyerhofer's Eq. 1 (see compute.py) is completely general:

    dL/dt = -(1 - c) * (2 * omega^2 * h^3) / (3 * nu) - E(c)

He only gets a closed form (Eq. 2/3) by (a) assuming eta and E are constant,
and (b) approximating the flow -> evaporation handover as instantaneous.
Flack, Soong, Bell & Hess (1984) [1] and Bornside, Macosko & Scriven (1989)
[2] made the physically important step of letting the transport
coefficients depend on the local solute concentration -- because in a real
polymer solution, viscosity climbs (often by orders of magnitude) and
solvent diffusivity collapses as the film dries.

What this module does -- and does NOT do
-----------------------------------------
Both [1] and [2] resolve concentration, viscosity and diffusivity *through
the depth* of the film (a spatial PDE, solved by finite differences/finite
elements). That is what lets them predict a solid "skin" forming at the
free surface. Reproducing that faithfully needs the papers' exact
constitutive fits and numerics, which are not available here (both papers
are paywalled; only abstracts/citations could be found).

This module instead solves the "well-mixed" (concentration uniform through
the film's depth -- a single ODE pair per instant in time, not a spatial
PDE) version of the same idea: viscosity and evaporation rate are still
functions of the *instantaneous, whole-film* concentration, but there is no
depth profile, so no skin formation and no diffusion boundary layer -- it
captures the "viscosity rises and evaporation slows as the film
concentrates" mechanism that is the qualitative point of [1]/[2], not their
full spatial detail.

Governing ODEs
--------------
Rather than track (h, phi), the state is the solute and solvent volumes per
area, q and s (h = q + s, phi = q/h) -- this makes solute conservation and
the finite solvent budget explicit instead of something the integrator can
accidentally violate:

    Q_flow  = 2 * rho * omega^2 * h^3 / (3 * eta(phi))     (Emslie flow rate)
    dq/dt   = -phi * Q_flow                                (flow only: solute is nonvolatile)
    ds/dt   = -(1 - phi) * Q_flow - E(phi)                 (flow *and* evaporation remove solvent)

with phi = q / (q + s). Integration stops once s is negligible (all solvent
gone) -- physically necessary since no evaporation law can remove solvent
that is no longer there; this is enforced explicitly rather than trusting
E(phi) to taper to zero on its own. Setting k_eta = n_evap = 0 recovers
eta(phi) = eta0, E(phi) = E0 -- i.e. exactly Meyerhofer's own Eq. 1 before
the closed-form approximation is taken (see tests/test_advanced.py for a
numerical check that this then agrees with compute.py's closed form).

Constitutive laws (generic, illustrative -- calibrate against your own
viscosity/evaporation-rate measurements; these are NOT the specific fitted
curves from [1] or [2], which were not accessible):

    eta(phi) = eta0 * exp(k_eta * phi)      k_eta = 0 -> constant viscosity
    E(phi)   = E0 * (1 - phi)^n_evap        n_evap = 0 -> constant E until solvent runs out

Limitation worth flagging: this exponential eta(phi) stays finite even as
phi -> 1, unlike real resin rheology (which diverges near the glass
transition / vitrification point and is what actually arrests flow in
[1]/[2]). In practice this matters little once phi is close to 1, since by
then little solvent remains to flow anywhere -- but it means k_eta = 0
(viscosity literally constant) with a large plot-range spin speed can still
show some residual flow after solvent depletion in principle; the "stop
once solvent is gone" rule above is what actually terminates the run.

References
----------
[1] W. W. Flack, D. S. Soong, A. T. Bell, D. W. Hess, "A mathematical model
    for spin coating of polymer resists", J. Appl. Phys. 56, 1199 (1984).
    doi:10.1063/1.334049 -- non-Newtonian, concentration-dependent
    viscosity and diffusivity.
[2] D. E. Bornside, C. W. Macosko, L. E. Scriven, "Spin coating:
    one-dimensional model", J. Appl. Phys. 66, 5185 (1989).
    doi:10.1063/1.343754 -- depth-resolved concentration/viscosity/
    diffusivity, predicts solid "skin" formation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import compute as base
from .parameters import Input, LabInput

SOLVENT_DEPLETION_TOL = 1e-7   # fraction of the *initial* solvent volume counted as "gone"


@dataclass(frozen=True)
class AdvancedInput:
    """SI-unit input, extending the base Input with the two constitutive-law coefficients."""
    omega: float
    viscosity0: float          # eta0: viscosity at phi = 0 [Pa*s]
    density: float             # kg/m^3 (assumed constant -- see module limitations)
    evaporation_rate0: float   # E0: evaporation rate at phi = 0 [m/s]
    solids_fraction0: float    # initial phi
    k_eta: float = 0.0         # viscosity growth coefficient (0 = off, recovers base model)
    n_evap: float = 0.0        # evaporation slowdown exponent (0 = off, recovers base model)


@dataclass(frozen=True)
class AdvancedResult:
    final_thickness: float          # h_f [m]: solute volume per area once solvent has run out
    final_phi: float                # solute volume fraction reached (<1 if the step cap was hit first)
    steps_used: int
    h0_used: float                  # the internal initial wet thickness (see _initial_thickness)
    converged: bool                 # False if max_steps was hit before solvent was fully depleted

    @property
    def final_thickness_nm(self) -> float:
        return self.final_thickness * 1e9


def _eta(phi: float, eta0: float, k_eta: float) -> float:
    return eta0 * math.exp(k_eta * phi)


def _evap(phi: float, e0: float, n_evap: float) -> float:
    return e0 * max(1.0 - phi, 0.0) ** n_evap if n_evap > 0 else e0


def _derivatives(q: float, s: float, p: AdvancedInput) -> tuple[float, float]:
    h = q + s
    phi = q / h if h > 0 else 1.0
    eta = _eta(phi, p.viscosity0, p.k_eta)
    q_flow = (2.0 * p.density * p.omega ** 2 * h ** 3) / (3.0 * eta)
    dq_dt = -phi * q_flow
    ds_dt = -(1.0 - phi) * q_flow - _evap(phi, p.evaporation_rate0, p.n_evap)
    return dq_dt, ds_dt


def _initial_thickness(p: AdvancedInput, headroom: float = 20.0) -> float:
    """
    A wet starting thickness large enough that the final result is
    (matched-asymptotically) independent of it -- the same reasoning
    Meyerhofer relies on for his closed form. Uses his own transition
    thickness h_s at phi0 as a length scale; tests/test_advanced.py checks
    numerically that h_f barely changes if `headroom` is doubled.
    """
    base_input = Input(omega=p.omega, viscosity=p.viscosity0, density=p.density,
                       evaporation_rate=p.evaporation_rate0, solids_fraction=p.solids_fraction0)
    h_s = base.transition_thickness(base_input)
    return headroom * h_s


def _rk4_step(q: float, s: float, p: AdvancedInput, dt: float) -> tuple[float, float]:
    """One classic RK4 step; each stage clamps q, s >= 0 so an overshooting
    trial step can't hand a negative volume to the next stage."""
    def clamp(q_, s_):
        return max(q_, 0.0), max(s_, 0.0)

    k1q, k1s = _derivatives(q, s, p)
    q2, s2 = clamp(q + 0.5 * dt * k1q, s + 0.5 * dt * k1s)
    k2q, k2s = _derivatives(q2, s2, p)
    q3, s3 = clamp(q + 0.5 * dt * k2q, s + 0.5 * dt * k2s)
    k3q, k3s = _derivatives(q3, s3, p)
    q4, s4 = clamp(q + dt * k3q, s + dt * k3s)
    k4q, k4s = _derivatives(q4, s4, p)
    dq = (dt / 6.0) * (k1q + 2 * k2q + 2 * k3q + k4q)
    ds = (dt / 6.0) * (k1s + 2 * k2s + 2 * k3s + k4s)
    return dq, ds


def simulate(p: AdvancedInput, headroom: float = 20.0, max_steps: int = 4000,
            rel_tol: float = 1e-7) -> AdvancedResult:
    """
    Adaptive-step RK4 (step-doubling error control) on (q, s): every step
    is tried once at size dt and once as two steps of dt/2; if the two
    disagree by more than `rel_tol` (relative, in q), dt is halved and the
    step retried, otherwise the (more accurate) half-step result is kept
    and dt is allowed to grow for the next step -- this lets the solver
    take large strides once the film has relaxed, without needing to guess
    a time grid up front (the natural relaxation timescale changes by
    orders of magnitude as eta(phi) climbs while drying).

    Stops as soon as the solvent volume s drops to SOLVENT_DEPLETION_TOL of
    its initial value -- required because no evaporation law here tapers
    itself exactly to zero solvent (see module docstring); q at that point
    is the dry film thickness (solute is only ever removed by flow, never
    by evaporation, so it needs no separate convergence check).
    """
    if p.omega <= 0 or p.viscosity0 <= 0 or p.density <= 0 or p.evaporation_rate0 <= 0:
        raise ValueError("Spin speed, viscosity, density and evaporation rate must all be > 0.")
    if not (0.0 < p.solids_fraction0 < 1.0):
        raise ValueError("Initial solids volume fraction must be between 0 and 1 (exclusive).")

    h0 = _initial_thickness(p, headroom)
    q = h0 * p.solids_fraction0
    s = h0 * (1.0 - p.solids_fraction0)
    s0 = s
    s_floor = s0 * SOLVENT_DEPLETION_TOL

    tau0 = 3.0 * p.viscosity0 / (4.0 * p.density * p.omega ** 2 * h0 ** 2)
    dt = tau0 * 0.05
    accepted = 0
    converged = False

    for _ in range(max_steps):
        for _retry in range(40):
            dq_full, ds_full = _rk4_step(q, s, p, dt)
            dq1, ds1 = _rk4_step(q, s, p, dt * 0.5)
            q_mid, s_mid = max(q + dq1, 0.0), max(s + ds1, 0.0)
            dq2, ds2 = _rk4_step(q_mid, s_mid, p, dt * 0.5)
            q_half = max(q_mid + dq2, 0.0)
            q_full = max(q + dq_full, 0.0)
            err = abs(q_half - q_full) / max(q_half, 1e-30)
            if err <= rel_tol or dt < tau0 * 1e-10:
                break
            dt *= 0.5

        s_half = max(s_mid + ds2, 0.0)

        if s_half <= s_floor:
            # bisect this last accepted step in time to land close to s == s_floor,
            # instead of reporting q from whatever overshoot the step produced
            lo_dt, hi_dt = 0.0, dt
            q_at, s_at = q, s
            for _bisect in range(30):
                mid_dt = 0.5 * (lo_dt + hi_dt)
                dq_m, ds_m = _rk4_step(q, s, p, mid_dt)
                s_try = max(s + ds_m, 0.0)
                if s_try > s_floor:
                    lo_dt = mid_dt
                else:
                    hi_dt = mid_dt
                    q_at, s_at = max(q + dq_m, 0.0), s_try
            q, s = q_at, s_at
            accepted += 1
            converged = True
            break

        q, s = q_half, s_half
        accepted += 1
        if err <= rel_tol / 8.0:
            dt *= 1.3

    return AdvancedResult(final_thickness=q, final_phi=(q / (q + s) if (q + s) > 0 else 1.0),
                          steps_used=accepted, h0_used=h0, converged=converged)


def thickness_nm(lab: LabInput, k_eta: float, n_evap: float) -> float:
    """Convenience wrapper in lab units, mirroring compute.thickness_nm's signature style."""
    p = AdvancedInput(
        omega=lab.rpm * math.pi / 30.0,
        viscosity0=lab.viscosity_cp * 1e-3, density=lab.density_g_cm3 * 1e3,
        evaporation_rate0=lab.evaporation_um_s * 1e-6, solids_fraction0=lab.solids_fraction,
        k_eta=k_eta, n_evap=n_evap,
    )
    return simulate(p).final_thickness_nm


def spin_curve(lab: LabInput, k_eta: float, n_evap: float, rpm_min: float, rpm_max: float,
              points: int, log_spaced: bool = True) -> list[tuple[float, float]]:
    if not (0 < rpm_min < rpm_max):
        raise ValueError("Plot range needs 0 < min < max.")
    points = max(points, 2)
    if log_spaced:
        ratio = (rpm_max / rpm_min) ** (1.0 / (points - 1))
        xs = [rpm_min * ratio ** i for i in range(points)]
    else:
        xs = [rpm_min + (rpm_max - rpm_min) * i / (points - 1) for i in range(points)]
    out = []
    for x in xs:
        lab_x = LabInput(rpm=x, viscosity_cp=lab.viscosity_cp, density_g_cm3=lab.density_g_cm3,
                         evaporation_um_s=base.evaporation_at(lab.evaporation_um_s, lab.rpm, x, lab.e_scaling),
                         solids_fraction=lab.solids_fraction, e_scaling=lab.e_scaling)
        out.append((x, thickness_nm(lab_x, k_eta, n_evap)))
    return out
