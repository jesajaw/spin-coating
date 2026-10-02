r"""
Formatted maths for Tk labels without a LaTeX installation: matplotlib's mathtext renders a string such as
``"Viscosity $\eta$ [$\mathrm{cP}$]"`` to a PNG which is shown in a ttk.Label.

The PNG is NOT transparent (matplotlib paints the figure background into it, white by default), so it is
rendered on the background colour of the widget it is shown in (`bg`) -- otherwise every label gets a white box.

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


def png_bytes(text: str, size_pt: float, color: str, dpi: float, bg: str = style.COLOR_BG) -> bytes:
    """PNG of the mathtext string: `color` text on an opaque `bg` background."""
    import matplotlib
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image
    buf = io.BytesIO()
    # math_to_image builds its own Figure; its background comes from these two rc parameters
    with matplotlib.rc_context({"figure.facecolor": bg, "savefig.facecolor": bg}):
        math_to_image(text, buf, prop=FontProperties(size=size_pt), dpi=dpi, format="png", color=color)
    return buf.getvalue()


def render(text: str, size_pt: float | None = None, color: str | None = None,
           bg: str | None = None) -> tk.PhotoImage | None:
    """Cached PhotoImage of `text` on background `bg`, or None if it cannot be rendered."""
    size_pt = size_pt or style.TEX_SIZE
    color = color or style.COLOR_FG
    bg = bg or style.COLOR_BG
    key = (text, size_pt, color, bg, style.tex_dpi())
    img = _cache.get(key)
    if img is None:
        try:
            img = tk.PhotoImage(data=base64.b64encode(png_bytes(text, size_pt, color, style.tex_dpi(), bg)))
        except Exception:
            return None
        _cache[key] = img
    return img


def wrap_tex(text: str, width_chars: int) -> list[str]:
    """
    Greedy line wrap of a string with $...$ segments. A formula is never split, and punctuation that sticks to a
    formula (``$h_0$:``) stays with it. Length is estimated from the readable form of the text.
    """
    atoms = [(m.group(0), m.start()) for m in re.finditer(r"\$[^$]*\$|[^\s$]+", text)]
    lines: list[str] = []
    current, current_len, prev_end = "", 0, None
    for atom, start in atoms:
        glued = prev_end is not None and start == prev_end
        prev_end = start + len(atom)
        n = len(plain(atom))
        if current and not glued and current_len + 1 + n > width_chars:
            lines.append(current)
            current, current_len = atom, n
        elif current:
            current += atom if glued else " " + atom
            current_len += n + (0 if glued else 1)
        else:
            current, current_len = atom, n
    if current:
        lines.append(current)
    return lines


class TexLabel(ttk.Label):
    """
    ttk.Label that shows mathtext; `set_text` re-renders. The image is rendered on the background colour of
    `style_name`, so the label looks transparent on its parent as long as the style's background matches it.
    """

    def __init__(self, parent, text: str = "", size: float | None = None, color: str | None = None,
                 style_name: str = "TLabel", wraplength: int = 0, **kw):
        super().__init__(parent, style=style_name, **kw)
        self._size, self._color, self._wrap = size, color, wraplength
        try:
            self._bg = ttk.Style(self).lookup(style_name, "background") or style.COLOR_BG
        except Exception:
            self._bg = style.COLOR_BG
        self.set_text(text)

    def set_text(self, text: str, color: str | None = None) -> None:
        if color is not None:
            self._color = color
        img = render(text, self._size, self._color, self._bg) if text else None
        if img is not None:
            self.configure(image=img, text="")
            self.image = img            # keep a reference (also held by the cache)
        else:
            self.configure(image="", text=plain(text), wraplength=self._wrap)
            self.image = None


class TexParagraph(ttk.Frame):
    """A paragraph that mixes text and $...$ formulas, wrapped to `width_chars` (one TexLabel per line)."""

    def __init__(self, parent, text: str, width_chars: int = 86, size: float | None = None,
                 color: str | None = None, style_name: str = "Body.TLabel"):
        super().__init__(parent)
        for line in wrap_tex(text, width_chars):
            TexLabel(self, line, size=size, color=color, style_name=style_name).pack(anchor="w")
