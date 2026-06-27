"""
app.py
======
ConcoLab — main application window.

Run from the project root::

    python -m ui.app
    # or
    python ui/app.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk

# Allow running as a plain script (python ui/app.py) as well as a module.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from ui.colors import (  # noqa: E402
    ACCENT, APP_TITLE, BG, CARD, MUTED, TEXT,
    TOOL_COMPARE, TOOL_TXT_TO_CSV,
)
from ui.convert import ConvertView  # noqa: E402
from ui.compare import CompareView  # noqa: E402


class ConcoLabApp(tk.Tk):
    """Main ConcoLab application window."""

    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=BG)
        self.geometry("960x540")
        self.minsize(900, 500)

        self.files_dir = os.path.join(PROJECT_DIR, "files")

        self._build_styles()
        self._build_header()
        self._build_selector()

        self.tool_area = tk.Frame(self, bg=BG)
        self.tool_area.pack(fill="both", expand=True, padx=24, pady=(8, 24))

        self._show_placeholder()

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------
    def _build_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Tool.TCombobox",
            fieldbackground=CARD,
            background=CARD,
            foreground=TEXT,
            arrowcolor=ACCENT,
            bordercolor=CARD,
            lightcolor=CARD,
            darkcolor=CARD,
            padding=8,
        )
        self.option_add("*TCombobox*Listbox.background", CARD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.option_add("*TCombobox*Listbox.selectForeground", BG)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(24, 8))

        tk.Label(
            header, text=APP_TITLE, bg=BG, fg=TEXT,
            font=("Segoe UI Semibold", 26),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="TransformedPoints conversion toolkit",
            bg=BG, fg=MUTED, font=("Segoe UI", 11),
        ).pack(anchor="w")

    # ------------------------------------------------------------------
    # Tool selector
    # ------------------------------------------------------------------
    def _build_selector(self) -> None:
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=24, pady=(8, 0))

        tk.Label(
            bar, text="Tool", bg=BG, fg=MUTED, font=("Segoe UI", 10),
        ).pack(anchor="w")

        self.tool_var = tk.StringVar(value="")
        self.tool_select = ttk.Combobox(
            bar,
            textvariable=self.tool_var,
            values=[TOOL_TXT_TO_CSV, TOOL_COMPARE],
            state="readonly",
            style="Tool.TCombobox",
            font=("Segoe UI", 11),
        )
        self.tool_select.pack(fill="x", pady=(4, 0))
        self.tool_select.bind("<<ComboboxSelected>>", self._on_tool_change)

    # ------------------------------------------------------------------
    # View orchestration
    # ------------------------------------------------------------------
    def _clear_tool_area(self) -> None:
        for child in self.tool_area.winfo_children():
            child.destroy()

    def _show_placeholder(self) -> None:
        self._clear_tool_area()
        tk.Label(
            self.tool_area,
            text="Select a tool above to get started.",
            bg=BG, fg=MUTED, font=("Segoe UI", 12),
        ).pack(expand=True)

    def _on_tool_change(self, _event=None) -> None:
        self._clear_tool_area()
        tool = self.tool_var.get()
        if tool == TOOL_TXT_TO_CSV:
            ConvertView(self.tool_area, PROJECT_DIR, self.files_dir).pack(
                fill="both", expand=True
            )
        elif tool == TOOL_COMPARE:
            CompareView(self.tool_area, PROJECT_DIR, self.files_dir).pack(
                fill="both", expand=True
            )


def main() -> None:
    ConcoLabApp().mainloop()


if __name__ == "__main__":
    main()
