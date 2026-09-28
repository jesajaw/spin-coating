"""
Application entry point for Spin-Coating UI.
"""
from .ui.layout import SpinCoatingApp

def main() -> None:
    app = SpinCoatingApp()
    app.mainloop()

if __name__ == "__main__":
    main()