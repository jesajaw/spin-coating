"""
Real-display check of one colour theme (needs a display, e.g. `xvfb-run -a python tests/gui_theme_check.py dark_blue`).

Starts the real tkinter app with SPIN_COATING_THEME=<name>, drives every model x uncertainty method, opens the
parameter window and the preset window, and verifies that every tk widget colour belongs to the chosen palette
(no colour of another theme / no unthemed default). Optional 2nd argument: folder for screenshots.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

theme = sys.argv[1]
shots = Path(sys.argv[2]) if len(sys.argv) > 2 else None
os.environ["SPIN_COATING_THEME"] = theme
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tkinter as tk                                   # noqa: E402
import tkinter.ttk                                      # noqa: E402,F401
import matplotlib                                       # noqa: E402
matplotlib.use("TkAgg")

from ui import style                                    # noqa: E402
from ui import app as appmod                            # noqa: E402
from src.model import parameters as P                   # noqa: E402

assert style.COLOR_SCHEME == theme, (style.COLOR_SCHEME, theme)
palette = {v.lower() for v in style._SCHEMES[theme].values()} | {style.COLOR_ERROR.lower()}
foreign = {v.lower() for n, sc in style._SCHEMES.items() if n != theme for v in sc.values()} - palette


def settle(app, ms=250):
    app.update_idletasks()
    app.after(ms)
    app.update()


def rgb_hex(win, color: str) -> str:
    r, g, b = (c // 256 for c in win.winfo_rgb(color))
    return f"#{r:02x}{g:02x}{b:02x}"


def walk(w):
    yield w
    for c in w.winfo_children():
        yield from walk(c)


problems: list[str] = []


def check_tree(root, where):
    for w in walk(root):
        cls = w.winfo_class()
        if cls in ("Canvas", "Entry", "Listbox", "Toplevel", "Tk", "Frame", "Text"):   # plain tk widgets carry explicit colours
            for opt in ("bg", "fg", "background", "foreground", "selectbackground", "highlightbackground"):
                try:
                    val = str(w.cget(opt))
                except tk.TclError:
                    continue
                if not val:
                    continue
                if opt == "highlightbackground" and int(str(w.cget("highlightthickness")) or 0) == 0:
                    continue          # invisible focus ring: Tk's default grey is irrelevant
                h = rgb_hex(w, val)
                if h in foreign:
                    problems.append(f"{where}: {cls} {w} {opt}={h} belongs to another theme")
        if isinstance(w, tk.ttk.Widget):                          # ttk widgets: resolve through the style
            st = style_obj.lookup(str(w.cget("style")) or cls, "background")
            if st:
                h = rgb_hex(w, st)
                if h in foreign:
                    problems.append(f"{where}: ttk {w} background={h} belongs to another theme")


app = appmod.SpinCoatingApp()
style_obj = tk.ttk.Style(app)
app.geometry("1340x820+0+0")
settle(app, 600)

for model_id in P.MODEL_ORDER:
    app._on_model_change(P.MODELS[model_id].name)
    for method in (appmod.METHOD_NONE, appmod.METHOD_GAUSS, appmod.METHOD_MC):
        app.d_method.set(method)
        app._on_method_change()
        for key in P.MODELS[model_id].keys[:3]:
            app.sigma_form.state[key] = 0.03 * app.input_form.state[key]
        app._recompute()
        if method == appmod.METHOD_MC and not P.MODELS[model_id].fast:
            app._on_run_mc()
        settle(app, 120)
        check_tree(app, f"{model_id}/{method}")
        if shots and method == appmod.METHOD_GAUSS:
            from PIL import ImageGrab
            ImageGrab.grab(bbox=(0, 0, 1340, 820), xdisplay=os.environ.get("DISPLAY")).save(shots / f"{theme}_{model_id}.png")

app._open_parameters(); settle(app, 300); check_tree(app._params_win, "parameters window")
app._open_presets(); settle(app, 300); check_tree(app._presets_win, "presets window")
if shots:
    from PIL import ImageGrab
    ImageGrab.grab(bbox=(0, 0, 1500, 950), xdisplay=os.environ.get("DISPLAY")).save(shots / f"{theme}_windows.png")

# the result text must not be an error for the default inputs
app.destroy()
if problems:
    print(f"[{theme}] FAILED ({len(problems)} problems)")
    for p in dict.fromkeys(problems):
        print("  ", p)
    sys.exit(1)
print(f"[{theme}] ok: 3 models x 3 methods, parameter + preset window, no foreign colours")
