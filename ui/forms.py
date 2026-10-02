"""
ParamForm: the parameter fields of one model, built from parameters.PARAMS.

    kind="values"  -> the parameter values (plus E(rpm) law and the way C0 is entered)
    kind="sigmas"  -> the absolute 1-sigma uncertainty of every parameter

The form keeps its own `state` dict (lab units, see parameters.default_state / default_sigmas), updates it on
every edit and calls on_change(). `set_model` rebuilds the rows for another model without losing what was typed
for parameters the models share (the state holds ALL parameters, only the model's own are shown).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.model import parameters as P
from .tex import TexLabel
from .widgets import Dropdown, NumberField
from . import style

CONC_LABELS = {P.CONC_DIRECT: "Volume fraction directly", P.CONC_WEIGHT: "From weight fraction + densities"}
CONC_LABELS_INV = {v: k for k, v in CONC_LABELS.items()}
E_LABELS_PLAIN = {P.E_CONSTANT: "Constant (independent of rpm)", P.E_SQRT: "Grows with sqrt(rpm) (Meyerhofer)"}
E_LABELS_INV = {v: k for k, v in E_LABELS_PLAIN.items()}


class ParamForm(ttk.Frame):
    def __init__(self, parent, model_id: str, state: dict, on_change=None, kind: str = "values"):
        super().__init__(parent)
        assert kind in ("values", "sigmas")
        self.kind = kind
        self.model_id = model_id
        self.state = dict(state)
        self.on_change = on_change
        self.fields: dict[str, NumberField] = {}
        self._build()

    # ------------------------------------------------------------------ public

    def set_model(self, model_id: str) -> None:
        self.model_id = model_id
        self._rebuild()

    def get_state(self) -> dict:
        return dict(self.state)

    def set_state(self, state: dict) -> None:
        self.state = dict(state)
        self._rebuild()

    # ------------------------------------------------------------------ building

    def _rebuild(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.fields = {}
        self._build()

    def _build(self) -> None:
        info = P.MODELS[self.model_id]
        for key in info.keys:
            if key == "solids_fraction" and self.kind == "values":
                self._build_concentration()
            else:
                self._add_field(key)
            if key == "evaporation_um_s" and self.kind == "values":
                self._build_e_scaling()
        if self.kind == "sigmas":
            TexLabel(self, r"Absolute $\pm$ values, 0 = exact", style_name="Note.TLabel").pack(anchor="w", pady=(4, 0))

    def _add_field(self, key: str) -> None:
        spec = P.PARAMS[key]
        if self.kind == "values":
            f = NumberField(self, spec.label_tex_for(self.model_id), self.state[key], spec.minimum, spec.maximum, spec.fmt,
                            on_change=lambda v, k=key: self._edited(k, v), log=spec.log, scale=spec.scale)
        else:
            unit = r"\mathrm{pp}" if key == "solids_fraction" else spec.unit_tex
            unit = rf" [${unit}$]" if unit else ""
            f = NumberField(self, rf"$\pm$ {spec.name} $\Delta {spec.symbol_for(self.model_id)}${unit}", self.state[key],
                            0.0, spec.sigma_max, spec.sigma_fmt, on_change=lambda v, k=key: self._edited(k, v),
                            scale=spec.scale)
        f.pack(fill="x")
        self.fields[key] = f

    def _build_e_scaling(self) -> None:
        self.d_e_scaling = Dropdown(self, r"Evaporation rate $E$ vs. spin speed", list(E_LABELS_PLAIN.values()),
                                    E_LABELS_PLAIN[self.state.get("e_scaling", P.E_SCALING_DEFAULT)],
                                    on_change=self._e_scaling_changed, width=30)
        self.d_e_scaling.pack(fill="x")

    def _build_concentration(self) -> None:
        self.d_conc = Dropdown(self, r"Solids fraction $C_0$ from", list(CONC_LABELS.values()),
                               CONC_LABELS[self.state.get("conc_mode", P.CONC_DEFAULT)],
                               on_change=self._conc_mode_changed, width=30)
        self.d_conc.pack(fill="x")
        if self.state.get("conc_mode") == P.CONC_WEIGHT:
            for key, label, lo, hi, fmt in (
                    ("weight_pct", r"Solids weight fraction $w$ [$\%$]", 0.1, 99.0, "%.2f"),
                    ("density_solute_g_cm3", r"Solute density (pure) $\rho_\mathrm{solute}$ [$\mathrm{g/cm^3}$]", 0.1, 10.0, "%.3f"),
                    ("density_solvent_g_cm3", r"Solvent density (pure) $\rho_\mathrm{solvent}$ [$\mathrm{g/cm^3}$]", 0.1, 3.0, "%.3f")):
                f = NumberField(self, label, self.state[key], lo, hi, fmt, on_change=lambda v, k=key: self._edited(k, v))
                f.pack(fill="x")
                self.fields[key] = f
            self.l_derived = TexLabel(self, "", style_name="Note.TLabel")
            self.l_derived.pack(anchor="w", pady=(0, 4))
            self._update_derived()
        else:
            self._add_field("solids_fraction")

    # ------------------------------------------------------------------ events

    def _edited(self, key: str, value: float) -> None:
        self.state[key] = value
        if key in ("weight_pct", "density_solute_g_cm3", "density_solvent_g_cm3"):
            P.sync_solids_fraction(self.state)
            self._update_derived()
        self._notify()

    def _update_derived(self) -> None:
        if not hasattr(self, "l_derived"):
            return
        try:
            c0 = P.volume_fraction_from_weight_fraction(self.state["weight_pct"] / 100.0,
                                                        self.state["density_solute_g_cm3"],
                                                        self.state["density_solvent_g_cm3"])
            self.l_derived.set_text(rf"$\rightarrow$ $C_0$ = {c0 * 100:.2f} % (volume)")
        except ValueError as e:
            self.l_derived.set_text(str(e), color=style.COLOR_ERROR)

    def _conc_mode_changed(self, label: str) -> None:
        self.state["conc_mode"] = CONC_LABELS_INV[label]
        P.sync_solids_fraction(self.state)
        self._rebuild()
        self._notify()

    def _e_scaling_changed(self, label: str) -> None:
        self.state["e_scaling"] = E_LABELS_INV[label]
        self._notify()

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()
