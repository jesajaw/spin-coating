"""
Minimal stand-in for tkinter / ttk / matplotlib's Tk backend, so the UI code can be imported and driven on a
machine without a display (CI, sandboxes). It does NOT draw anything -- it only checks that the UI code is wired
correctly (names, arguments, callbacks, state flow). Real appearance has to be checked by running `python main.py`.

Usage:  from tests import tk_stub; tk_stub.install()
"""

from __future__ import annotations

import sys
import types


class _Widget:
    created: list = []

    def __init__(self, *args, **kwargs):
        self._cfg = dict(kwargs)
        self._after = []
        _Widget.created.append(self)

    def __getattr__(self, name):                       # any other Tk method: accept and do nothing
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: None

    def configure(self, *a, **k):
        self._cfg.update(k)

    config = configure

    def cget(self, key):
        return self._cfg.get(key)

    def winfo_children(self):
        return []

    def winfo_exists(self):
        return True

    def winfo_fpixels(self, _s):
        return 96.0

    def winfo_width(self):
        return 400

    def winfo_height(self):
        return 300

    def after(self, ms, fn=None, *args):
        self._after.append(fn)
        return f"after#{len(self._after)}"

    def get(self, *a):
        return ""

    def curselection(self):
        return ()

    def bbox(self, *a):
        return (0, 0, 10, 10)

    def option_add(self, *a):
        return None


class _Var:
    def __init__(self, master=None, value=None, **kw):
        self._v = value

    def get(self):
        return self._v

    def set(self, v):
        self._v = v


class _Style:
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        return lambda *a, **k: None


class _Image(_Widget):
    pass


def install() -> None:
    tk = types.ModuleType("tkinter")
    ttk = types.ModuleType("tkinter.ttk")
    fd = types.ModuleType("tkinter.filedialog")

    class Tk(_Widget):
        pass

    class Toplevel(_Widget):
        pass

    for name in ("Frame", "Canvas", "Entry", "Listbox", "Text", "Label", "Button", "Scrollbar"):
        setattr(tk, name, type(name, (_Widget,), {}))
    tk.Tk, tk.Toplevel = Tk, Toplevel
    tk.StringVar, tk.BooleanVar, tk.IntVar, tk.DoubleVar = _Var, _Var, _Var, _Var
    tk.PhotoImage = _Image
    tk.TclError = type("TclError", (Exception,), {})
    for name in ("Frame", "Label", "Button", "Entry", "Combobox", "Checkbutton", "Notebook", "Separator",
                 "Scrollbar", "LabelFrame", "Radiobutton", "Progressbar"):
        setattr(ttk, name, type(name, (_Widget,), {}))
    ttk.Style = _Style
    fd.askopenfilename = lambda **k: ""
    tk.ttk, tk.filedialog = ttk, fd
    sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk, "tkinter.filedialog": fd})

    be = types.ModuleType("matplotlib.backends.backend_tkagg")

    class FigureCanvasTkAgg:
        def __init__(self, figure, master=None):
            self.figure = figure
            self.widget = _Widget()

        def get_tk_widget(self):
            return self.widget

        def draw_idle(self):
            pass

    be.FigureCanvasTkAgg = FigureCanvasTkAgg
    sys.modules["matplotlib.backends.backend_tkagg"] = be
