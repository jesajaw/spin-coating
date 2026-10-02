r"""
Statistical deviation on top of the nominal result -- for EVERY model.

Every parameter in parameters.PARAMS can carry an uncertainty (absolute 1-sigma,
lab units, 0 = exact). The `sig` argument below is a dict {parameter key: sigma}.
Two independent, selectable methods, both generic (they only call model.thickness_nm):

1. Gaussian (linearised) error propagation
       sigma_h^2 = sum_i ( dh/dx_i * sigma_i )^2
   for independent, normally distributed inputs. The partial derivatives are
   taken numerically (central differences), so this works unchanged for the
   closed-form models and for the ODE model. Only first order.

2. Monte Carlo
   Every parameter is drawn from its own distribution (normal, uniform or
   triangular) and the draws are propagated through the full, non-linear model.
   Also gives percentiles. A fixed seed keeps results reproducible, so unrelated
   re-computes do not make the numbers jitter.

`spread` of every parameter means, depending on the kind:
   GAUSS -> standard deviation, UNIFORM -> half-width, TRIANGULAR -> half-width
   (symmetric, mode = value). The same number therefore gives different standard
   deviations (uniform: spread/sqrt(3), triangular: spread/sqrt(6)).

Both methods only know model.* / model.parameters, no UI.

Note: this covers only the entered parameter uncertainties, not the systematic
error of the model itself.

Caveat on the Monte Carlo mean/std: the thickness depends on rpm, eta, E, rho
through power laws. If a parameter's sigma is a large fraction of its value,
Gaussian sampling occasionally draws it close to zero and the power law blows
the result up -- a few extreme draws can then dominate mean and (even more) std,
while the median and P05/P95 stay sensible. This is a property of propagating a
heavy-tailed input through the model, not a bug; for relative uncertainties above
roughly 20-30 % read the percentiles instead.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

from . import thickness_nm
from . import parameters as P

GRADIENT_REL_STEP = 1e-3     # relative step of the numerical derivatives
GRADIENT_ABS_STEP = 1e-3     # used instead when the nominal value is 0


def active_keys(model_id: str, sig: dict) -> list[str]:
    """Parameters of this model that actually carry an uncertainty."""
    return [k for k in P.MODELS[model_id].keys if sig.get(k, 0.0) > 0]


def has_sigma(model_id: str, sig: dict) -> bool:
    return bool(active_keys(model_id, sig))


def _clamp(key: str, x: float) -> float:
    spec = P.PARAMS[key]
    if spec.hard_min is not None:
        x = max(x, spec.hard_min)
    if spec.hard_max is not None:
        x = min(x, spec.hard_max)
    return x


# ============================================================================
# 1. Analytic (linearised Gaussian) error propagation
# ============================================================================

@dataclass(frozen=True)
class AnalyticResult:
    mean_nm: float
    sigma_nm: float
    relative_sigma: float


def _partial(model_id: str, values: dict, key: str) -> float:
    """dh/dx for parameter `key` [nm per lab unit], central difference (one-sided at a physical limit)."""
    x = values[key]
    step = abs(x) * GRADIENT_REL_STEP if x != 0 else GRADIENT_ABS_STEP
    lo, hi = _clamp(key, x - step), _clamp(key, x + step)
    if hi <= lo:
        return 0.0
    v_lo, v_hi = dict(values, **{key: lo}), dict(values, **{key: hi})
    return (thickness_nm(model_id, v_hi) - thickness_nm(model_id, v_lo)) / (hi - lo)


def sigma_analytic_nm(model_id: str, values: dict, sig: dict) -> float:
    """1-sigma of the thickness [nm] at the spin speed in `values['rpm']`."""
    total = 0.0
    for k in active_keys(model_id, sig):
        total += (_partial(model_id, values, k) * sig[k]) ** 2
    return math.sqrt(total)


def propagate_analytic(model_id: str, values: dict, sig: dict) -> AnalyticResult:
    h = thickness_nm(model_id, values)
    s = sigma_analytic_nm(model_id, values, sig)
    return AnalyticResult(mean_nm=h, sigma_nm=s, relative_sigma=s / h if h else 0.0)


def _interp_log_x(xs: list[float], ys: list[float], x: float) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (math.log(x) - math.log(xs[i - 1])) / (math.log(xs[i]) - math.log(xs[i - 1]))
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return ys[-1]


def analytic_band(model_id: str, values: dict, sig: dict, curve: list[tuple[float, float]],
                  max_points: int | None = None) -> list[tuple[float, float]]:
    """
    (lower, upper) = h -/+ 1 sigma for every (rpm, h) point of a spin curve.
    With `max_points` the relative sigma is only evaluated on that many points and interpolated
    (log x) -- used for the ODE model, where every evaluation is a numerical solve.
    """
    n = len(curve)
    if max_points and max_points < n:
        idx = sorted({round(i * (n - 1) / (max_points - 1)) for i in range(max_points)})
        cx = [curve[i][0] for i in idx]
        cr = []
        for i in idx:
            x, h = curve[i]
            cr.append(sigma_analytic_nm(model_id, dict(values, rpm=x), sig) / h if h else 0.0)
        rel = [_interp_log_x(cx, cr, x) for x, _ in curve]
    else:
        rel = [sigma_analytic_nm(model_id, dict(values, rpm=x), sig) / h if h else 0.0 for x, h in curve]
    return [(h - h * r, h + h * r) for (_, h), r in zip(curve, rel)]


# ============================================================================
# 2. Monte Carlo simulation
# ============================================================================

class DistKind(str, Enum):
    GAUSS = "Normal distribution (Gauss)"
    UNIFORM = "Uniform distribution"
    TRIANGULAR = "Triangular distribution"


@dataclass(frozen=True)
class MonteCarloResult:
    n: int                 # number of valid samples
    mean_nm: float
    std_nm: float
    p05_nm: float
    p50_nm: float
    p95_nm: float


def _unit_draws(kind: DistKind, n: int, seed: int, dim: int) -> list[tuple[float, ...]]:
    """n samples of `dim` unit-scale draws; scaled by the spreads later."""
    rng = random.Random(seed)
    if kind == DistKind.GAUSS:
        draw = lambda: rng.gauss(0.0, 1.0)
    elif kind == DistKind.UNIFORM:
        draw = lambda: rng.uniform(-1.0, 1.0)
    else:
        draw = lambda: rng.triangular(-1.0, 1.0, 0.0)
    return [tuple(draw() for _ in range(dim)) for _ in range(n)]


def _perturbed(model_id: str, values: dict, sig: dict, u: tuple[float, ...]) -> dict:
    """Applies one draw u (one number per model parameter, in model key order) to the value dict."""
    v = dict(values)
    for k, ui in zip(P.MODELS[model_id].keys, u):
        s = sig.get(k, 0.0)
        if s > 0:
            v[k] = _clamp(k, values[k] + s * ui)
    return v


def _sample(model_id: str, values: dict, sig: dict, u: tuple[float, ...]) -> float | None:
    try:
        return thickness_nm(model_id, _perturbed(model_id, values, sig, u))
    except ValueError:
        return None      # e.g. ODE did not converge for an extreme draw: drop the sample


def _percentile(sorted_samples: list[float], p: float) -> float:
    return sorted_samples[min(int(p * len(sorted_samples)), len(sorted_samples) - 1)]


def _draws(model_id: str, kind: DistKind, n: int, seed: int) -> list[tuple[float, ...]]:
    if n < 2:
        raise ValueError("Monte Carlo needs at least 2 samples.")
    return _unit_draws(kind, n, seed, len(P.MODELS[model_id].keys))


def propagate_monte_carlo(model_id: str, values: dict, sig: dict, kind: DistKind, n: int,
                          seed: int) -> MonteCarloResult:
    samples = [s for s in (_sample(model_id, values, sig, u) for u in _draws(model_id, kind, n, seed))
               if s is not None]
    if len(samples) < 2:
        raise ValueError("Monte Carlo produced fewer than 2 valid samples -- check the uncertainties.")
    samples.sort()
    m = len(samples)
    mean = sum(samples) / m
    std = math.sqrt(sum((x - mean) ** 2 for x in samples) / (m - 1))
    return MonteCarloResult(n=m, mean_nm=mean, std_nm=std, p05_nm=_percentile(samples, 0.05),
                            p50_nm=_percentile(samples, 0.50), p95_nm=_percentile(samples, 0.95))


def monte_carlo_band(model_id: str, values: dict, sig: dict, kind: DistKind, rpms: list[float], n: int,
                     seed: int) -> list[tuple[float, float]]:
    """(P05, P95) of the thickness at every rpm; the same draws are reused for all points."""
    draws = _draws(model_id, kind, n, seed)
    out = []
    for rpm in rpms:
        v = dict(values, rpm=rpm)
        samples = sorted(s for s in (_sample(model_id, v, sig, u) for u in draws) if s is not None)
        if not samples:
            raise ValueError("Monte Carlo produced no valid samples -- check the uncertainties.")
        out.append((_percentile(samples, 0.05), _percentile(samples, 0.95)))
    return out


def interpolate_band(coarse_rpms: list[float], band: list[tuple[float, float]],
                     rpms: list[float]) -> list[tuple[float, float]]:
    """Interpolates a band computed on few spin speeds onto all plot points (log x)."""
    lo = [b[0] for b in band]
    hi = [b[1] for b in band]
    return [(_interp_log_x(coarse_rpms, lo, x), _interp_log_x(coarse_rpms, hi, x)) for x in rpms]
