"""
Reusable building blocks:
- Cell: clickable tile (title, optional status line, hover highlight)
- NumberField: mathtext label + numeric box with a proportional accent fill bar; click-drag or double-click to type
- Dropdown: label + readonly combobox
- ResultDisplay: big value with the quantity name, plus detail lines
- ScrollFrame: vertically scrollable container (mouse wheel while the pointer is over it)
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

from . import style
from .tex import TexLabel


class Cell(ttk.Frame):
    def __init__(self, parent, title: str, on_click=None, status_text: str | None = None,
                 width: int = style.CELL_WIDTH, height: int = style.CELL_HEIGHT):
        super().__init__(parent, padding=8, relief="groove", style="Cell.TFrame")
        self.on_click = on_click
        self.pack_propagate(False)
        self.configure(width=width, height=height)

        self.title_label = ttk.Label(self, text=title, style="CellTitle.TLabel")
        self.title_label.pack(anchor="w")

        self.status_label = None
        clickable = [self, self.title_label]
        if status_text is not None:
            self.status_label = ttk.Label(self, text=status_text, style="Status.TLabel",
                                          wraplength=width - 20, justify="left")
            self.status_label.pack(anchor="w", pady=(4, 8), fill="x")
            clickable.append(self.status_label)

        if on_click is not None:
            for w in clickable:
                w.configure(cursor="hand2")
                w.bind("<Button-1>", self._on_click)
                w.bind("<Enter>", self._on_enter)
                w.bind("<Leave>", self._on_leave)

        self.bind("<Configure>", self._on_resize)

    def set_title(self, text: str) -> None:
        self.title_label.configure(text=text)

    def set_status(self, text: str) -> None:
        if self.status_label is not None:
            self.status_label.configure(text=text)

    def _on_click(self, _e=None) -> None:
        if self.on_click:
            self.on_click()

    def _on_enter(self, _e=None) -> None:
        self.configure(style="CellHover.TFrame")
        self.title_label.configure(style="CellTitleHover.TLabel")
        if self.status_label is not None:
            self.status_label.configure(style="StatusHover.TLabel")

    def _on_leave(self, _e=None) -> None:
        self.configure(style="Cell.TFrame")
        self.title_label.configure(style="CellTitle.TLabel")
        if self.status_label is not None:
            self.status_label.configure(style="Status.TLabel")

    def _on_resize(self, event) -> None:
        wrap = max(event.width - 20, 20)
        self.title_label.configure(wraplength=wrap)
        if self.status_label is not None:
            self.status_label.configure(wraplength=wrap)


class NumberField(ttk.Frame):
    """
    One input row: [value box with an accent fill bar]  Label.
    Click-drag left/right across the box sets the value proportionally within [minimum, maximum];
    double-click opens a text editor for the exact number (confirm with Enter or by clicking elsewhere,
    Escape cancels). Values typed outside the slider range are clamped to it.
    on_change(value) fires on every edit -- callers debounce it themselves (see app.py).
    `label` is mathtext (plain text and $...$ may be mixed).
    """

    def __init__(self, parent, label: str, value: float, minimum: float, maximum: float,
                 fmt: str = "%.3f", on_change=None, box_width: int = 130, log: bool = False,
                 scale: float = 1.0):
        super().__init__(parent)
        self.minimum, self.maximum, self.fmt, self.log = minimum, maximum, fmt, log
        self.scale = scale                      # shown value * scale = value handed to the caller
        self.on_change = on_change
        self._value = min(max(value / scale, minimum), maximum)
        self._dragging = False
        self._box_width = box_width

        row = ttk.Frame(self)
        row.pack(fill="x")

        self.canvas = tk.Canvas(row, width=box_width, height=style.FIELD_HEIGHT, bg=style.COLOR_BG_LIGHT,
                                highlightthickness=1, highlightbackground=style.COLOR_DARK,
                                cursor="sb_h_double_arrow")
        self.canvas.pack(side="left")
        self._fill = self.canvas.create_rectangle(0, 0, 0, 0, fill=style.COLOR_DARK, width=0)
        self._text = self.canvas.create_text(box_width // 2, style.FIELD_HEIGHT // 2, text="",
                                             fill=style.COLOR_FG, font=style.FONT_MONO_NORMAL)

        self.label = TexLabel(row, label)
        self.label.pack(side="left", padx=(8, 0))

        self._entry: tk.Entry | None = None
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)
        self.canvas.bind("<Double-Button-1>", self._open_editor)

        ttk.Frame(self, height=4).pack()
        self._redraw()

    # -- value access ---------------------------------------------------

    def get(self) -> float:
        """Value in the caller's units (shown value * scale)."""
        return self._value * self.scale

    def get_shown(self) -> float:
        return self._value

    def set(self, value: float, fire: bool = False) -> None:
        """`value` in the caller's units."""
        self._set_shown(value / self.scale, fire)

    def _set_shown(self, shown: float, fire: bool) -> None:
        self._value = min(max(shown, self.minimum), self.maximum)
        self._redraw()
        if fire and self.on_change:
            self.on_change(self.get())

    # -- drawing ----------------------------------------------------------

    def _frac(self) -> float:
        lo, hi, v = self.minimum, self.maximum, self._value
        if self.log and lo > 0 and v > 0:
            return (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo))
        return (v - lo) / (hi - lo) if hi > lo else 0.0

    def _redraw(self) -> None:
        w = self._box_width
        self.canvas.coords(self._fill, 0, 0, w * max(0.0, min(1.0, self._frac())), style.FIELD_HEIGHT)
        self.canvas.itemconfigure(self._text, text=self.fmt % self._value)

    # -- interaction --------------------------------------------------------

    def _value_from_x(self, x: float) -> float:
        frac = max(0.0, min(1.0, x / self._box_width))
        lo, hi = self.minimum, self.maximum
        if self.log and lo > 0:
            return math.exp(math.log(lo) + frac * (math.log(hi) - math.log(lo)))
        return lo + frac * (hi - lo)

    def _start_drag(self, event) -> None:
        if self._entry is not None:
            return
        self._dragging = True
        self._set_shown(self._value_from_x(event.x), True)

    def _drag(self, event) -> None:
        if self._dragging:
            self._set_shown(self._value_from_x(event.x), True)

    def _end_drag(self, _event) -> None:
        self._dragging = False

    def _open_editor(self, _event) -> None:
        if self._entry is not None:
            return
        self._entry = tk.Entry(self.canvas, bg=style.COLOR_BG_LIGHT, fg=style.COLOR_FG,
                               insertbackground=style.COLOR_FG, relief="flat",
                               font=style.FONT_MONO_NORMAL, justify="center")
        self._entry.insert(0, self.fmt % self._value)
        self._entry.select_range(0, "end")
        self._entry.place(x=0, y=0, width=self._box_width, height=style.FIELD_HEIGHT)
        self._entry.focus_set()
        self._entry.bind("<Return>", self._commit_editor)
        self._entry.bind("<FocusOut>", self._commit_editor)
        self._entry.bind("<Escape>", lambda e: self._close_editor())

    def _commit_editor(self, _event) -> None:
        if self._entry is None:
            return
        text = self._entry.get().strip().replace(",", ".")
        self._close_editor()
        try:
            self._set_shown(float(text), True)
        except ValueError:
            self._redraw()

    def _close_editor(self) -> None:
        if self._entry is not None:
            self._entry.destroy()
            self._entry = None


class Dropdown(ttk.Frame):
    def __init__(self, parent, label: str, values: list[str], value: str, on_change=None, width: int = 22):
        super().__init__(parent)
        if label:
            TexLabel(self, label).pack(anchor="w")
        self.var = tk.StringVar(value=value)
        self.combo = ttk.Combobox(self, textvariable=self.var, values=values, state="readonly", width=width)
        self.combo.pack(anchor="w", pady=(2, 0), fill="x")
        if on_change:
            self.combo.bind("<<ComboboxSelected>>", lambda e: on_change(self.var.get()))
        ttk.Frame(self, height=6).pack()

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str) -> None:
        self.var.set(value)

    def set_values(self, values: list[str]) -> None:
        self.combo.configure(values=values)


class ResultDisplay(ttk.Frame):
    """`quantity_tex = value unit` in big accent text, then a caption and detail lines (mathtext allowed)."""

    def __init__(self, parent):
        super().__init__(parent)
        top = ttk.Frame(self)
        top.pack(anchor="w")
        self.quantity_label = TexLabel(top, "", size=16, color=style.COLOR)
        self.quantity_label.pack(side="left", padx=(0, 10))
        self.value_label = ttk.Label(top, text="--", style="ResultBig.TLabel")
        self.value_label.pack(side="left")
        self.caption_label = TexLabel(self, "", style_name="ResultSmall.TLabel", color=style.COLOR_STATUS_TEXT)
        self.caption_label.pack(anchor="w")
        self.detail_frame = ttk.Frame(self)
        self.detail_frame.pack(anchor="w", pady=(8, 0))
        self._details: list[TexLabel] = []

    def set(self, value_text: str, quantity_tex: str = "", caption: str = "", details=(), error: bool = False) -> None:
        self.quantity_label.set_text(f"${quantity_tex}$ =" if quantity_tex and not error else "")
        self.value_label.configure(text=value_text, style="Error.TLabel" if error else "ResultBig.TLabel")
        self.caption_label.set_text(caption, color=style.COLOR_ERROR if error else style.COLOR_STATUS_TEXT)
        for lbl in self._details:
            lbl.destroy()
        self._details = []
        for line in details:
            lbl = TexLabel(self.detail_frame, line, color=style.COLOR_STATUS_TEXT)
            lbl.pack(anchor="w")
            self._details.append(lbl)


class ScrollFrame(ttk.Frame):
    """
    Vertically scrollable container: put children into `.body`. The mouse wheel scrolls while the pointer is over
    the frame. Labels registered with `track_wrap` follow the available width (for long text blocks).
    """

    def __init__(self, parent, padding: int = 0):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=style.COLOR_BG, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = ttk.Frame(self.canvas, padding=padding)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self._wrap_labels: list[tuple[ttk.Label, int]] = []
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        for w in (self.canvas, self.body):
            w.bind("<Enter>", self._bind_wheel)
            w.bind("<Leave>", self._unbind_wheel)

    def track_wrap(self, label: ttk.Label, margin: int = 0) -> None:
        self._wrap_labels.append((label, margin))

    def _on_canvas_resize(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        for label, margin in self._wrap_labels:
            label.configure(wraplength=max(event.width - margin - 8, 60))

    def _bind_wheel(self, _e=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def _unbind_wheel(self, _e=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units")
