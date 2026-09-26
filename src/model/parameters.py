"""
Physical constants, unit conversion factors, and sensible default/range
values for the input parameters of the Meyerhofer model.

Purely declarative: no logic, no imports from calc/stat/ui/resins. Both
calc.meyerhofer (lab-unit -> SI conversion) and ui.app (slider ranges,
default values) read from here -- a single source of truth for "what is a
sensible value", instead of magic numbers scattered across files.
"""

import math
from dataclasses import dataclass


# -- Unit conversion factors: lab units -> SI --------------------------------
RPM_TO_RAD_S = math.pi / 30.0      # omega [rad/s] = rpm * pi/30
CP_TO_PA_S = 1.0e-3                # 1 cP = 1 mPa*s = 1e-3 Pa*s
G_CM3_TO_KG_M3 = 1.0e3             # 1 g/cm^3 = 1000 kg/m^3
UM_S_TO_M_S = 1.0e-6               # 1 um/s = 1e-6 m/s

M_TO_NM = 1.0e9
M_TO_UM = 1.0e6

# -- Default values & slider ranges (lab units) ------------------------------
RPM_DEFAULT, RPM_MIN, RPM_MAX = 3000.0, 100.0, 12000.0
VISCOSITY_CP_DEFAULT, VISCOSITY_CP_MIN, VISCOSITY_CP_MAX = 10.0, 0.1, 5000.0
DENSITY_DEFAULT, DENSITY_MIN, DENSITY_MAX = 1.0, 0.1, 3.0
EVAP_UM_S_DEFAULT, EVAP_UM_S_MIN, EVAP_UM_S_MAX = 0.10, 0.001, 10.0

SOLIDS_PCT_DEFAULT, SOLIDS_PCT_MIN, SOLIDS_PCT_MAX = 10.0, 0.1, 99.0
WEIGHT_PCT_DEFAULT = 10.0
DENSITY_SOLUTE_DEFAULT = 1.2
DENSITY_SOLVENT_DEFAULT = 0.9


@dataclass(frozen=True)
class Input:
    """SI-unit input to the Meyerhofer formula."""
    omega: float             # angular velocity [rad/s]
    viscosity: float         # dynamic viscosity of the solution [Pa*s]
    density: float           # density of the solution [kg/m^3]
    evaporation_rate: float  # evaporation rate E [m/s] (volume / area / time)
    solids_fraction: float   # initial solute volume fraction c0, 0 < c0 < 1


@dataclass(frozen=True)
class Result:
    omega: float                  # rad/s, echoed back for display
    transition_thickness: float   # h_s: wet film thickness at the flow/evaporation transition [m]
    final_thickness: float        # h_f: final dry film thickness [m]

    @property
    def final_thickness_nm(self) -> float:
        return self.final_thickness * M_TO_NM

    @property
    def final_thickness_um(self) -> float:
        return self.final_thickness * M_TO_UM

    @property
    def transition_thickness_um(self) -> float:
        return self.transition_thickness * M_TO_UM


def validate(p: Input) -> str | None:
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
