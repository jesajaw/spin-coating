"""
Spin-curve plot (thickness vs. spin speed), drawn with matplotlib's object-oriented API (no pyplot, so no
global state) and embedded in Tk. constrained layout keeps axis labels, tick labels and the plot area from
colliding at any window size. Axis labels use mathtext.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator, FuncFormatter, NullFormatter

from . import style

NICE_TICKS = (50, 100, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 4000, 5000, 7000, 10000, 15000, 20000)
X_LABEL = r"spin speed $\omega$ [rpm]"


def _style_axes(ax) -> None:
    ax.set_facecolor(style.COLOR_BG_LIGHT)
    for spine in ax.spines.values():
        spine.set_color(style.COLOR_DARK)
    ax.tick_params(colors=style.COLOR_STATUS_TEXT, which="both", labelsize=9)
    ax.xaxis.label.set_color(style.COLOR_FG)
    ax.yaxis.label.set_color(style.COLOR_FG)
    ax.grid(True, which="major", color="#3c3c48", linewidth=0.7)
    ax.set_axisbelow(True)


def draw_spin_curve(ax, points: list[tuple[float, float]], band: list[tuple[float, float]] | None = None,
                    marker: tuple[float, float] | None = None, y_label_tex: str = r"$h_\mathrm{f}$ [nm]",
                    log_x: bool = True, band_label: str | None = None) -> None:
    """Draws everything onto `ax` (cleared first). Separate from the Tk widget so it can be tested headlessly."""
    ax.clear()
    _style_axes(ax)
    if len(points) < 2:
        ax.text(0.5, 0.5, "Not enough data to plot.", transform=ax.transAxes, ha="center", va="center",
                color=style.COLOR_STATUS_TEXT)
        ax.set_xticks([])
        ax.set_yticks([])
        return

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    if band:
        lo = [max(b[0], 0.0) for b in band]
        hi = [b[1] for b in band]
        ax.fill_between(xs, lo, hi, color=style.COLOR, alpha=0.25, linewidth=0, label=band_label or "uncertainty band")
        ys = ys + hi
    ax.plot(xs, [p[1] for p in points], color=style.COLOR, linewidth=2.2, label="nominal")

    if marker:
        mx, my = marker
        ax.axvline(mx, color=style.COLOR_STATUS_TEXT, linewidth=0.8, linestyle=":")
        ax.plot([mx], [my], "o", markersize=8, markerfacecolor=style.COLOR_FG, markeredgecolor=style.COLOR,
                markeredgewidth=2, zorder=5)
        ax.annotate(f"{my:,.1f} nm", (mx, my), textcoords="offset points", xytext=(10, 10),
                    color=style.COLOR_FG, fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor=style.COLOR_BG, edgecolor=style.COLOR_DARK))

    x0, x1 = min(xs), max(xs)
    if log_x and x0 > 0:
        ax.set_xscale("log")
        ticks = [t for t in NICE_TICKS if x0 <= t <= x1] or [x0, x1]
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"{v:,.0f}"))
        ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlim(x0, x1)
    top = max(ys) * 1.12 if max(ys) > 0 else 1.0
    ax.set_ylim(0, top)
    ax.set_xlabel(X_LABEL, fontsize=10)
    ax.set_ylabel(y_label_tex, fontsize=10)
    if band:
        leg = ax.legend(loc="upper right", fontsize=8, frameon=True, facecolor=style.COLOR_BG,
                        edgecolor=style.COLOR_DARK)
        for text in leg.get_texts():
            text.set_color(style.COLOR_FG)


class SpinCurvePlot(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.figure = Figure(figsize=(6.4, 4.4), dpi=100, facecolor=style.COLOR_BG_LIGHT, layout="constrained")
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.widget = self.canvas.get_tk_widget()
        self.widget.configure(background=style.COLOR_BG_LIGHT, highlightthickness=0)
        self.widget.pack(fill="both", expand=True)
        draw_spin_curve(self.ax, [])

    def set_data(self, points, band=None, marker=None, y_label_tex: str = r"$h_\mathrm{f}$ [nm]",
                 log_x: bool = True, band_label: str | None = None) -> None:
        draw_spin_curve(self.ax, points, band, marker, y_label_tex, log_x, band_label)
        self.canvas.draw_idle()
