"""
Analytic Meyerhofer model (1978) for the final dry film thickness in spin
coating.

Combines the viscous thinning of Emslie/Bonner/Peck (rotating disk,
Newtonian fluid) with a constant solvent evaporation rate E. Meyerhofer
assumes an abrupt transition from "flow-dominated" to
"evaporation-dominated" thinning, at the point where both thinning rates
are equal.

    dh/dt (viscous)     = 2 * rho * omega^2 * h^3 / (3 * eta)
    dh/dt (evaporation) = E

At the transition point h_s both are equal:
    h_s = (3 * eta * E / (2 * rho * omega^2)) ** (1/3)

From that point on, the volume only changes through solvent evaporation;
which, via a solute volume balance, gives the final dry film thickness:
    h_f = c0 * h_s

Reference:
    D. Meyerhofer, "Characteristics of resist films produced by
    spinning", J. Appl. Phys. 49, 3993 (1978).
    A. G. Emslie, F. T. Bonner, L. G. Peck, J. Appl. Phys. 29, 858 (1958).

Works exclusively in SI units (m, s, kg, Pa*s, rad/s). Conversion from
"lab units" (rpm, cP, g/cm^3, um/s) happens only in from_lab_units(), and
the conversion factors themselves come from .parameters -- this file has
no UI, no dearpygui, no duplicated constants. It is the "encapsulated
compute" layer: it is only ever called with plain values, returns plain
dataclasses, and never reaches back into UI state itself.
"""

from . import parameters
from .parameters import Input, Result


def compute(p: Input) -> Result:
    """Evaluates the Meyerhofer formula. Raises ValueError on unphysical input."""
    err = parameters.validate(p)
    if err:
        raise ValueError(err)

    h_s = (3.0 * p.viscosity * p.evaporation_rate / (2.0 * p.density * p.omega ** 2)) ** (1.0 / 3.0)
    h_f = p.solids_fraction * h_s
    return Result(omega=p.omega, transition_thickness=h_s, final_thickness=h_f)


def volume_fraction_from_weight_fraction(weight_fraction: float, density_solute: float,
                                          density_solvent: float) -> float:
    """
    Converts a solute weight fraction w (0..1) into a volume fraction c0,
    given the pure-component densities of solute and solvent. Assumes
    ideal (additive) mixing volumes -- the same assumption the Meyerhofer
    derivation itself makes.
    """
    if not (0.0 < weight_fraction < 1.0):
        raise ValueError("Weight fraction must be between 0 and 1.")
    if density_solute <= 0 or density_solvent <= 0:
        raise ValueError("Densities must be > 0.")
    v_solute = weight_fraction / density_solute
    v_solvent = (1.0 - weight_fraction) / density_solvent
    return v_solute / (v_solute + v_solvent)


def from_lab_units(spin_speed_rpm: float, viscosity_cp: float, density_g_cm3: float,
                    evaporation_rate_um_s: float, solids_fraction: float) -> Input:
    """Converts the usual lab-bench/datasheet units into SI-based Input."""
    return Input(
        omega=spin_speed_rpm * parameters.RPM_TO_RAD_S,
        viscosity=viscosity_cp * parameters.CP_TO_PA_S,
        density=density_g_cm3 * parameters.G_CM3_TO_KG_M3,
        evaporation_rate=evaporation_rate_um_s * parameters.UM_S_TO_M_S,
        solids_fraction=solids_fraction,
    )
