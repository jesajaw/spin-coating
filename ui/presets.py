"""
Parameter-presets window. A preset stores everything (model, all parameter values, E(rpm) law, how C0 was entered,
uncertainties, note) as JSON via src/store.py.

Left:  list of saved presets (click = load into the editor), Delete.
Right: editor with name, note, model and the same parameter forms as the main window (tabs "Values" and
       "Uncertainties"). Buttons: Save, Apply to main window, Take over settings from main window.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src import store
from src.model import parameters as P
from . import dialogs, style
from .forms import ParamForm
from .tex import TexLabel
from .widgets import Dropdown, ScrollFrame


class PresetsWindow(tk.Toplevel):
    def __init__(self, parent, get_current, apply_preset):
        """
        get_current() -> (model_id, state, sigmas) of the main window
        apply_preset(model_id, state, sigmas) puts a preset into the main window
        """
        super().__init__(parent)
        self.configure(bg=style.COLOR_BG)
        self.title("Parameter Presets")
        self.geometry("920x700")
        self.minsize(820, 560)
        self.transient(parent)
        style.force_dark_titlebar(self)
        self._get_current, self._apply = get_current, apply_preset

        outer = ttk.Frame(self, padding=style.LAYOUT.outer_padding)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        # -- left: list ------------------------------------------------------
        left = ttk.LabelFrame(outer, text="Saved presets", padding=10)
        left.grid(row=0, column=0, sticky="ns", padx=(0, style.LAYOUT.col_gap))
        self.listbox = tk.Listbox(left, width=30, height=18, exportselection=False, bg=style.COLOR_BG_LIGHT,
                                  fg=style.COLOR_FG, selectbackground=style.COLOR_DARK,
                                  selectforeground=style.COLOR_FG, highlightthickness=1,
                                  highlightbackground=style.COLOR_DARK, relief="flat", font=style.FONT_NORMAL)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        ttk.Button(left, text="Delete", command=self._on_delete).pack(anchor="w", pady=(8, 0))

        # -- right: editor ---------------------------------------------------
        right = ttk.LabelFrame(outer, text="Preset", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(3, weight=1)
        right.columnconfigure(0, weight=1)

        head = ttk.Frame(right)
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(0, weight=1)
        head.columnconfigure(1, weight=1)
        name_box = ttk.Frame(head)
        name_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(name_box, text="Name", style="FieldLabel.TLabel").pack(anchor="w")
        self.e_name = ttk.Entry(name_box)
        self.e_name.pack(fill="x", pady=(2, 6))
        note_box = ttk.Frame(head)
        note_box.grid(row=0, column=1, sticky="ew")
        ttk.Label(note_box, text="Note (e.g. source / calibration date)", style="FieldLabel.TLabel").pack(anchor="w")
        self.e_notes = ttk.Entry(note_box)
        self.e_notes.pack(fill="x", pady=(2, 6))

        model_id, state, sigmas = get_current()
        self.model_id = model_id
        self.d_model = Dropdown(right, "Model", P.model_names(), P.MODELS[model_id].name,
                                on_change=self._on_model_change, width=40)
        self.d_model.grid(row=1, column=0, sticky="w")

        ttk.Label(right, text="Everything below is saved with the preset. 'Apply to main window' loads it "
                              "into the calculator.", style="Help.TLabel", wraplength=560, justify="left"
                  ).grid(row=2, column=0, sticky="w", pady=(0, 6))

        self.tabs = ttk.Notebook(right)
        self.tabs.grid(row=3, column=0, sticky="nsew")
        self._values_scroll = ScrollFrame(self.tabs, padding=10)
        self._sigmas_scroll = ScrollFrame(self.tabs, padding=10)
        self.tabs.add(self._values_scroll, text="Values")
        self.tabs.add(self._sigmas_scroll, text="Uncertainties")
        self.f_values = ParamForm(self._values_scroll.body, model_id, state, kind="values")
        self.f_values.pack(fill="x")
        self.f_sigmas = ParamForm(self._sigmas_scroll.body, model_id, sigmas, kind="sigmas")
        self.f_sigmas.pack(fill="x")

        buttons = ttk.Frame(right)
        buttons.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Save", style="Accent.TButton", command=self._on_save).pack(side="left")
        ttk.Button(buttons, text="Apply to main window", command=self._on_apply).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Take over settings from main window", command=self._on_take_over
                   ).pack(side="left", padx=(8, 0))
        self.l_status = TexLabel(right, "", style_name="ResultSmall.TLabel")
        self.l_status.grid(row=5, column=0, sticky="w", pady=(8, 0))

        self._refresh_list()

    # ------------------------------------------------------------------ list

    def _refresh_list(self, select: str | None = None) -> None:
        names = store.list_presets()
        self.listbox.delete(0, "end")
        self.listbox.insert("end", *names)
        if select in names:
            self.listbox.selection_set(names.index(select))

    def _selected_name(self) -> str | None:
        sel = self.listbox.curselection()
        return self.listbox.get(sel[0]) if sel else None

    def _status(self, text: str, error: bool = False) -> None:
        self.l_status.set_text(text, color=style.COLOR_ERROR if error else style.COLOR_STATUS_TEXT)

    # ------------------------------------------------------------------ editor <-> preset

    def _load_into_editor(self, model_id: str, state: dict, sigmas: dict, name: str = "", notes: str = "") -> None:
        self.model_id = model_id
        self.d_model.set(P.MODELS[model_id].name)
        self.f_values.model_id = model_id
        self.f_values.set_state(state)
        self.f_sigmas.model_id = model_id
        self.f_sigmas.set_state(sigmas)
        for entry, text in ((self.e_name, name), (self.e_notes, notes)):
            entry.delete(0, "end")
            entry.insert(0, text)

    def _on_select(self, _event=None) -> None:
        name = self._selected_name()
        if not name:
            return
        try:
            preset = store.load_preset(name)
        except ValueError as e:
            self._status(str(e), error=True)
            return
        state, sigmas = preset.to_state()
        self._load_into_editor(preset.model, state, sigmas, preset.name, preset.notes)
        self._status(f"'{preset.name}' loaded into the editor.")

    def _on_model_change(self, name: str) -> None:
        self.model_id = P.model_id_from_name(name)
        self.f_values.set_model(self.model_id)
        self.f_sigmas.set_model(self.model_id)

    def _on_save(self) -> None:
        name = self.e_name.get().strip()
        if not name:
            self._status("Please enter a name for the preset.", error=True)
            return
        if name in store.list_presets() and not dialogs.ask_yes_no(self, "Overwrite preset",
                                                                    f"A preset named '{name}' already exists. Overwrite it?"):
            return
        preset = store.ParameterPreset.from_state(name, self.model_id, self.f_values.get_state(),
                                              self.f_sigmas.get_state(), self.e_notes.get().strip())
        path = store.save_preset(preset)
        self._refresh_list(select=name)
        self._status(f"Saved as {path.name}")

    def _on_apply(self) -> None:
        self._apply(self.model_id, self.f_values.get_state(), self.f_sigmas.get_state())
        self._status("Applied to the main window.")

    def _on_take_over(self) -> None:
        model_id, state, sigmas = self._get_current()
        self._load_into_editor(model_id, state, sigmas, self.e_name.get(), self.e_notes.get())
        self._status("Settings of the main window taken over -- give it a name and save.")

    def _on_delete(self) -> None:
        name = self._selected_name()
        if not name:
            self._status("Select a preset in the list first.", error=True)
            return
        if dialogs.ask_yes_no(self, "Delete preset", f"Delete the preset '{name}' permanently?"):
            store.delete_preset(name)
            self._refresh_list()
            self._status(f"'{name}' deleted.")
