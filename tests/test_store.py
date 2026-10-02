"""Preset store tests: round trip of everything a preset holds, migration of the old flat format."""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import settings, store
from src.model import parameters as P


def _with_temp_dir(fn):
    def wrapper():
        old = settings.PRESETS_DIR
        with tempfile.TemporaryDirectory() as tmp:
            settings.PRESETS_DIR = Path(tmp)
            try:
                fn()
            finally:
                settings.PRESETS_DIR = old
    wrapper.__name__ = fn.__name__
    return wrapper


@_with_temp_dir
def test_round_trip_keeps_model_values_and_uncertainties():
    state, sigmas = P.default_state(), P.default_sigmas()
    state.update(rpm=4200.0, viscosity_cp=55.5, k_eta=7.0, e_scaling=P.E_CONSTANT, solids_fraction=0.17)
    sigmas.update(rpm=40.0, viscosity_cp=2.5, solids_fraction=0.005)
    store.save_preset(store.ResinPreset.from_state("Test resin", P.MODEL_FLACK, state, sigmas, "note"))
    assert "Test resin" in store.list_presets()
    p = store.load_preset("Test resin")
    st2, sg2 = p.to_state()
    assert p.model == P.MODEL_FLACK and p.notes == "note"
    assert st2["rpm"] == 4200.0 and st2["k_eta"] == 7.0 and st2["e_scaling"] == P.E_CONSTANT
    assert math.isclose(st2["solids_fraction"], 0.17) and math.isclose(sg2["solids_fraction"], 0.005)
    assert sg2["viscosity_cp"] == 2.5


@_with_temp_dir
def test_weight_mode_round_trip():
    state = P.default_state()
    state.update(conc_mode=P.CONC_WEIGHT, weight_pct=25.0, density_solute_g_cm3=1.3, density_solvent_g_cm3=0.85)
    P.sync_solids_fraction(state)
    store.save_preset(store.ResinPreset.from_state("w", P.MODEL_MEYERHOFER, state, P.default_sigmas()))
    st2, _ = store.load_preset("w").to_state()
    assert st2["conc_mode"] == P.CONC_WEIGHT and st2["weight_pct"] == 25.0
    assert math.isclose(st2["solids_fraction"], state["solids_fraction"])


@_with_temp_dir
def test_old_flat_format_is_still_read_and_broken_files_are_skipped():
    old = {"name": "Old", "viscosity_cp": 120.0, "density_g_cm3": 1.05, "evaporation_rate_um_s": 0.05,
           "concentration_mode": "weight", "solids_pct": None, "weight_pct": 25.0,
           "density_solute_g_cm3": 1.2, "density_solvent_g_cm3": 0.9, "notes": "x"}
    (settings.PRESETS_DIR / "old.json").write_text(json.dumps(old), encoding="utf-8")
    (settings.PRESETS_DIR / "broken.json").write_text("{not json", encoding="utf-8")
    p = store.load_preset("Old")
    st, _ = p.to_state()
    assert p.model == P.MODEL_MEYERHOFER and st["viscosity_cp"] == 120.0 and st["conc_mode"] == P.CONC_WEIGHT
    assert store.list_presets() == ["Old"]


def test_shipped_example_presets_load():
    for name in store.list_presets():
        state, sigmas = store.load_preset(name).to_state()
        assert 0 < state["solids_fraction"] < 1, name


@_with_temp_dir
def test_delete():
    store.save_preset(store.ResinPreset.from_state("gone", P.MODEL_EMSLIE, P.default_state(), P.default_sigmas()))
    store.delete_preset("gone")
    assert store.list_presets() == []


if __name__ == "__main__":
    tests = [(k, f) for k, f in sorted(globals().items()) if k.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"ok  {name}")
    print(f"{len(tests)} tests passed.")
