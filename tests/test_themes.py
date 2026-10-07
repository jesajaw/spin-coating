"""Theme palettes: complete and readable (WCAG contrast). No display needed. The real-display check is gui_theme_check.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui import style  # noqa: E402


def _lum(hex_color: str) -> float:
    r, g, b = (int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_every_theme_defines_the_same_keys():
    keys = [set(sc) for sc in style._SCHEMES.values()]
    assert all(k == keys[0] for k in keys)
    assert {"BG", "BG_LIGHT", "FG", "ACCENT", "ACCENT_DARK", "STATUS_TEXT", "GRID"} <= keys[0]


def test_text_is_readable_in_every_theme():
    for name, sc in style._SCHEMES.items():
        assert contrast(sc["FG"], sc["BG"]) >= 7, name
        assert contrast(sc["FG"], sc["BG_LIGHT"]) >= 7, name
        assert contrast(sc["STATUS_TEXT"], sc["BG"]) >= 4.5, name
        assert contrast(sc["STATUS_TEXT"], sc["BG_LIGHT"]) >= 4.5, name
        assert contrast(sc["FG"], sc["ACCENT_DARK"]) >= 4.5, name      # selected tab, accent button, slider fill
        assert contrast(style.COLOR_ERROR, sc["BG"]) >= 4.5, name


def test_unknown_theme_name_is_rejected():
    import importlib
    import os
    os.environ["SPIN_COATING_THEME"] = "nope"
    try:
        try:
            importlib.reload(style)
        except ValueError as e:
            assert "dark_purple" in str(e)
        else:
            raise AssertionError("expected ValueError")
    finally:
        del os.environ["SPIN_COATING_THEME"]
        importlib.reload(style)
