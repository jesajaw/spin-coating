r"""
Formatted maths for Tk labels without a LaTeX installation: matplotlib's mathtext renders a string such as
``"Viscosity $\eta$ [$\mathrm{cP}$]"`` to a transparent PNG which is shown in a ttk.Label.

Plain text and $...$ segments can be mixed. If rendering fails for any reason the label falls back to the
text with the TeX commands stripped, so a bad formula never breaks the window.
"""

from __future__ import annotations

import base64
import io
import re
import tkinter as tk
from tkinter import ttk

from . import style

_cache: dict[tuple, tk.PhotoImage] = {}


def plain(text: str) -> str:
    """Readable fallback: $...$ markers and TeX commands removed."""
    text = text.replace("$", "")
    text = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:text|mathit)\{([^}]*)\}", r"\1", text)
    text = text.replace("\\pm", "±").replace("\\mu", "µ").replace("\\omega", "ω").replace("\\eta", "η") \
               .replace("\\rho", "ρ").replace("\\kappa", "κ").replace("\\varphi", "φ").replace("\\phi", "φ") \
               .replace("\\to", "→").replace("\\infty", "∞").replace("\\%", "%")
    return re.sub(r"[\\{}]", "", text)


def png_bytes(text: str, size_pt: float, color: str, dpi: float) -> bytes:
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image
    buf = io.BytesIO()
    math_to_image(text, buf, prop=FontProperties(size=size_pt), dpi=dpi, format="png", color=color)
    return buf.getvalue()


def render(text: str, size_pt: float | None = None, color: str | None = None) -> tk.PhotoImage | None:
    """Cached PhotoImage of `text`, or None if it cannot be rendered."""
    size_pt = size_pt or style.TEX_SIZE
    color = color or style.COLOR_FG
    key = (text, size_pt, color, style.tex_dpi())
    img = _cache.get(key)
    if img is None:
        try:
            img = tk.PhotoImage(data=base64.b64encode(png_bytes(text, size_pt, color, style.tex_dpi())))
        except Exception:
            return None
        _cache[key] = img
    return img


class TexLabel(ttk.Label):
    """ttk.Label that shows mathtext; `set_text` re-renders. `style_name` should match the parent's background."""

    def __init__(self, parent, text: str = "", size: float | None = None, color: str | None = None,
                 style_name: str = "TLabel", wraplength: int = 0, **kw):
        super().__init__(parent, style=style_name, **kw)
        self._size, self._color, self._wrap = size, color, wraplength
        self.set_text(text)

    def set_text(self, text: str, color: str | None = None) -> None:
        if color is not None:
            self._color = color
        img = render(text, self._size, self._color) if text else None
        if img is not None:
            self.configure(image=img, text="")
            self.image = img            # keep a reference (also held by the cache)
        else:
            self.configure(image="", text=plain(text), wraplength=self._wrap)
            self.image = None
