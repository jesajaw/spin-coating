"""
Model package. One module per physical model (pure physics), one for the
statistical deviation, one for parameters/defaults:

    emslie.py       Emslie-Bonner-Peck (1958)   Newtonian, non-volatile      -> h(t)
    meyerhofer.py   Meyerhofer (1978)           + constant evaporation       -> h_f
    flack.py        Flack et al. (1984) idea    + concentration dependence   -> h_f
    deviation.py    Gaussian error propagation + Monte Carlo for ANY model
    parameters.py   units, parameter specs with default values, data shapes

This file only dispatches by model id; all functions take the LAB-unit value
dict (see parameters.model_values).
"""

from __future__ import annotations

from . import emslie, flack, meyerhofer
from . import parameters as P
from .parameters import Result

_MODULES = {P.MODEL_EMSLIE: emslie, P.MODEL_MEYERHOFER: meyerhofer, P.MODEL_FLACK: flack}


def module(model_id: str):
    return _MODULES[model_id]


def compute(model_id: str, values: dict) -> Result:
    """Nominal result with display details. Raises ValueError on unphysical input."""
    return _MODULES[model_id].compute(values)


def thickness_nm(model_id: str, values: dict) -> float:
    """Thickness [nm] only (fast path used by the deviation module). Raises ValueError."""
    return _MODULES[model_id].thickness_nm(values)


def spin_speeds(rpm_min: float, rpm_max: float, points: int, log_spaced: bool = True) -> list[float]:
    if not (0 < rpm_min < rpm_max):
        raise ValueError("Plot range needs 0 < min < max.")
    points = max(points, 2)
    if log_spaced:
        ratio = (rpm_max / rpm_min) ** (1.0 / (points - 1))
        return [rpm_min * ratio ** i for i in range(points)]
    return [rpm_min + (rpm_max - rpm_min) * i / (points - 1) for i in range(points)]


def at_rpm(values: dict, rpm: float) -> dict:
    """Copy of `values` at another spin speed; E keeps following its law from the reference speed."""
    v = dict(values)
    v["rpm"] = rpm
    return v


def spin_curve(model_id: str, values: dict, rpm_min: float, rpm_max: float, points: int,
               log_spaced: bool = True) -> list[tuple[float, float]]:
    """(rpm, thickness in nm) samples for the thickness-over-rpm plot."""
    return [(x, thickness_nm(model_id, at_rpm(values, x))) for x in spin_speeds(rpm_min, rpm_max, points, log_spaced)]
