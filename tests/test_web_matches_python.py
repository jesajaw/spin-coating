"""index.html (browser version) must give the same numbers as the Python models. Skipped if node is missing."""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.model import deviation as D, parameters as P  # noqa: E402
import src.model as M  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def _js_values() -> dict:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    logic = html[html.index("// LOGIC_START"):html.index("// LOGIC_END")]
    logic += "\nmodule.exports={thicknessAtRpm,sigmaAnalyticNm,propagateMonteCarlo};\n"
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "logic.js").write_text(logic, encoding="utf-8")
        script = (ROOT / "tests" / "web" / "logic_values.js").read_text(encoding="utf-8")
        (Path(tmp) / "run.js").write_text(script, encoding="utf-8")
        out = subprocess.run(["node", "run.js"], cwd=tmp, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _py(model_id: str, **state_override) -> dict:
    st = P.default_state()
    st.update(state_override)
    return P.model_values(st, model_id)


def test_web_thickness_matches_python():
    js = _js_values()
    cases = {
        "emslie": (P.MODEL_EMSLIE, {}),
        "mey": (P.MODEL_MEYERHOFER, {}),
        "mey_const": (P.MODEL_MEYERHOFER, {"e_scaling": "constant"}),
        "fl_exp": (P.MODEL_FLACK, {}),
        "fl_paper": (P.MODEL_FLACK, {"visc_law": P.VISC_PAPER}),
        "fl_k0n0": (P.MODEL_FLACK, {"k_eta": 0.0, "n_evap": 0.0, "e_scaling": "constant"}),
    }
    for name, (mid, ov) in cases.items():
        assert math.isclose(js[name], M.thickness_nm(mid, _py(mid, **ov)), rel_tol=1e-9), name
    v = _py(P.MODEL_MEYERHOFER, rpm=6000.0)
    v["rpm_ref"] = 3000.0
    assert math.isclose(js["mey_rpm6000"], M.thickness_nm(P.MODEL_MEYERHOFER, v), rel_tol=1e-9)


def test_web_gauss_matches_python():
    js = _js_values()
    sig = dict(rpm=100, viscosity_cp=1, density_g_cm3=0.02, evaporation_um_s=0.01, solids_fraction=0.005,
               h0_um=0, time_s=0, k_eta=0, n_evap=0)
    assert math.isclose(js["gauss_mey"], D.sigma_analytic_nm(P.MODEL_MEYERHOFER, _py(P.MODEL_MEYERHOFER), sig), rel_tol=1e-6)
    assert math.isclose(js["gauss_em"], D.sigma_analytic_nm(P.MODEL_EMSLIE, _py(P.MODEL_EMSLIE), dict(sig, h0_um=2, time_s=1)), rel_tol=1e-6)
    assert math.isclose(js["gauss_fl"], D.sigma_analytic_nm(P.MODEL_FLACK, _py(P.MODEL_FLACK), dict(sig, k_eta=2, n_evap=0.2)), rel_tol=1e-6)
