"""
Entry point. The actual app lives in src/ -- main.py stays deliberately
thin so the architecture (model/ui/data) is visible at a glance.

This is a *script* (always run as __main__), so it must use an absolute
import here, never a relative one (`from .src import app` would fail --
a script has no parent package for a leading dot to refer to).

Start:
    pip install -r requirements.txt
    python main.py
"""

from src import app

if __name__ == "__main__":
    app.main()
