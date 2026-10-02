"""
UI smoke tests WITHOUT a display: tkinter is replaced by tests/tk_stub.py, matplotlib (mathtext, figure) is real.
They check that every formula renders, the plot draws, and the app wiring (model switch, uncertainty methods,
Monte Carlo, presets, info windows) runs without exceptions. They cannot judge the look -- run `python main.py`.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import tk_stub

tk_stub.install()

import matplotlib
matplotlib.use("Agg")

from src.model import parameters as P                       # noqa: E402
from ui import texts, tex                                    # noqa: E402


def _all_tex_strings() -> list[str]:
    out = []
    for spec in P.PARAMS.values():
        out += [spec.label_tex, spec.sigma_label_tex]
    for info in P.MODELS.values():
        out += [f"${info.quantity_tex}$ =", f"${info.quantity_tex}$ [nm]"]
    for blocks in texts.PHYSICS.values():
        out += [f"${c}$" for k, c in blocks if k == "tex"]
    out += [f"${f}$" for f in texts.PARAM_FORMULA.values()]
    out += [r"$\omega_\mathrm{min}$ [rpm]", r"Solids fraction $C_0$ from", r"Evaporation rate $E$ vs. spin speed",
            r"Solids weight fraction $w$ [$\%$]", r"$\rightarrow$ $C_0$ = 7.69 % (volume)",
            r"Wet transition thickness $h_\mathrm{s}$: 2.566 $\mu$m", r"Limit for $h_0\to\infty$: 12.0 nm",
            r"$\pm$ Solids volume fraction $\Delta C_0$ [$\mathrm{pp}$]"]
    return out


def test_every_formula_renders():
    for s in _all_tex_strings():
        data = tex.png_bytes(s, 10.0, "#e0dff0", 96.0)
        assert data[:8] == b"\x89PNG\r\n\x1a\n", s


def test_plot_draws_with_and_without_band():
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from ui import plot, style
    pts = [(500 * 1.06 ** i, 600 / (1 + 0.1 * i)) for i in range(60)]
    band = [(y * 0.9, y * 1.1) for _, y in pts]
    for b in (None, band):
        fig = Figure(figsize=(6.4, 4.4), dpi=100, facecolor=style.COLOR_BG_LIGHT, layout="constrained")
        plot.draw_spin_curve(fig.add_subplot(111), pts, b, marker=pts[20], band_label="P05 - P95 (Monte Carlo)")
        buf = io.BytesIO()
        FigureCanvasAgg(fig).print_png(buf)
        assert len(buf.getvalue()) > 5000
    fig = Figure(layout="constrained")
    plot.draw_spin_curve(fig.add_subplot(111), [])           # empty data must not raise


def test_app_runs_through_all_models_and_methods():
    from ui import app as appmod
    a = appmod.SpinCoatingApp()
    for model_id in P.MODEL_ORDER:
        a._on_model_change(P.MODELS[model_id].name)
        assert a.model_id == model_id
        for method in (appmod.METHOD_NONE, appmod.METHOD_GAUSS, appmod.METHOD_MC):
            a.d_method.set(method)
            a._on_method_change()
            # give a few parameters an uncertainty
            for key in P.MODELS[model_id].keys[:3]:
                a.sigma_form.state[key] = 0.02 * a.input_form.state[key]
            a._recompute()
            if method == appmod.METHOD_MC and not P.MODELS[model_id].fast:
                a._on_run_mc()
        a._open_physics()
        a._open_parameters()
    a._open_presets()


def test_error_state_is_shown_not_raised():
    from ui import app as appmod
    a = appmod.SpinCoatingApp()
    a._on_model_change(P.MODELS[P.MODEL_MEYERHOFER].name)
    a.input_form.state["viscosity_cp"] = 0.0
    a._recompute()          # unphysical input -> error message in the result box, no exception


def test_presets_window_roundtrip():
    import tempfile
    from src import settings, store
    from ui import app as appmod
    old = settings.PRESETS_DIR
    with tempfile.TemporaryDirectory() as tmp:
        settings.PRESETS_DIR = Path(tmp)
        try:
            a = appmod.SpinCoatingApp()
            win = appmod.PresetsWindow(a, a._current, a._apply_preset)
            win.e_name.get = lambda: "ui preset"
            win.e_notes.get = lambda: "from smoke test"
            win._on_save()
            assert store.list_presets() == ["ui preset"]
            win.listbox.curselection = lambda: (0,)
            win.listbox.get = lambda i: "ui preset"
            win._on_select()
            win._on_apply()
            win._on_take_over()
        finally:
            settings.PRESETS_DIR = old


if __name__ == "__main__":
    tests = [(k, f) for k, f in sorted(globals().items()) if k.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"ok  {name}")
    print(f"{len(tests)} tests passed.")
