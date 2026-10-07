"""
Main application window.

    +-----------------------------+--------------------------------------------+
    | [Input | Uncertainty] tabs  |  plot range / band toggle                  |
    |                             |  +--------------------------------------+  |
    |                             |  |         spin curve (large)           |  |
    | Model [dropdown]            |  +--------------------------------------+  |
    | [Parameters][Presets]       |  Result              | Statistical dev.    |
    +-----------------------------+--------------------------------------------+

The model decides which fields exist (see model/parameters.MODELS). Computation is live: every field recomputes the
result and the plot, debounced by ~150 ms. Models that need a numerical ODE solve per evaluation
(ModelInfo.fast == False) compute their Monte Carlo on demand ("Run Monte Carlo"); everything else is live.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src import settings
from src.model import deviation
from src.model import parameters as P
import src.model as model
from . import style
from .forms import ParamForm
from .info import ParametersWindow
from .plot import SpinCurvePlot
from .presets import PresetsWindow
from .tex import TexLabel
from .widgets import Dropdown, NumberField, ResultDisplay, ScrollFrame

METHOD_NONE = "None"
METHOD_GAUSS = "Gauss (analytic)"
METHOD_MC = "Monte Carlo"
DEBOUNCE_MS = 150


class SpinCoatingApp(tk.Tk):
    def __init__(self):
        style.enable_dpi_awareness()
        super().__init__()
        self.title(settings.APP_TITLE)
        style.apply_style(self)
        self.minsize(1120, 700)

        self.model_id = P.MODEL_DEFAULT
        self._debounce_id = None
        self._mc_cache: dict | None = None      # on-demand Monte Carlo of a slow model: {"stats", "band"}
        self._params_win = self._presets_win = None

        self._build()
        self._update_method_widgets()
        self._recompute()
        self.geometry("1340x820")

    # ------------------------------------------------------------------ layout

    def _build(self) -> None:
        lay = style.LAYOUT
        outer = ttk.Frame(self, padding=lay.outer_padding)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=0)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        left = ttk.Frame(outer, width=lay.left_col_width)
        left.grid(row=0, column=0, sticky="ns", padx=(0, lay.col_gap))
        left.pack_propagate(False)
        self._build_left(left)

        right = ttk.Frame(outer)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        graph_box = ttk.LabelFrame(right, text="Film thickness vs. spin speed", padding=10)
        graph_box.grid(row=0, column=0, sticky="nsew", pady=(0, lay.row_gap))
        self._build_graph(graph_box)

        bottom = ttk.Frame(right)
        bottom.grid(row=1, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1, uniform="bottom")
        bottom.columnconfigure(1, weight=1, uniform="bottom")
        result_box = ttk.LabelFrame(bottom, text="Result", padding=12)
        result_box.grid(row=0, column=0, sticky="nsew", padx=(0, lay.col_gap))
        self.result = ResultDisplay(result_box)
        self.result.pack(anchor="w")
        stats_box = ttk.LabelFrame(bottom, text="Statistical deviation", padding=12)
        stats_box.grid(row=0, column=1, sticky="nsew")
        self.l_stat = [TexLabel(stats_box, "", style_name="ResultSmall.TLabel", wraplength=360) for _ in range(3)]
        for lbl in self.l_stat:
            lbl.pack(anchor="w", pady=(0, 3))

    def _build_left(self, parent) -> None:
        # Bottom block first (pack side="bottom" reserves its space), then the tabs fill what is left above it.
        bottom = ttk.Frame(parent)
        bottom.pack(side="bottom", fill="x", pady=(style.LAYOUT.row_gap, 0))
        self.d_model = Dropdown(bottom, "Model", P.model_names(), P.MODELS[self.model_id].name,
                                on_change=self._on_model_change, width=36)      # same widget as the other dropdowns
        self.d_model.pack(fill="x")
        row = ttk.Frame(bottom)
        row.pack(fill="x")
        ttk.Button(row, text="Parameters", command=self._open_parameters).pack(side="left")
        ttk.Button(row, text="Parameter presets...", command=self._open_presets).pack(side="left", padx=(6, 0))

        self.tabs = ttk.Notebook(parent)
        self.tabs.pack(fill="both", expand=True)

        input_scroll = ScrollFrame(self.tabs, padding=10)
        self.tabs.add(input_scroll, text="Input")
        self.input_form = ParamForm(input_scroll.body, self.model_id, P.default_state(),
                                    on_change=self._on_input_change, kind="values")
        self.input_form.pack(fill="x")

        unc_scroll = ScrollFrame(self.tabs, padding=10)
        self.tabs.add(unc_scroll, text="Uncertainty")
        self._build_uncertainty(unc_scroll.body)

    def _build_uncertainty(self, parent) -> None:
        self.d_method = Dropdown(parent, "Method", [METHOD_NONE, METHOD_GAUSS, METHOD_MC], METHOD_NONE,
                                 on_change=self._on_method_change, width=30)
        self.d_method.pack(fill="x")

        self.mc_frame = ttk.Frame(parent)
        self.d_dist = Dropdown(self.mc_frame, "Distribution shape (Monte Carlo)", [d.value for d in deviation.DistKind],
                               deviation.DistKind.GAUSS.value, on_change=self._on_input_change, width=30)
        self.d_dist.pack(fill="x")
        self.f_mc_n = NumberField(self.mc_frame, "Number of samples", settings.MONTE_CARLO_DEFAULT_N,
                                  settings.MONTE_CARLO_MIN_N, settings.MONTE_CARLO_MAX_N, "%.0f",
                                  on_change=self._on_input_change)
        self.f_mc_n.pack(fill="x")

        self.run_row = ttk.Frame(parent)
        ttk.Label(self.run_row, text="Every sample of this model re-solves the full ODE, so Monte Carlo is not "
                                     "live here -- click to (re)compute statistics and band:",
                  style="Help.TLabel", wraplength=400, justify="left").pack(anchor="w", pady=(0, 4))
        ttk.Button(self.run_row, text="Run Monte Carlo", style="Accent.TButton", command=self._on_run_mc).pack(anchor="w")

        self.sigma_frame = ttk.Frame(parent)
        ttk.Label(self.sigma_frame, text="Uncertainties of the parameters", style="CategoryHeader.TLabel"
                  ).pack(anchor="w", pady=(6, 4))
        self.sigma_form = ParamForm(self.sigma_frame, self.model_id, P.default_sigmas(),
                                    on_change=self._on_input_change, kind="sigmas")
        self.sigma_form.pack(fill="x")
        ttk.Label(self.sigma_frame, text="Only the uncertainties entered here are propagated -- not the "
                                         "systematic error of the model itself.", style="Help.TLabel",
                  wraplength=400, justify="left").pack(anchor="w", pady=(6, 0))

    def _build_graph(self, parent) -> None:
        opt_row = ttk.Frame(parent)
        opt_row.pack(fill="x", pady=(0, 6))
        self.f_plot_min = NumberField(opt_row, r"$\omega_\mathrm{min}$ [rpm]", settings.PLOT_RPM_DEFAULT_MIN, 50, 20000,
                                      "%.0f", on_change=self._on_input_change, box_width=80)
        self.f_plot_min.pack(side="left", padx=(0, 14))
        self.f_plot_max = NumberField(opt_row, r"$\omega_\mathrm{max}$ [rpm]", settings.PLOT_RPM_DEFAULT_MAX, 50, 20000,
                                      "%.0f", on_change=self._on_input_change, box_width=80)
        self.f_plot_max.pack(side="left")
        self.v_band = tk.BooleanVar(value=True)
        self.c_band = ttk.Checkbutton(opt_row, text="Show uncertainty band", variable=self.v_band,
                                      command=self._recompute)
        self.c_band.pack(side="left", padx=(20, 0))

        self.plot = SpinCurvePlot(parent)
        self.plot.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ windows

    def _alive(self, win) -> bool:
        return win is not None and bool(win.winfo_exists())

    def _open_parameters(self) -> None:
        if self._alive(self._params_win):
            self._params_win.refresh(self.model_id)
            self._params_win.lift()
        else:
            self._params_win = ParametersWindow(self, self.model_id)

    def _open_presets(self) -> None:
        if self._alive(self._presets_win):
            self._presets_win.lift()
        else:
            self._presets_win = PresetsWindow(self, self._current, self._apply_preset)

    def _current(self) -> tuple[str, dict, dict]:
        return self.model_id, self.input_form.get_state(), self.sigma_form.get_state()

    def _apply_preset(self, model_id: str, state: dict, sigmas: dict) -> None:
        self.model_id = model_id
        self.d_model.set(P.MODELS[model_id].name)
        self.input_form.model_id = model_id
        self.input_form.set_state(state)
        self.sigma_form.model_id = model_id
        self.sigma_form.set_state(sigmas)
        self._after_model_change()

    # ------------------------------------------------------------------ events

    def _on_model_change(self, name: str) -> None:
        self.model_id = P.model_id_from_name(name)
        self.input_form.set_model(self.model_id)
        self.sigma_form.set_model(self.model_id)
        self._after_model_change()

    def _after_model_change(self) -> None:
        self._mc_cache = None
        self._adapt_sample_count()
        self._update_method_widgets()
        if self._alive(self._params_win):
            self._params_win.refresh(self.model_id)
        self._recompute()

    def _on_method_change(self, _value=None) -> None:
        self._update_method_widgets()
        self._on_input_change()

    def _on_input_change(self, _value=None) -> None:
        """Any input changed: drop an on-demand Monte Carlo result (it no longer matches) and recompute."""
        self._mc_cache = None
        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(DEBOUNCE_MS, self._recompute)

    def _adapt_sample_count(self) -> None:
        """Slow (ODE) models get a much smaller sample range than the closed-form ones."""
        if P.MODELS[self.model_id].fast:
            self.f_mc_n.maximum = settings.MONTE_CARLO_MAX_N
            if self.f_mc_n.get() <= settings.SLOW_MC_DEFAULT_N:
                self.f_mc_n.set(settings.MONTE_CARLO_DEFAULT_N)
        else:
            self.f_mc_n.maximum = settings.SLOW_MC_MAX_N
            self.f_mc_n.set(min(self.f_mc_n.get(), settings.SLOW_MC_DEFAULT_N))

    def _update_method_widgets(self) -> None:
        info = P.MODELS[self.model_id]
        method = self.d_method.get()
        for frame in (self.mc_frame, self.run_row, self.sigma_frame):
            frame.pack_forget()
        if method == METHOD_NONE:
            return
        if method == METHOD_MC:
            self.mc_frame.pack(fill="x")
            if not info.fast:
                self.run_row.pack(fill="x", pady=(4, 4))
        self.sigma_frame.pack(fill="x")

    # ------------------------------------------------------------------ compute

    def _set_stats(self, *lines: str, error: bool = False) -> None:
        for i, lbl in enumerate(self.l_stat):
            text = lines[i] if i < len(lines) else ""
            lbl.set_text(text, color=style.COLOR_ERROR if (error and i == 0) else style.COLOR_STATUS_TEXT)

    def _read_inputs(self) -> tuple[dict, dict, dict]:
        state = self.input_form.get_state()
        values = P.model_values(state, self.model_id)
        return state, values, self.sigma_form.get_state()

    def _recompute(self, *_args) -> None:
        self._debounce_id = None
        mid = self.model_id
        info = P.MODELS[mid]
        self._set_stats()
        try:
            _state, values, sig = self._read_inputs()
            result = model.compute(mid, values)
        except ValueError as e:
            self.result.set("--", caption=str(e), error=True)
            self.plot.set_data([])
            return

        q = info.quantity_tex
        self.result.set(f"{result.thickness_nm:,.1f} nm", q, rf"{info.caption}  ({result.thickness_um:.3f} $\mu$m)",
                        result.details)

        method = self.d_method.get()
        has_sigma = deviation.has_sigma(mid, sig)
        curve, band = [], None
        try:
            rpm_min, rpm_max = self.f_plot_min.get(), self.f_plot_max.get()
            if rpm_min < rpm_max:
                curve = model.spin_curve(mid, values, rpm_min, rpm_max, settings.PLOT_POINTS)
                if self.v_band.get() and method != METHOD_NONE and has_sigma:
                    band = self._band(mid, info, values, sig, curve, method)
        except ValueError:
            curve, band = [], None
        self.plot.set_data(curve, band=band, marker=(values["rpm"], result.thickness_nm),
                           y_label_tex=rf"${q}$ [nm]",
                           band_label="±1σ (Gauss)" if method == METHOD_GAUSS else "P05 - P95 (Monte Carlo)")

        if method == METHOD_NONE:
            return
        if not has_sigma:
            self._set_stats("Enter at least one uncertainty (Uncertainty tab).")
            return
        try:
            self._show_stats(mid, info, values, sig, method, q)
        except ValueError as e:
            self._set_stats(f"! {e}", error=True)

    def _band(self, mid, info, values, sig, curve, method):
        if method == METHOD_GAUSS:
            return deviation.analytic_band(mid, values, sig, curve,
                                           max_points=None if info.fast else settings.SLOW_BAND_POINTS)
        if info.fast:
            kind = deviation.DistKind(self.d_dist.get())
            return deviation.monte_carlo_band(mid, values, sig, kind, [x for x, _ in curve],
                                              settings.BAND_SAMPLES, settings.MONTE_CARLO_SEED)
        return self._mc_cache["band"] if self._mc_cache else None

    def _show_stats(self, mid, info, values, sig, method, q) -> None:
        if method == METHOD_GAUSS:
            a = deviation.propagate_analytic(mid, values, sig)
            self._set_stats(rf"${q}$ = {a.mean_nm:.1f} ± {a.sigma_nm:.1f} nm  (1σ, Gauss)",
                            f"relative uncertainty: {a.relative_sigma * 100:.1f} %",
                            f"~95 % range (±2σ): {a.mean_nm - 2 * a.sigma_nm:.1f} - {a.mean_nm + 2 * a.sigma_nm:.1f} nm")
            return
        if info.fast:
            kind = deviation.DistKind(self.d_dist.get())
            mc = deviation.propagate_monte_carlo(mid, values, sig, kind, int(self.f_mc_n.get()),
                                                 settings.MONTE_CARLO_SEED)
        elif self._mc_cache:
            mc = self._mc_cache["stats"]
        else:
            self._set_stats("Click \"Run Monte Carlo\" on the Uncertainty tab.")
            return
        self._set_stats(rf"${q}$ = {mc.mean_nm:.1f} nm  (Monte Carlo, n = {mc.n})",
                        f"standard deviation: {mc.std_nm:.1f} nm",
                        f"P05 / P50 / P95: {mc.p05_nm:.1f} / {mc.p50_nm:.1f} / {mc.p95_nm:.1f} nm")

    def _on_run_mc(self) -> None:
        """On-demand Monte Carlo of a slow (ODE) model: statistics at the operating point plus the band."""
        mid = self.model_id
        info = P.MODELS[mid]
        if info.fast or self.d_method.get() != METHOD_MC:
            return
        self._set_stats("Running...")
        self.update_idletasks()
        try:
            _state, values, sig = self._read_inputs()
            if not deviation.has_sigma(mid, sig):
                self._set_stats("Enter at least one uncertainty first.")
                return
            kind = deviation.DistKind(self.d_dist.get())
            n = int(self.f_mc_n.get())
            stats = deviation.propagate_monte_carlo(mid, values, sig, kind, n, settings.MONTE_CARLO_SEED)
            band = None
            rpm_min, rpm_max = self.f_plot_min.get(), self.f_plot_max.get()
            if rpm_min < rpm_max:
                xs = model.spin_speeds(rpm_min, rpm_max, settings.PLOT_POINTS)
                coarse = model.spin_speeds(rpm_min, rpm_max, settings.SLOW_BAND_POINTS)
                cband = deviation.monte_carlo_band(mid, values, sig, kind, coarse,
                                                   min(n, settings.SLOW_BAND_SAMPLES), settings.MONTE_CARLO_SEED)
                band = deviation.interpolate_band(coarse, cband, xs)
        except ValueError as e:
            self._set_stats(f"! {e}", error=True)
            return
        self._mc_cache = {"stats": stats, "band": band}
        self._recompute()


def run() -> None:
    app = SpinCoatingApp()
    app.mainloop()
