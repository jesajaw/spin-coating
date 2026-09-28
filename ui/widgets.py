"""
Reusable UI building blocks for Spin-Coating app.
"""
import tkinter as tk
from tkinter import ttk
from . import style

class Cell(ttk.Frame):
    """Clickable tile card with hover effect."""
    def __init__(self, parent, title: str, on_click=None, status_text: str | None = None, width: int = style.CELL_WIDTH, height: int = style.CELL_HEIGHT):
        super().__init__(parent, padding=8, relief="groove", style="Cell.TFrame")
        self.on_click = on_click
        self.pack_propagate(False)
        self.configure(width=width, height=height)
        
        self.title_label = ttk.Label(self, text=title, style="CellTitle.TLabel")
        self.title_label.pack(anchor="w")
        
        self.status_label = None
        clickable = [self, self.title_label]
        
        if status_text is not None:
            self.status_label = ttk.Label(self, text=status_text, style="Status.TLabel", wraplength=width - 20, justify="left")
            self.status_label.pack(anchor="w", pady=(4, 8), fill="x")
            clickable.append(self.status_label)
            
        if on_click is not None:
            for w in clickable:
                w.configure(cursor="hand2")
                w.bind("<Button-1>", lambda e: self._on_click())
                w.bind("<Enter>", lambda e: self._on_enter())
                w.bind("<Leave>", lambda e: self._on_leave())

    def set_status(self, text: str) -> None:
        if self.status_label:
            self.status_label.configure(text=text)

    def _on_click(self) -> None:
        if self.on_click:
            self.on_click()

    def _on_enter(self) -> None:
        self.configure(style="CellHover.TFrame")
        self.title_label.configure(style="CellTitleHover.TLabel")
        if self.status_label:
            self.status_label.configure(style="StatusHover.TLabel")

    def _on_leave(self) -> None:
        self.configure(style="Cell.TFrame")
        self.title_label.configure(style="CellTitle.TLabel")
        if self.status_label:
            self.status_label.configure(style="Status.TLabel")

class ResultDisplay(ttk.Frame):
    """Compact result panel with quick copy-to-clipboard button."""
    def __init__(self, parent, label: str = "Computed Result", initial_text: str = "--"):
        super().__init__(parent)
        box = ttk.LabelFrame(self, text=label, padding=10)
        box.pack(fill="x")
        
        ttk.Button(box, text="📋 Copy", style="Icon.TButton", command=self._copy).pack(anchor="e")
        self.value_label = ttk.Label(box, text=initial_text, style="ResultText.TLabel", wraplength=350, justify="center")
        self.value_label.pack(fill="x", pady=(0, 8))

    def set_text(self, text: str) -> None:
        self.value_label.configure(text=text)

    def get_text(self) -> str:
        return self.value_label.cget("text")

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.get_text())

class LabeledEntry(ttk.Frame):
    """Convenience label + entry field pair."""
    def __init__(self, parent, label: str, default_value: str = ""):
        super().__init__(parent)
        ttk.Label(self, text=label, width=22, anchor="w").pack(side="left")
        self.entry = ttk.Entry(self)
        self.entry.insert(0, default_value)
        self.entry.pack(side="left", fill="x", expand=True)

    def get(self) -> str:
        return self.entry.get().strip()

    def set(self, val: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, val)