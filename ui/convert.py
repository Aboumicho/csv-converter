"""
convert.py
==========
ConvertView — the "Convert TXT to CSV" tool panel.
"""

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox

from ui.colors import ACCENT, BG, MUTED
from ui.core import make_card, set_card_enabled


class ConvertView(tk.Frame):
    """
    Self-contained frame for the TXT → CSV conversion tool.

    Parameters
    ----------
    parent : tk.Widget
        The tool_area container from ConcoLabApp.
    project_dir : str
        Project root (contains ``txt_files/`` and ``files/``).
    files_dir : str
        Output directory for generated CSV files.
    """

    def __init__(self, parent: tk.Widget, project_dir: str, files_dir: str):
        super().__init__(parent, bg=BG)
        self.project_dir = project_dir
        self.files_dir = files_dir
        self.generated_csv: str | None = None
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        from csv_writer import FilePipeline  # local import avoids circular deps
        self._FilePipeline = FilePipeline

        grid = tk.Frame(self, bg=BG)
        grid.pack(expand=True)

        self.import_card = make_card(
            grid,
            column=0,
            title="Import TXT",
            subtitle="Click to choose a .txt file",
            glyph="TXT",
            glyph_color=ACCENT,
            command=self._import_txt,
        )

        self.download_card = make_card(
            grid,
            column=1,
            title="Download CSV",
            subtitle="Generate a file first",
            glyph="CSV",
            glyph_color=MUTED,
            command=self._download_csv,
            enabled=False,
        )

        self.status_var = tk.StringVar(value="Waiting for a .txt file...")
        tk.Label(
            self, textvariable=self.status_var,
            bg=BG, fg=MUTED, font=("Segoe UI", 10),
        ).pack(side="bottom", pady=(12, 0))

    # ------------------------------------------------------------------

    def _import_txt(self) -> None:
        txt_path = filedialog.askopenfilename(
            title="Select a TransformedPoints .txt file",
            initialdir=os.path.join(self.project_dir, "txt_files"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not txt_path:
            return

        self.status_var.set(f"Converting {os.path.basename(txt_path)} ...")
        self.update_idletasks()

        try:
            csv_path = self._FilePipeline(
                txt_path=txt_path,
                project_dir=self.project_dir,
                output_dir=self.files_dir,
            ).run()
        except Exception as exc:
            self.status_var.set("Conversion failed.")
            messagebox.showerror("Conversion failed", str(exc))
            return

        self.generated_csv = csv_path
        set_card_enabled(self.download_card, True)
        self.download_card["subtitle"].configure(
            text=f"Ready: {os.path.basename(csv_path)}"
        )
        self.status_var.set(f"CSV generated in /files: {os.path.basename(csv_path)}")

    def _download_csv(self) -> None:
        if not self.generated_csv or not os.path.exists(self.generated_csv):
            messagebox.showwarning(
                "No CSV available", "Import and convert a .txt file first."
            )
            return

        dest = filedialog.asksaveasfilename(
            title="Save CSV as",
            defaultextension=".csv",
            initialfile=os.path.basename(self.generated_csv),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not dest:
            return

        try:
            shutil.copyfile(self.generated_csv, dest)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))
            return

        self.status_var.set(f"Saved to {dest}")
        messagebox.showinfo("Saved", f"CSV saved to:\n{dest}")
