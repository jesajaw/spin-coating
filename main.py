"""
Entry point. The actual app lives in src/ -- main.py stays deliberately
thin so the architecture (config/calc/stat/ui/resins) is visible at a
glance.

Start:
    pip install -r requirements.txt
    python main.py
"""

from src.app import main

if __name__ == "__main__":
    main()
