import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.model import advanced as adv, compute as m, parameters as P


def _lab(rpm=3000, e_scaling=P.E_SQRT):
    return P.LabInput(rpm=rpm, viscosity_cp=10, density_g_cm3=1.0, evaporation_um_s=0.1,
                      solids_fraction=0.10, e_scaling=e_scaling)


def test_zero_coefficients_approach_meyerhofer_closed_form():
    closed = m.thickness_at_rpm(_lab(), 3000)
    numeric = adv.thickness_nm(_lab(), k_eta=0.0, n_evap=0.0)
    rel = abs(numeric - closed) / closed
    assert rel < 0.05, rel


def test_result_insensitive_to_initial_wet_thickness():
    lab = _lab()
    p = adv.AdvancedInput(omega=lab.rpm * math.pi / 30, viscosity0=lab.viscosity_cp * 1e-3,
                          density=lab.density_g_cm3 * 1e3, evaporation_rate0=lab.evaporation_um_s * 1e-6,
                          solids_fraction0=lab.solids_fraction)
    r20 = adv.simulate(p, headroom=20)
    r40 = adv.simulate(p, headroom=40)
    assert r20.converged and r40.converged
    assert abs(r20.final_thickness_nm - r40.final_thickness_nm) / r20.final_thickness_nm < 1e-3


def test_higher_viscosity_growth_gives_thicker_film():
    lab = _lab()
    values = [adv.thickness_nm(lab, k_eta=k, n_evap=0.0) for k in (0, 2, 5, 10, 20)]
    assert all(a < b for a, b in zip(values, values[1:])), values


def test_higher_evaporation_slowdown_gives_thinner_film():
    lab = _lab()
    values = [adv.thickness_nm(lab, k_eta=0.0, n_evap=n) for n in (0, 0.5, 1, 2, 4)]
    assert all(a > b for a, b in zip(values, values[1:])), values


def test_recovers_meyerhofer_scaling_exponent_when_off():
    lab1 = _lab(rpm=1000, e_scaling=P.E_CONSTANT)
    lab2 = _lab(rpm=4000, e_scaling=P.E_CONSTANT)
    h1 = adv.thickness_nm(lab1, 0.0, 0.0)
    h2 = adv.thickness_nm(lab2, 0.0, 0.0)
    slope = math.log(h2 / h1) / math.log(4.0)
    assert math.isclose(slope, -2 / 3, abs_tol=1e-6), slope


def test_spin_curve_is_monotonically_decreasing():
    lab = _lab()
    curve = adv.spin_curve(lab, k_eta=3.0, n_evap=1.0, rpm_min=500, rpm_max=8000, points=30)
    ys = [y for _, y in curve]
    assert all(a >= b for a, b in zip(ys, ys[1:])), "thickness should decrease monotonically with rpm"


def test_rejects_unphysical_input():
    bad = adv.AdvancedInput(omega=0, viscosity0=1e-2, density=1000, evaporation_rate0=1e-7,
                            solids_fraction0=0.1)
    try:
        adv.simulate(bad)
        assert False, "expected ValueError"
    except ValueError:
        pass


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"{len(tests)} tests passed.")
