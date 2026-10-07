"""
Parameter presets (e.g. a resin, varnish or ink with its measured values), one JSON file per preset under settings.PRESETS_DIR.

A preset stores EVERYTHING needed to reproduce a calculation: the model, every
parameter value (lab units), how the solids fraction was entered, the E(rpm)
law, the uncertainties and a free-text note. Deliberately simple (no DB) --
presets are hand-curated files of a few kB.

JSON layout (version 2):

    {
      "version": 2,
      "name": "...", "notes": "...",
      "model": "meyerhofer",                       # emslie | meyerhofer | flack
      "values": {"rpm": 3000, "viscosity_cp": 10, "density_g_cm3": 1.0, "h0_um": 100,
                 "time_s": 30, "evaporation_um_s": 0.1, "k_eta": 5, "n_evap": 1},
      "e_scaling": "sqrt",                         # sqrt | constant
      "visc_law": "exponential",                   # exponential | flack_table1 (Flack model only)
      "concentration": {"mode": "direct", "solids_pct": 10, "weight_pct": null,
                        "density_solute_g_cm3": null, "density_solvent_g_cm3": null},
      "uncertainties": {"rpm": 0, ..., "solids_pp": 0}   # absolute 1-sigma, solids in percentage points
    }

Files of the first app version (flat: viscosity_cp, density_g_cm3,
evaporation_rate_um_s, concentration_mode, ...) are still read.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import settings
from .model import parameters as P

VERSION = 2
_VALUE_KEYS = tuple(k for k in P.PARAMS if k != "solids_fraction")   # solids go through "concentration"


def _num(x, default: float) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


@dataclass
class ParameterPreset:
    name: str
    model: str = P.MODEL_DEFAULT
    notes: str = ""
    values: dict = field(default_factory=dict)
    e_scaling: str = P.E_SCALING_DEFAULT
    visc_law: str = P.VISC_DEFAULT
    concentration: dict = field(default_factory=dict)
    uncertainties: dict = field(default_factory=dict)

    # -- conversion to/from the app's working state --------------------------

    @classmethod
    def from_state(cls, name: str, model: str, state: dict, sigmas: dict, notes: str = "") -> "ParameterPreset":
        mode = state.get("conc_mode", P.CONC_DEFAULT)
        conc = {"mode": mode, "solids_pct": None, "weight_pct": None,
                "density_solute_g_cm3": None, "density_solvent_g_cm3": None}
        if mode == P.CONC_WEIGHT:
            conc.update(weight_pct=state["weight_pct"], density_solute_g_cm3=state["density_solute_g_cm3"],
                        density_solvent_g_cm3=state["density_solvent_g_cm3"])
        else:
            conc["solids_pct"] = state["solids_fraction"] * 100.0
        unc = {k: sigmas.get(k, 0.0) for k in _VALUE_KEYS}
        unc["solids_pp"] = sigmas.get("solids_fraction", 0.0) * 100.0
        return cls(name=name, model=model, notes=notes, values={k: state[k] for k in _VALUE_KEYS},
                   e_scaling=state.get("e_scaling", P.E_SCALING_DEFAULT),
                   visc_law=state.get("visc_law", P.VISC_DEFAULT), concentration=conc, uncertainties=unc)

    def to_state(self) -> tuple[dict, dict]:
        """(state, sigmas) in the form the app/forms work with; anything missing falls back to the defaults."""
        state, sigmas = P.default_state(), P.default_sigmas()
        for k in _VALUE_KEYS:
            if k in self.values:
                state[k] = _num(self.values[k], state[k])
            if k in self.uncertainties:
                sigmas[k] = max(_num(self.uncertainties[k], 0.0), 0.0)
        if "solids_pp" in self.uncertainties:
            sigmas["solids_fraction"] = max(_num(self.uncertainties["solids_pp"], 0.0), 0.0) / 100.0
        if self.e_scaling in P.E_SCALING_MODES:
            state["e_scaling"] = self.e_scaling
        if self.visc_law in P.VISC_MODES:
            state["visc_law"] = self.visc_law
        c = self.concentration or {}
        if c.get("mode") == P.CONC_WEIGHT:
            state["conc_mode"] = P.CONC_WEIGHT
            state["weight_pct"] = _num(c.get("weight_pct"), state["weight_pct"])
            state["density_solute_g_cm3"] = _num(c.get("density_solute_g_cm3"), state["density_solute_g_cm3"])
            state["density_solvent_g_cm3"] = _num(c.get("density_solvent_g_cm3"), state["density_solvent_g_cm3"])
            P.sync_solids_fraction(state)
        else:
            state["conc_mode"] = P.CONC_DIRECT
            if c.get("solids_pct") is not None:
                state["solids_fraction"] = _num(c["solids_pct"], state["solids_fraction"] * 100.0) / 100.0
        return state, sigmas

    # -- JSON ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"version": VERSION, "name": self.name, "notes": self.notes, "model": self.model,
                "values": self.values, "e_scaling": self.e_scaling, "visc_law": self.visc_law,
                "concentration": self.concentration, "uncertainties": self.uncertainties}

    @classmethod
    def from_dict(cls, d: dict) -> "ParameterPreset":
        if "values" not in d:                       # first app version: flat layout, Meyerhofer only
            values = {"viscosity_cp": d.get("viscosity_cp"), "density_g_cm3": d.get("density_g_cm3"),
                      "evaporation_um_s": d.get("evaporation_rate_um_s")}
            conc = {"mode": d.get("concentration_mode", P.CONC_DIRECT), "solids_pct": d.get("solids_pct"),
                    "weight_pct": d.get("weight_pct"), "density_solute_g_cm3": d.get("density_solute_g_cm3"),
                    "density_solvent_g_cm3": d.get("density_solvent_g_cm3")}
            return cls(name=d.get("name", "preset"), model=P.MODEL_MEYERHOFER, notes=d.get("notes", ""),
                       values={k: v for k, v in values.items() if v is not None}, concentration=conc)
        model = d.get("model", P.MODEL_DEFAULT)
        return cls(name=d.get("name", "preset"), model=model if model in P.MODELS else P.MODEL_DEFAULT,
                   notes=d.get("notes", ""), values=dict(d.get("values", {})),
                   e_scaling=d.get("e_scaling", P.E_SCALING_DEFAULT), visc_law=d.get("visc_law", P.VISC_DEFAULT),
                   concentration=dict(d.get("concentration", {})), uncertainties=dict(d.get("uncertainties", {})))


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "preset"


def _ensure_dir() -> Path:
    settings.PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return settings.PRESETS_DIR


def _scan() -> dict[str, Path]:
    directory = _ensure_dir()
    result: dict[str, Path] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result[data.get("name", path.stem)] = path
        except (json.JSONDecodeError, OSError, AttributeError):
            continue   # skip a broken/foreign file instead of crashing the whole listing
    return result


def list_presets() -> list[str]:
    return sorted(_scan().keys())


def load_preset(name: str) -> ParameterPreset:
    paths = _scan()
    if name not in paths:
        raise ValueError(f"Preset '{name}' not found.")
    return ParameterPreset.from_dict(json.loads(paths[name].read_text(encoding="utf-8")))


def save_preset(preset: ParameterPreset) -> Path:
    directory = _ensure_dir()
    path = directory / f"{_slug(preset.name)}.json"
    path.write_text(json.dumps(preset.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def delete_preset(name: str) -> None:
    paths = _scan()
    if name in paths:
        paths[name].unlink()
