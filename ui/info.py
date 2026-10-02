"""
Two non-modal info windows, both depending on the selected model and refreshed when the model changes:

- PhysicsWindow:    the physics of the model (equations, sources) -- first version with placeholders, see texts.py
- ParametersWindow: what is practically typed into every field of the model
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.model import parameters as P
from . import style, texts
from .tex import TexLabel, TexParagraph
from .widgets import ScrollFrame


class _InfoWindow(tk.Toplevel):
    TITLE = ""
    SIZE = "700x620"

    def __init__(self, parent, model_id: str):
        super().__init__(parent)
        self.configure(bg=style.COLOR_BG)
        self.geometry(self.SIZE)
        self.minsize(480, 360)
        self.transient(parent)
        style.force_dark_titlebar(self)
        self.model_id = model_id
        self.scroll = ScrollFrame(self, padding=16)
        self.scroll.pack(fill="both", expand=True)
        self.refresh(model_id)

    # -- helpers for subclasses -------------------------------------------------

    def _clear(self) -> None:
        for child in self.scroll.body.winfo_children():
            child.destroy()
        self.scroll._wrap_labels = []

    def _heading(self, text: str, top: int = 0) -> None:
        ttk.Label(self.scroll.body, text=text, style="Heading.TLabel").pack(anchor="w", pady=(top, 4))

    def _paragraph(self, text: str, style_name: str = "Body.TLabel") -> None:
        if "$" in text:                 # text with formulas: rendered line by line (see tex.TexParagraph)
            color = style.COLOR_STATUS_TEXT if style_name == "Note.TLabel" else None
            TexParagraph(self.scroll.body, text, color=color, style_name="TLabel").pack(anchor="w", pady=(0, 8))
            return
        lbl = ttk.Label(self.scroll.body, text=text, style=style_name, justify="left", wraplength=640)
        lbl.pack(anchor="w", pady=(0, 8))
        self.scroll.track_wrap(lbl, margin=34)

    def _equation(self, tex: str, size: float = 12.5) -> None:
        TexLabel(self.scroll.body, f"${tex}$", size=size).pack(pady=(2, 10))

    def refresh(self, model_id: str) -> None:
        self.model_id = model_id
        self.title(f"{self.TITLE} -- {P.MODELS[model_id].name}")
        self._clear()
        self._fill(model_id)

    def _fill(self, model_id: str) -> None:     # pragma: no cover - implemented by subclasses
        raise NotImplementedError


class PhysicsWindow(_InfoWindow):
    TITLE = "Physics"

    def _fill(self, model_id: str) -> None:
        first_ref = True
        for kind, content in texts.PHYSICS[model_id]:
            if kind == "title":
                self._heading(content)
            elif kind == "text":
                self._paragraph(content)
            elif kind == "note":
                self._paragraph(content, "Note.TLabel")
            elif kind == "tex":
                self._equation(content)
            elif kind == "ref":
                if first_ref:
                    self._heading("Sources", top=10)
                    first_ref = False
                self._paragraph(content)


class ParametersWindow(_InfoWindow):
    TITLE = "Parameters"
    SIZE = "720x680"

    def _fill(self, model_id: str) -> None:
        info = P.MODELS[model_id]
        self._heading(f"What to enter -- {info.name}")
        self._paragraph(f"Result: {info.caption}. " + texts.uncertainty_note())
        for key in info.keys:
            spec = P.PARAMS[key]
            self._parameter_block(model_id, key, spec)
            if key == "evaporation_um_s":
                self._extra_block(model_id, "e_scaling", r"Evaporation rate vs. spin speed")
        if info.uses_concentration:
            self._extra_block(model_id, "solids_fraction_weight", r"Weight fraction route for $C_0$")

    def _parameter_block(self, model_id: str, key: str, spec: P.ParamSpec) -> None:
        body = self.scroll.body
        ttk.Separator(body).pack(fill="x", pady=(6, 8))
        TexLabel(body, spec.label_tex_for(model_id), size=11.5, color=style.COLOR).pack(anchor="w")
        default = spec.default
        shown = (spec.fmt % default)
        unit = f" {spec.unit}" if spec.unit not in ("", "-") else ""
        self._paragraph(texts.param_help(key, model_id))
        self._paragraph(f"Default: {shown}{unit}   |   slider range: {spec.fmt % spec.minimum} - "
                        f"{spec.fmt % spec.maximum}{unit}", "Note.TLabel")
        if key in texts.PARAM_FORMULA:
            self._equation(texts.PARAM_FORMULA[key], size=11)

    def _extra_block(self, model_id: str, key: str, title_tex: str) -> None:
        body = self.scroll.body
        ttk.Separator(body).pack(fill="x", pady=(6, 8))
        TexLabel(body, title_tex, size=11.5, color=style.COLOR).pack(anchor="w")
        if key == "solids_fraction_weight":
            self._paragraph("Enter the solids weight fraction w (percent) and the pure-component densities of solute "
                            "and solvent; the volume fraction is computed for you. Defaults: w = "
                            f"{P.WEIGHT_PCT_DEFAULT:g} %, solute {P.DENSITY_SOLUTE_DEFAULT:g} g/cm3, "
                            f"solvent {P.DENSITY_SOLVENT_DEFAULT:g} g/cm3.")
            self._equation(texts.PARAM_FORMULA["solids_fraction"], size=11)
        else:
            self._paragraph(texts.param_help(key, model_id))
            self._equation(texts.PARAM_FORMULA[key], size=11)
