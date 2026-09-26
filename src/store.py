"""
Presets for resins/varnishes: material properties (viscosity, density,
evaporation rate, solids fraction) that are independent of the process
parameter spin speed -- spin speed is a user choice for a given run, not a
material property, and is therefore deliberately NOT stored in a preset.

Storage format: one JSON file per preset under ui.settings.PRESETS_DIR.
Kept deliberately simple (no DB, no schema versioning) -- presets are
hand-curated files of a few kB, nothing that needs a real database.
"""

import json
import re
from dataclasses import dataclass, asdict, fields
from pathlib import Path

from .ui import settings as cfg_ui


@dataclass
class ResinPreset:
    name: str
    viscosity_cp: float
    density_g_cm3: float
    evaporation_rate_um_s: float
    concentration_mode: str            # "direct" (volume fraction) or "weight" (weight fraction)
    solids_pct: float | None = None            # used when mode == "direct" (vol.-%, 0..100)
    weight_pct: float | None = None             # used when mode == "weight" (wt.-%, 0..100)
    density_solute_g_cm3: float | None = None   # used when mode == "weight"
    density_solvent_g_cm3: float | None = None  # used when mode == "weight"
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ResinPreset":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "preset"


def _ensure_dir() -> Path:
    cfg_ui.PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return cfg_ui.PRESETS_DIR


def _scan() -> dict[str, Path]:
    """Reads all preset JSON files and maps display name -> file path."""
    directory = _ensure_dir()
    result: dict[str, Path] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result[data.get("name", path.stem)] = path
        except (json.JSONDecodeError, OSError):
            continue   # skip a broken/foreign file in the folder instead of crashing the whole listing
    return result


def list_presets() -> list[str]:
    return sorted(_scan().keys())


def load_preset(name: str) -> ResinPreset:
    paths = _scan()
    if name not in paths:
        raise ValueError(f"Preset '{name}' not found.")
    data = json.loads(paths[name].read_text(encoding="utf-8"))
    return ResinPreset.from_dict(data)


def save_preset(preset: ResinPreset) -> Path:
    directory = _ensure_dir()
    path = directory / f"{_slug(preset.name)}.json"
    path.write_text(json.dumps(preset.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def delete_preset(name: str) -> None:
    paths = _scan()
    if name in paths:
        paths[name].unlink()
