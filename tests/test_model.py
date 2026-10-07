"""
Model-layer tests (no UI, no display). Run:  python -m pytest tests   or   python tests/test_model.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src.model as M
from src.model import deviation as D, emslie, flack, meyerhofer, parameters as P


def vals(model_id: str, **override) -> dict:
    v = P.model_values(P.default_state(), model_id)
    v.update(override)
    return v


# -- Emslie ------------------------------------------------------------------------------------------------------

def test_emslie_closed_form_and_limit():
    v = vals(P.MODEL_EMSLIE, rpm=3000, viscosity_cp=10, density_g_cm3=1.0, h0_um=100, time_s=30)
    omega, eta, rho, h0, t = 3000 * math.pi / 30, 0.01, 1000.0, 100e-6, 30.0
    expected = h0 / math.sqrt(1 + 4 * rho * omega ** 2 * h0 ** 2 * t / (3 * eta))
    assert math.isclose(emslie.thickness_nm(v), expected * 1e9, rel_tol=1e-12)
    # thick start film -> memory of h0 is lost, h -> sqrt(3 eta / (4 rho w^2 t))
    big = emslie.thickness_nm(dict(v, h0_um=2000))
    assert math.isclose(big, emslie.long_time_limit_m(omega, eta, rho, t) * 1e9, rel_tol=0.01)


def test_emslie_thins_with_time_and_speed():
    t1 = emslie.thickness_nm(vals(P.MODEL_EMSLIE, time_s=10))
    t2 = emslie.thickness_nm(vals(P.MODEL_EMSLIE, time_s=40))
    assert t2 < t1
    assert math.isclose(math.log(t2 / t1) / math.log(4.0), -0.5, abs_tol=0.05)   # ~ t^(-1/2) once thin


# -- Meyerhofer --------------------------------------------------------------------------------------------------

def test_meyerhofer_known_value():
    # 3000 rpm, 10 cP, 1.0 g/cm3, E = 0.1 um/s, C0 = 10 %  ->  256.6 nm
    assert math.isclose(meyerhofer.thickness_nm(vals(P.MODEL_MEYERHOFER)), 256.6, rel_tol=1e-3)


def test_meyerhofer_matches_ossila_eq7_with_k_from_the_evaporation_rate():
    """Ossila Eq. 7 (h_f with E = k sqrt(w)), typed out independently of meyerhofer.py."""
    for rpm, c0 in ((1000, 0.05), (3000, 0.10), (6000, 0.30)):
        v = vals(P.MODEL_MEYERHOFER, rpm=rpm, rpm_ref=rpm, solids_fraction=c0, e_scaling=P.E_SQRT)
        w, eta, rho, e = rpm * math.pi / 30, v["viscosity_cp"] * 1e-3, v["density_g_cm3"] * 1e3, v["evaporation_um_s"] * 1e-6
        k = e / math.sqrt(w)
        eq7 = (3 / 2) ** (1 / 3) * k ** (1 / 3) * c0 * (1 - c0) ** (-1 / 3) * rho ** (-1 / 3) * eta ** (1 / 3) / math.sqrt(w)
        assert math.isclose(meyerhofer.thickness_nm(v), eq7 * 1e9, rel_tol=1e-9)


def test_meyerhofer_scaling_exponents():
    for scaling, expected in ((P.E_CONSTANT, -2 / 3), (P.E_SQRT, -0.5)):
        base = vals(P.MODEL_MEYERHOFER, e_scaling=scaling, rpm_ref=3000)
        h1 = meyerhofer.thickness_nm(dict(base, rpm=1000))
        h2 = meyerhofer.thickness_nm(dict(base, rpm=4000))
        assert math.isclose(math.log(h2 / h1) / math.log(4.0), expected, abs_tol=1e-9)


def test_validation_rejects_unphysical_input():
    for model_id, bad in ((P.MODEL_EMSLIE, dict(rpm=0)), (P.MODEL_EMSLIE, dict(h0_um=0)),
                          (P.MODEL_MEYERHOFER, dict(viscosity_cp=0)), (P.MODEL_MEYERHOFER, dict(solids_fraction=1.5)),
                          (P.MODEL_FLACK, dict(k_eta=-1)), (P.MODEL_FLACK, dict(n_evap=-1))):
        try:
            M.compute(model_id, vals(model_id, **bad))
        except ValueError:
            continue
        raise AssertionError(f"{model_id} accepted {bad}")


def test_weight_to_volume_fraction():
    c0 = P.volume_fraction_from_weight_fraction(0.10, 1.2, 0.9)
    assert math.isclose(c0, 0.0769, rel_tol=1e-3)
    state = P.default_state()
    state.update(conc_mode=P.CONC_WEIGHT, weight_pct=10.0, density_solute_g_cm3=1.2, density_solvent_g_cm3=0.9)
    P.sync_solids_fraction(state)
    assert math.isclose(state["solids_fraction"], c0)


# -- Flack-type model ----------------------------------------------------------------------------------------------

def test_flack_without_concentration_dependence_approaches_meyerhofer():
    v = vals(P.MODEL_FLACK, k_eta=0.0, n_evap=0.0)
    rel = abs(flack.thickness_nm(v) - meyerhofer.thickness_nm(v)) / meyerhofer.thickness_nm(v)
    assert rel < 0.05, rel      # closed form assumes an abrupt flow -> evaporation switch


def test_flack_monotonic_in_its_coefficients():
    up = [flack.thickness_nm(vals(P.MODEL_FLACK, k_eta=k, n_evap=0.0)) for k in (0, 2, 5, 10, 20)]
    down = [flack.thickness_nm(vals(P.MODEL_FLACK, k_eta=0.0, n_evap=n)) for n in (0, 0.5, 1, 2, 4)]
    assert all(a < b for a, b in zip(up, up[1:])), up              # stiffer viscosity -> thicker film
    assert all(a > b for a, b in zip(down, down[1:])), down        # slower evaporation -> thinner film


def test_flack_eta0_is_the_viscosity_at_the_initial_concentration():
    # The help text promises eta0 = eta(C0) (same meaning as in Meyerhofer). So at phi = C0 the flow
    # rate must not depend on k_eta, and the viscosity may only rise once the film concentrates.
    omega, eta0, rho, e0, c0, h = 314.0, 0.01, 1000.0, 1e-7, 0.1, 5e-6
    q, s = c0 * h, (1 - c0) * h
    base = flack._derivatives(q, s, omega, eta0, rho, e0, 0.0, 0.0, c0)
    for k in (2.0, 5.0, 20.0):
        assert flack._derivatives(q, s, omega, eta0, rho, e0, k, 0.0, c0) == base
    q2, s2 = 0.5 * h, 0.5 * h                                  # concentrated: phi = 0.5 > C0
    slow = flack._derivatives(q2, s2, omega, eta0, rho, e0, 5.0, 0.0, c0)
    fast = flack._derivatives(q2, s2, omega, eta0, rho, e0, 0.0, 0.0, c0)
    assert abs(slow[0]) < abs(fast[0])                         # more viscous -> slower outflow of solute


def test_flack_independent_of_internal_start_thickness():
    v = vals(P.MODEL_FLACK)
    omega, eta, rho, e = v["rpm"] * P.RPM_TO_RAD_S, v["viscosity_cp"] * 1e-3, v["density_g_cm3"] * 1e3, 1e-7
    a = flack.simulate(omega, eta, rho, e, v["solids_fraction"], 5.0, 1.0, headroom=20)
    b = flack.simulate(omega, eta, rho, e, v["solids_fraction"], 5.0, 1.0, headroom=40)
    assert a.converged and b.converged
    assert abs(a.final_thickness - b.final_thickness) / a.final_thickness < 1e-3


# -- all models: curves ---------------------------------------------------------------------------------------------

def test_spin_curves_decrease_with_rpm():
    for model_id in P.MODEL_ORDER:
        ys = [y for _, y in M.spin_curve(model_id, vals(model_id), 500, 8000, 25)]
        assert all(a >= b for a, b in zip(ys, ys[1:])), model_id


# -- deviation (every model) ------------------------------------------------------------------------------------------

def _sigmas(model_id: str, v: dict, rel: float = 0.03) -> dict:
    return {k: rel * abs(v[k]) for k in P.MODELS[model_id].keys if v[k] != 0}


def test_gauss_matches_monte_carlo_for_every_model():
    for model_id in P.MODEL_ORDER:
        v = vals(model_id)
        sig = _sigmas(model_id, v)
        g = D.propagate_analytic(model_id, v, sig)
        n = 400 if model_id == P.MODEL_FLACK else 6000
        mc = D.propagate_monte_carlo(model_id, v, sig, D.DistKind.GAUSS, n, seed=1)
        assert abs(mc.std_nm - g.sigma_nm) / g.sigma_nm < 0.12, (model_id, mc.std_nm, g.sigma_nm)
        assert abs(mc.mean_nm - g.mean_nm) / g.mean_nm < 0.02, model_id


def test_meyerhofer_gauss_equals_textbook_formula():
    # h_f ~ eta^(1/3) E^(1/3) rho^(-1/3) w^(-1/2 with E~sqrt(w))  and  1 + C0/(3 (1-C0)) for C0
    v = vals(P.MODEL_MEYERHOFER)
    sig = {"viscosity_cp": 0.5, "evaporation_um_s": 0.005, "density_g_cm3": 0.01, "rpm": 50.0, "solids_fraction": 0.004}
    c = v["solids_fraction"]
    rel = math.sqrt(sum((a * s / x) ** 2 for a, s, x in (
        (1 / 3, 0.5, v["viscosity_cp"]), (1 / 3, 0.005, v["evaporation_um_s"]), (1 / 3, 0.01, v["density_g_cm3"]),
        (0.5, 50.0, v["rpm"]), (1 + c / (3 * (1 - c)), 0.004, c))))
    got = D.propagate_analytic(P.MODEL_MEYERHOFER, v, sig)
    assert math.isclose(got.relative_sigma, rel, rel_tol=2e-3), (got.relative_sigma, rel)


def test_only_parameters_of_the_model_matter():
    v = vals(P.MODEL_MEYERHOFER)
    got = D.propagate_analytic(P.MODEL_MEYERHOFER, v, {"h0_um": 50.0, "time_s": 10.0})   # not used by this model
    assert got.sigma_nm == 0.0 and not D.has_sigma(P.MODEL_MEYERHOFER, {"h0_um": 50.0})


def test_bands_enclose_the_nominal_curve():
    for model_id in P.MODEL_ORDER:
        v = vals(model_id)
        sig = _sigmas(model_id, v, 0.05)
        curve = M.spin_curve(model_id, v, 500, 8000, 12)
        for lo, hi in D.analytic_band(model_id, v, sig, curve, max_points=None if model_id != P.MODEL_FLACK else 5):
            assert lo <= hi
        if model_id != P.MODEL_FLACK:
            band = D.monte_carlo_band(model_id, v, sig, D.DistKind.UNIFORM, [x for x, _ in curve], 300, 7)
            assert all(lo <= y <= hi for (_, y), (lo, hi) in zip(curve, band))


if __name__ == "__main__":
    tests = [(k, f) for k, f in sorted(globals().items()) if k.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"ok  {name}")
    print(f"{len(tests)} tests passed.")


def test_flack_paper_viscosity_law_is_anchored_and_close_to_k18():
    """Table I law: factor 1 at C0, monotone rising, and within ~1 % of exp(18 dphi) between 10 and 50 wt%."""
    assert flack.viscosity_factor(0.1, 0.1, 0.0, P.VISC_PAPER) == 1.0
    phis = [0.1 + 0.05 * i for i in range(9)]
    f = [flack.viscosity_factor(x, 0.1, 0.0, P.VISC_PAPER) for x in phis]
    assert all(b > a for a, b in zip(f, f[1:]))
    assert math.isclose(f[8], math.exp(18 * 0.4), rel_tol=0.02)


def test_flack_paper_law_ignores_k_eta_and_converges():
    a = flack.thickness_nm(vals(P.MODEL_FLACK, visc_law=P.VISC_PAPER, k_eta=0.0))
    b = flack.thickness_nm(vals(P.MODEL_FLACK, visc_law=P.VISC_PAPER, k_eta=30.0))
    assert a == b and a > flack.thickness_nm(vals(P.MODEL_FLACK, k_eta=0.0))

