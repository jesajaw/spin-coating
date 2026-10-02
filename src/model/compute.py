"""
Meyerhofer's model for the final dry film thickness in spin coating.

Physics
-------
Emslie, Bonner and Peck (1958) solved the flow of a Newtonian, non-volatile
liquid on a rotating disk; the film thins at the rate

    dh/dt = -(2 * rho * omega^2 / (3 * eta)) * h^3

Meyerhofer (1978) added a constant solvent evaporation rate E (volume of
solvent per area and time). Written for the solvent volume per area L, with
c the solute volume fraction and nu = eta / rho the kinematic viscosity:

    dL/dt = -(1 - c) * (2 * omega^2 * h^3) / (3 * nu) - E          (Eq. 1)

Early on, outflow dominates and c stays at its initial value c0; late, the
film is so thin that flow is negligible and only evaporation is left. If the
switch between both regimes is abrupt, it happens where both terms of Eq. 1
are equal, at the wet thickness

    h_s = ( 3 * eta * E / (2 * rho * omega^2 * (1 - c0)) )^(1/3)   (Eq. 2)

After that point the solute volume per area no longer changes, so with ideal
(additive) mixing volumes the dry film is

    h_f = c0 * h_s                                                  (Eq. 3)

Eq. 2/3 give h_f ~ eta^(1/3) * E^(1/3) * omega^(-2/3). Meyerhofer measured
E ~ sqrt(omega) for spinning photoresist, which turns this into the widely
observed h_f ~ omega^(-1/2).

References
----------
[1] D. Meyerhofer, "Characteristics of resist films produced by spinning",
    J. Appl. Phys. 49, 3993-3997 (1978). doi:10.1063/1.325357
[2] A. G. Emslie, F. T. Bonner, L. G. Peck, "Flow of a viscous liquid on a
    rotating disk", J. Appl. Phys. 29, 858-862 (1958).
[3] M. Pichumani, P. Bagheri, K. M. Poduska, W. Gonzalez-Vinas, A. Yethiraj,
    "Dynamics, crystallization and structures in colloid spin coating",
    arXiv:1210.6662, Eq. 6 -- the form of Eq. 1 used here.

Assumptions/limits: Newtonian liquid, constant (spatially uniform)
evaporation rate, abrupt transition, no spin-up phase, uniform concentration
over the film depth. Viscosity in reality rises with concentration, which
this closed form ignores (Meyerhofer's own numerical solution includes it).

Works in SI units (m, s, kg, Pa*s, rad/s). Conversion from lab units happens
in from_lab(); no UI, no global state.
"""

from . import parameters as P
from .parameters import Input, LabInput, Result


def transition_thickness(p: Input) -> float:
    """Eq. 2: wet film thickness h_s [m] where flow and evaporation thin the film equally fast."""
    return (3.0 * p.viscosity * p.evaporation_rate
            / (2.0 * p.density * p.omega ** 2 * (1.0 - p.solids_fraction))) ** (1.0 / 3.0)


def compute(p: Input) -> Result:
    """Evaluates Eq. 2 and 3. Raises ValueError on unphysical input."""
    err = P.validate(p)
    if err:
        raise ValueError(err)
    h_s = transition_thickness(p)
    return Result(omega=p.omega, transition_thickness=h_s, final_thickness=p.solids_fraction * h_s)


def volume_fraction_from_weight_fraction(weight_fraction: float, density_solute: float,
                                          density_solvent: float) -> float:
    """
    Solute weight fraction w (0..1) -> volume fraction c0, from the pure-component
    densities. Assumes ideal (additive) mixing volumes, the same assumption
    as Eq. 3.
    """
    if not (0.0 < weight_fraction < 1.0):
        raise ValueError("Weight fraction must be between 0 and 1 (exclusive).")
    if density_solute <= 0 or density_solvent <= 0:
        raise ValueError("Densities must be > 0.")
    v_solute = weight_fraction / density_solute
    v_solvent = (1.0 - weight_fraction) / density_solvent
    return v_solute / (v_solute + v_solvent)


def evaporation_at(e_ref_um_s: float, rpm_ref: float, rpm: float, scaling: str) -> float:
    """Evaporation rate [um/s] at `rpm`, given E at the reference speed `rpm_ref`."""
    if scaling == P.E_SQRT:
        return e_ref_um_s * (rpm / rpm_ref) ** 0.5
    return e_ref_um_s


def from_lab_units(spin_speed_rpm: float, viscosity_cp: float, density_g_cm3: float,
                    evaporation_rate_um_s: float, solids_fraction: float) -> Input:
    """Converts the usual lab-bench/datasheet units into the SI-based Input."""
    return Input(
        omega=spin_speed_rpm * P.RPM_TO_RAD_S,
        viscosity=viscosity_cp * P.CP_TO_PA_S,
        density=density_g_cm3 * P.G_CM3_TO_KG_M3,
        evaporation_rate=evaporation_rate_um_s * P.UM_S_TO_M_S,
        solids_fraction=solids_fraction,
    )


def thickness_nm(rpm: float, viscosity_cp: float, density_g_cm3: float, e_um_s: float,
                 solids_fraction: float) -> float:
    """h_f in nm for lab-unit values, with E already given for exactly this rpm."""
    return compute(from_lab_units(rpm, viscosity_cp, density_g_cm3, e_um_s, solids_fraction)).final_thickness_nm


def thickness_at_rpm(lab: LabInput, rpm: float) -> float:
    """h_f [nm] at another spin speed, E following lab.e_scaling from the reference lab.rpm."""
    e = evaporation_at(lab.evaporation_um_s, lab.rpm, rpm, lab.e_scaling)
    return thickness_nm(rpm, lab.viscosity_cp, lab.density_g_cm3, e, lab.solids_fraction)


def spin_curve(lab: LabInput, rpm_min: float, rpm_max: float, points: int, log_spaced: bool = False) -> list[tuple[float, float]]:
    """(rpm, h_f in nm) samples for the thickness-over-rpm plot."""
    if not (0 < rpm_min < rpm_max):
        raise ValueError("Plot range needs 0 < min < max.")
    points = max(points, 2)
    if log_spaced:
        ratio = (rpm_max / rpm_min) ** (1.0 / (points - 1))
        xs = [rpm_min * ratio ** i for i in range(points)]
    else:
        xs = [rpm_min + (rpm_max - rpm_min) * i / (points - 1) for i in range(points)]
    return [(x, thickness_at_rpm(lab, x)) for x in xs]
