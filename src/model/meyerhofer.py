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
the conversion factors themselves come from config.physics -- this file
has no UI, no dearpygui, no duplicated constants.
"""

from dataclasses import dataclass

import physics as cfg


@dataclass(frozen=True)
class MeyerhoferInput:
    """SI-unit input to the Meyerhofer formula."""
    omega: float             # angular velocity [rad/s]
    viscosity: float         # dynamic viscosity of the solution [Pa*s]
    density: float           # density of the solution [kg/m^3]
    evaporation_rate: float  # evaporation rate E [m/s] (volume / area / time)
    solids_fraction: float   # initial solute volume fraction c0, 0 < c0 < 1


@dataclass(frozen=True)
class MeyerhoferResult:
    omega: float                  # rad/s, echoed back for display
    transition_thickness: float   # h_s: wet film thickness at the flow/evaporation transition [m]
    final_thickness: float        # h_f: final dry film thickness [m]

    @property
    def final_thickness_nm(self) -> float:
        return self.final_thickness * cfg.M_TO_NM

    @property
    def final_thickness_um(self) -> float:
        return self.final_thickness * cfg.M_TO_UM

    @property
    def transition_thickness_um(self) -> float:
        return self.transition_thickness * cfg.M_TO_UM


def validate(p: MeyerhoferInput) -> str | None:
    """Returns an error message if the input is unphysical, else None."""
    if p.omega <= 0:
        return "Spin speed must be > 0."
    if p.viscosity <= 0:
        return "Viscosity must be > 0."
    if p.density <= 0:
        return "Density must be > 0."
    if p.evaporation_rate <= 0:
        return "Evaporation rate must be > 0."
    if not (0.0 < p.solids_fraction < 1.0):
        return "Solids volume fraction must be between 0 and 1."
    return None


def compute(p: MeyerhoferInput) -> MeyerhoferResult:
    """Evaluates the Meyerhofer formula. Raises ValueError on unphysical input."""
    err = validate(p)
    if err:
        raise ValueError(err)

    h_s = (3.0 * p.viscosity * p.evaporation_rate / (2.0 * p.density * p.omega ** 2)) ** (1.0 / 3.0)
    h_f = p.solids_fraction * h_s
    return MeyerhoferResult(omega=p.omega, transition_thickness=h_s, final_thickness=h_f)


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
                    evaporation_rate_um_s: float, solids_fraction: float) -> MeyerhoferInput:
    """Converts the usual lab-bench/datasheet units into SI-based MeyerhoferInput."""
    return MeyerhoferInput(
        omega=spin_speed_rpm * cfg.RPM_TO_RAD_S,
        viscosity=viscosity_cp * cfg.CP_TO_PA_S,
        density=density_g_cm3 * cfg.G_CM3_TO_KG_M3,
        evaporation_rate=evaporation_rate_um_s * cfg.UM_S_TO_M_S,
        solids_fraction=solids_fraction,
    )
