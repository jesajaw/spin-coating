"""
Declarative layer of the model package: unit conversions, model ids, the
parameter specifications (label, unit, DEFAULT VALUE, slider range, ...) and the
data shapes the physics modules exchange. No model physics, no UI.

Everything that defines "what is a parameter" lives here, so nothing is defined
twice -- the UI builds its fields from PARAMS, the deviation module takes its
clamping limits from it, the preset store takes its defaults from it.

All model functions work on a plain ``dict`` of values in LAB units (rpm, cP,
g/cm^3, um/s, um, s, fraction 0..1). The keys are the keys of PARAMS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# -- Unit conversion factors: lab units -> SI ---------------------------------
RPM_TO_RAD_S = math.pi / 30.0      # omega [rad/s] = rpm * pi/30
CP_TO_PA_S = 1.0e-3                # 1 cP = 1 mPa*s = 1e-3 Pa*s
G_CM3_TO_KG_M3 = 1.0e3             # 1 g/cm^3 = 1000 kg/m^3
UM_S_TO_M_S = 1.0e-6               # 1 um/s = 1e-6 m/s
UM_TO_M = 1.0e-6
M_TO_NM = 1.0e9
M_TO_UM = 1.0e6

# -- Models ---------------------------------------------------------------------
MODEL_EMSLIE = "emslie"
MODEL_MEYERHOFER = "meyerhofer"
MODEL_FLACK = "flack"
MODEL_ORDER = (MODEL_EMSLIE, MODEL_MEYERHOFER, MODEL_FLACK)
MODEL_DEFAULT = MODEL_MEYERHOFER


@dataclass(frozen=True)
class ModelInfo:
    id: str
    name: str                 # label in the model dropdown
    quantity: str             # plain-text name of the computed quantity
    quantity_tex: str         # same, mathtext (no surrounding $)
    caption: str              # what the number means
    keys: tuple[str, ...]     # parameters that enter this model (all of them may carry an uncertainty)
    fast: bool = True         # False = needs a numerical ODE solve per evaluation (Monte Carlo is run on demand)

    @property
    def uses_evaporation(self) -> bool:
        return "evaporation_um_s" in self.keys

    @property
    def uses_concentration(self) -> bool:
        return "solids_fraction" in self.keys


# -- How the evaporation rate E depends on the spin speed ---------------------
# Meyerhofer found E ~ sqrt(omega) experimentally (that is what turns the
# h ~ omega^(-2/3) of a constant E into the h ~ omega^(-1/2) usually observed).
E_CONSTANT = "constant"
E_SQRT = "sqrt"
E_SCALING_MODES = (E_CONSTANT, E_SQRT)
E_SCALING_DEFAULT = E_SQRT

# -- Solids fraction: how c0 is entered -----------------------------------------
CONC_DIRECT = "direct"     # volume fraction typed in directly
CONC_WEIGHT = "weight"     # weight fraction + pure-component densities
CONC_DEFAULT = CONC_DIRECT


@dataclass(frozen=True)
class ParamSpec:
    key: str
    name: str                 # plain name, e.g. "Viscosity"
    symbol: str               # mathtext without $, e.g. r"\eta_0"
    unit: str                 # plain unit text, e.g. "cP"
    unit_tex: str             # mathtext unit without $, e.g. r"\mathrm{cP}"
    default: float            # DEFAULT VALUE (in display units, see scale)
    minimum: float            # slider range
    maximum: float
    fmt: str                  # printf format for the field
    sigma_max: float          # slider range of the uncertainty field
    sigma_fmt: str
    log: bool = False         # logarithmic slider
    scale: float = 1.0        # display value * scale = value in lab units (percent fields: 0.01)
    hard_min: float | None = None   # physical limits used when Monte Carlo draws would leave them
    hard_max: float | None = None

    @property
    def label_tex(self) -> str:
        unit = rf" [${self.unit_tex}$]" if self.unit_tex else ""
        return rf"{self.name} ${self.symbol}${unit}"

    @property
    def label_plain(self) -> str:
        return f"{self.name} [{self.unit}]" if self.unit else self.name

    @property
    def sigma_label_tex(self) -> str:
        unit = rf" [${self.unit_tex}$]" if self.unit_tex else ""
        return rf"$\pm$ ${self.symbol}${unit}"


PARAMS: dict[str, ParamSpec] = {p.key: p for p in (
    ParamSpec("rpm", "Spin speed", r"\omega", "rpm", r"\mathrm{rpm}",
              default=3000.0, minimum=100.0, maximum=12000.0, fmt="%.0f",
              sigma_max=2000.0, sigma_fmt="%.1f", hard_min=1e-6),
    ParamSpec("viscosity_cp", "Viscosity", r"\eta", "cP", r"\mathrm{cP}",
              default=10.0, minimum=0.1, maximum=5000.0, fmt="%.2f",
              sigma_max=1000.0, sigma_fmt="%.2f", hard_min=1e-9),
    ParamSpec("density_g_cm3", "Solution density", r"\rho", "g/cm3", r"\mathrm{g/cm^3}",
              default=1.0, minimum=0.1, maximum=3.0, fmt="%.3f",
              sigma_max=1.0, sigma_fmt="%.3f", hard_min=1e-9),
    ParamSpec("h0_um", "Initial film thickness", r"h_0", "um", r"\mu\mathrm{m}",
              default=100.0, minimum=1.0, maximum=2000.0, fmt="%.1f",
              sigma_max=500.0, sigma_fmt="%.1f", log=True, hard_min=1e-6),
    ParamSpec("time_s", "Spin time", r"t", "s", r"\mathrm{s}",
              default=30.0, minimum=0.1, maximum=600.0, fmt="%.1f",
              sigma_max=60.0, sigma_fmt="%.2f", log=True, hard_min=0.0),
    ParamSpec("evaporation_um_s", "Evaporation rate", r"E", "um/s", r"\mu\mathrm{m/s}",
              default=0.10, minimum=0.001, maximum=10.0, fmt="%.3f",
              sigma_max=5.0, sigma_fmt="%.4f", log=True, hard_min=1e-9),
    ParamSpec("solids_fraction", "Solids volume fraction", r"C_0", "%", r"\%",
              default=10.0, minimum=0.1, maximum=99.0, fmt="%.2f",
              sigma_max=20.0, sigma_fmt="%.3f", scale=0.01, hard_min=1e-6, hard_max=0.999999),
    ParamSpec("k_eta", "Viscosity growth", r"k_\eta", "", "",
              default=5.0, minimum=0.0, maximum=30.0, fmt="%.2f",
              sigma_max=10.0, sigma_fmt="%.2f", hard_min=0.0),
    ParamSpec("n_evap", "Evaporation slowdown", r"n", "", "",
              default=1.0, minimum=0.0, maximum=6.0, fmt="%.2f",
              sigma_max=3.0, sigma_fmt="%.2f", hard_min=0.0),
)}

# Inputs that only exist to derive C_0 from a weight fraction; they carry no uncertainty of their own.
WEIGHT_PCT_DEFAULT = 10.0
DENSITY_SOLUTE_DEFAULT = 1.2
DENSITY_SOLVENT_DEFAULT = 0.9

COMMON_KEYS = ("rpm", "viscosity_cp", "density_g_cm3")

MODELS: dict[str, ModelInfo] = {m.id: m for m in (
    ModelInfo(MODEL_EMSLIE, "Emslie-Bonner-Peck (1958)", "h(t)", "h(t)",
              "wet film thickness after the given spin time (no evaporation)",
              COMMON_KEYS + ("h0_um", "time_s")),
    ModelInfo(MODEL_MEYERHOFER, "Meyerhofer (1978)", "h_f", r"h_\mathrm{f}",
              "final dry film thickness",
              COMMON_KEYS + ("evaporation_um_s", "solids_fraction")),
    ModelInfo(MODEL_FLACK, "Flack et al. (1984), depth-averaged", "h_f", r"h_\mathrm{f}",
              "final dry film thickness, concentration-dependent viscosity and evaporation",
              COMMON_KEYS + ("evaporation_um_s", "solids_fraction", "k_eta", "n_evap"), fast=False),
)}


def model_names() -> list[str]:
    return [MODELS[m].name for m in MODEL_ORDER]


def model_id_from_name(name: str) -> str:
    for info in MODELS.values():
        if info.name == name:
            return info.id
    return MODEL_DEFAULT


def default_state() -> dict:
    """
    Complete input state in LAB units: every parameter of every model (so switching the model
    keeps what was typed), plus the way the solids fraction is entered.
    `solids_fraction` is a fraction (0..1); `weight_pct` is in percent.
    """
    state = {k: spec.default * spec.scale for k, spec in PARAMS.items()}
    state.update(e_scaling=E_SCALING_DEFAULT, conc_mode=CONC_DEFAULT, weight_pct=WEIGHT_PCT_DEFAULT,
                 density_solute_g_cm3=DENSITY_SOLUTE_DEFAULT, density_solvent_g_cm3=DENSITY_SOLVENT_DEFAULT)
    return state


def default_sigmas() -> dict:
    """Absolute 1-sigma uncertainties (lab units) of every parameter; 0 = exact."""
    return {k: 0.0 for k in PARAMS}


def model_values(state: dict, model_id: str) -> dict:
    """The value dict a physics module expects: only the model's own parameters, plus E-scaling info."""
    v = {k: float(state[k]) for k in MODELS[model_id].keys}
    v["e_scaling"] = state.get("e_scaling", E_SCALING_DEFAULT)
    v["rpm_ref"] = v["rpm"]      # the spin speed typed in is the speed E is specified at
    return v


# -- Small unit/definition helpers shared by the physics modules ----------------

def evaporation_at(e_ref_um_s: float, rpm_ref: float, rpm: float, scaling: str) -> float:
    """Evaporation rate [um/s] at `rpm`, given E at the reference speed `rpm_ref`."""
    if scaling == E_SQRT and rpm_ref > 0:
        return e_ref_um_s * (rpm / rpm_ref) ** 0.5
    return e_ref_um_s


def volume_fraction_from_weight_fraction(weight_fraction: float, density_solute: float,
                                         density_solvent: float) -> float:
    """
    Solute weight fraction w (0..1) -> volume fraction C0, from the pure-component densities.
    Assumes ideal (additive) mixing volumes.
    """
    if not (0.0 < weight_fraction < 1.0):
        raise ValueError("Weight fraction must be between 0 and 1 (exclusive).")
    if density_solute <= 0 or density_solvent <= 0:
        raise ValueError("Densities must be > 0.")
    v_solute = weight_fraction / density_solute
    v_solvent = (1.0 - weight_fraction) / density_solvent
    return v_solute / (v_solute + v_solvent)


def sync_solids_fraction(state: dict) -> None:
    """If C0 is entered via weight fraction, recompute state['solids_fraction'] from it (keeps the old value on bad input)."""
    if state.get("conc_mode") == CONC_WEIGHT:
        try:
            state["solids_fraction"] = volume_fraction_from_weight_fraction(
                state["weight_pct"] / 100.0, state["density_solute_g_cm3"], state["density_solvent_g_cm3"])
        except ValueError:
            pass


@dataclass(frozen=True)
class Result:
    """Nominal result of a model, ready for display."""
    thickness_nm: float
    details: tuple[str, ...] = ()       # lines (mathtext allowed) shown below the big number

    @property
    def thickness_um(self) -> float:
        return self.thickness_nm / 1000.0
