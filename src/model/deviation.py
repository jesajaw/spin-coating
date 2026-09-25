"""
Optional statistical deviation on top of the purely physical Meyerhofer
result. Two independent, independently selectable methods:

1. Analytic Gaussian error propagation (propagate_analytic)
   h_f is a pure power-law product of its inputs:
       h_f = c0^1 * eta^(1/3) * E^(1/3) * rho^(-1/3) * omega^(-2/3)
   For a power-law product y = prod(x_i^a_i), linearized (Gaussian) error
   propagation with independent, normally distributed inputs gives:
       (sigma_y / y)^2 = sum_i (a_i * sigma_xi / xi)^2
   Fast, closed form, no random sampling -- but only a first-order
   linearization around the nominal value.

2. Monte Carlo simulation (propagate_monte_carlo)
   Each input parameter gets its own distribution (Normal/Gaussian,
   uniform, or triangular), and N draws are propagated through the full
   (non-linearized) model. More robust for large uncertainties, and
   additionally yields percentiles instead of just a single sigma value.

Both functions only know calc.meyerhofer, no UI.
"""

import math
import random
from dataclasses import dataclass
from enum import Enum

import meyerhofer as model


# ============================================================================
# 1. Analytic Gaussian error propagation
# ============================================================================

@dataclass(frozen=True)
class ParamUncertainty:
    """An input parameter with an optional absolute 1-sigma uncertainty."""
    value: float
    sigma: float = 0.0   # 0 = no spread for this parameter

    def relative_sigma(self) -> float:
        if self.value == 0 or self.sigma == 0:
            return 0.0
        return abs(self.sigma / self.value)


@dataclass(frozen=True)
class InputUncertainties:
    rpm: ParamUncertainty
    viscosity_cp: ParamUncertainty
    density_g_cm3: ParamUncertainty
    evaporation_rate_um_s: ParamUncertainty
    solids_fraction: ParamUncertainty   # value & sigma as a fraction (0..1), not percent


@dataclass(frozen=True)
class AnalyticResult:
    mean_nm: float
    sigma_nm: float
    relative_sigma: float


def propagate_analytic(u: InputUncertainties, nominal_nm: float) -> AnalyticResult:
    # (exponent, relative uncertainty) for each factor in the power-law product h_f.
    # omega is proportional to rpm -> same relative uncertainty.
    terms = [
        (1.0,     u.solids_fraction.relative_sigma()),
        (1.0/3.0, u.viscosity_cp.relative_sigma()),
        (1.0/3.0, u.evaporation_rate_um_s.relative_sigma()),
        (1.0/3.0, u.density_g_cm3.relative_sigma()),
        (2.0/3.0, u.rpm.relative_sigma()),
    ]
    relative_sigma = math.sqrt(sum((a * rel) ** 2 for a, rel in terms))
    sigma_nm = nominal_nm * relative_sigma
    return AnalyticResult(mean_nm=nominal_nm, sigma_nm=sigma_nm, relative_sigma=relative_sigma)


# ============================================================================
# 2. Monte Carlo simulation
# ============================================================================

class DistKind(str, Enum):
    GAUSS = "Normal distribution (Gauss)"
    UNIFORM = "Uniform distribution"
    TRIANGULAR = "Triangular distribution"


@dataclass(frozen=True)
class ScatterParam:
    """
    An input parameter for Monte Carlo sampling. The meaning of `spread`
    depends on `kind`:
        GAUSS      -> standard deviation
        UNIFORM    -> half-width of [value-spread, value+spread]
        TRIANGULAR -> half-width, mode = value (symmetric triangle)
    spread <= 0 -> parameter is not sampled (fixed nominal value).
    """
    value: float
    kind: DistKind
    spread: float = 0.0

    def sample(self) -> float:
        if self.spread <= 0:
            return self.value
        if self.kind == DistKind.GAUSS:
            return random.gauss(self.value, self.spread)
        if self.kind == DistKind.UNIFORM:
            return random.uniform(self.value - self.spread, self.value + self.spread)
        return random.triangular(self.value - self.spread, self.value + self.spread, self.value)


@dataclass(frozen=True)
class ScatterInputs:
    rpm: ScatterParam
    viscosity_cp: ScatterParam
    density_g_cm3: ScatterParam
    evaporation_rate_um_s: ScatterParam
    solids_fraction: ScatterParam


@dataclass(frozen=True)
class MonteCarloResult:
    n: int              # number of valid samples actually used (< n_requested if unphysical draws were dropped)
    mean_nm: float
    std_nm: float
    p05_nm: float
    p50_nm: float
    p95_nm: float


def propagate_monte_carlo(s: ScatterInputs, n: int) -> MonteCarloResult:
    samples = []
    for _ in range(n):
        rpm = max(s.rpm.sample(), 1e-6)
        eta = max(s.viscosity_cp.sample(), 1e-9)
        rho = max(s.density_g_cm3.sample(), 1e-9)
        evap = max(s.evaporation_rate_um_s.sample(), 1e-9)
        c0 = min(max(s.solids_fraction.sample(), 1e-6), 0.999999)
        try:
            result = model.compute(model.from_lab_units(rpm, eta, rho, evap, c0))
        except ValueError:
            continue   # unphysical draw (should rarely happen given the clamps above), discard
        samples.append(result.final_thickness_nm)

    if not samples:
        raise ValueError("Monte Carlo simulation produced no valid samples -- check the parameters.")

    samples.sort()
    n_valid = len(samples)
    mean = sum(samples) / n_valid
    variance = sum((x - mean) ** 2 for x in samples) / max(n_valid - 1, 1)
    std = math.sqrt(variance)

    def percentile(p: float) -> float:
        idx = min(int(p * n_valid), n_valid - 1)
        return samples[idx]

    return MonteCarloResult(
        n=n_valid, mean_nm=mean, std_nm=std,
        p05_nm=percentile(0.05), p50_nm=percentile(0.50), p95_nm=percentile(0.95),
    )
