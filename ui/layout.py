"""
Main Application Window Layout for Spin-Coating simulation in Tkinter.
"""
import tkinter as tk
from tkinter import ttk
import json
from . import style, dialogs, widgets
from ..model import compute

class SpinCoatingApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Spin-Coating Parameter & Film Thickness Simulator")
        style.apply_style(self)
        
        self.minsize(style.px(700), style.px(520))
        self.geometry(f"{style.px(780)}x{style.px(580)}")
        
        self._build_ui()

    def _build_ui(self) -> None:
        main_container = ttk.Frame(self, padding=style.LAYOUT.outer_padding)
        main_container.pack(fill="both", expand=True)
        
        # Header / Action bar (Load Preset / Clear)
        action_bar = ttk.Frame(main_container)
        action_bar.pack(fill="x", pady=(0, 15))
        
        widgets.Cell(action_bar, "Load JSON Config", on_click=self._load_config, 
                     status_text="Import parameters from file", width=style.px(200), height=style.px(70)).pack(side="left", padx=(0, 10))
                     
        widgets.Cell(action_bar, "Clear Inputs", on_click=self._reset_fields, 
                     status_text="Reset values to default", width=style.px(200), height=style.px(70)).pack(side="left")
        
        # Form Container for Input Parameters
        param_box = ttk.LabelFrame(main_container, text="Spin Coating Process Parameters", padding=15)
        param_box.pack(fill="x", pady=(0, 15))
        
        self.inputs = {
            "viscosity": widgets.LabeledEntry(param_box, "Viscosity η (Pa·s):", "0.05"),
            "spin_speed": widgets.LabeledEntry(param_box, "Spin Speed ω (rpm):", "3000"),
            "spin_time": widgets.LabeledEntry(param_box, "Spin Time t (s):", "30"),
            "density": widgets.LabeledEntry(param_box, "Solution Density ρ (kg/m³):", "1000"),
            "solid_fraction": widgets.LabeledEntry(param_box, "Solid Concentration c₀:", "0.10"),
        }
        
        for field in self.inputs.values():
            field.pack(fill="x", pady=4)

        # Calculate Button & Output
        btn_bar = ttk.Frame(main_container)
        btn_bar.pack(fill="x", pady=(0, 15))
        
        ttk.Button(btn_bar, text="Calculate Film Thickness", style="Accent.TButton", 
                   command=self._run_calculation).pack(fill="x", ipady=4)
        
        self.result_box = widgets.ResultDisplay(main_container, label="Calculated Final Film Thickness (h)")
        self.result_box.pack(fill="x")

    def _run_calculation(self) -> None:
        try:
            params = {k: float(v.get()) for k, v in self.inputs.items()}
        except ValueError:
            dialogs.show_error(self, "Invalid Input", "Please enter valid numerical values for all parameters.")
            return

        try:
            # Invoking spin coating calculation logic
            res = compute.calculate_thickness(params) if hasattr(compute, "calculate_thickness") else self._default_calc(params)
            self.result_box.set_text(f"{res:.2f} nm")
        except Exception as err:
            dialogs.show_error(self, "Calculation Error", str(err))

    def _default_calc(self, p: dict) -> float:
        # Fallback physics calculation if model.compute structure varies
        # Meyerhofer model approximation
        import math
        omega_rad = p["spin_speed"] * (2 * math.pi / 60)
        h_final = p["solid_fraction"] * math.sqrt(p["viscosity"] / (p["density"] * omega_rad**2 * p["spin_time"])) * 1e9
        return h_final

    def _load_config(self) -> None:
        path = dialogs.ask_open_file(self)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, val in data.items():
                if k in self.inputs:
                    self.inputs[k].set(str(val))
        except Exception as e:
            dialogs.show_error(self, "File Error", f"Could not load file: {e}")

    def _reset_fields(self) -> None:
        defaults = {"viscosity": "0.05", "spin_speed": "3000", "spin_time": "30", "density": "1000", "solid_fraction": "0.10"}
        for k, val in defaults.items():
            if k in self.inputs:
                self.inputs[k].set(val)
        self.result_box.set_text("--")