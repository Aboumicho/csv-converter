"""
compare.py
==========
CompareView — the "Compare Fit Check vs Post-Op" tool panel.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from ui.colors import ACCENT, BG, MUTED
from ui.core import make_card, set_card_enabled


class CompareView(tk.Frame):
    """
    Self-contained frame for the fit-check vs post-op comparison tool.

    Parameters
    ----------
    parent : tk.Widget
        The tool_area container from ConcoLabApp.
    project_dir : str
        Project root directory.
    files_dir : str
        Output directory (``PROJECT_DIR/files/``).
    """

    def __init__(self, parent: tk.Widget, project_dir: str, files_dir: str):
        super().__init__(parent, bg=BG)
        self.project_dir = project_dir
        self.files_dir = files_dir
        self.fitcheck_path: str | None = None
        self.postop_path: str | None = None
        self._build()

    # ------------------------------------------------------------------

    def _build(self) -> None:
        from comparison import ComparisonPipeline  # local import avoids circular deps
        self._ComparisonPipeline = ComparisonPipeline

        grid = tk.Frame(self, bg=BG)
        grid.pack(expand=True)

        self.fitcheck_card = make_card(
            grid,
            column=0,
            title="Fit Check",
            subtitle="Click to choose a .csv file",
            glyph="CSV",
            glyph_color=ACCENT,
            command=self._import_fitcheck,
        )

        self.postop_card = make_card(
            grid,
            column=1,
            title="Post-Op",
            subtitle="Click to choose a .csv file",
            glyph="CSV",
            glyph_color=ACCENT,
            command=self._import_postop,
        )

        self.report_card = make_card(
            grid,
            column=2,
            title="Generate Report",
            subtitle="Load both files first",
            glyph="RPT",
            glyph_color=MUTED,
            command=self._generate_report,
            enabled=False,
        )

        self.status_var = tk.StringVar(value="Load a Fit Check CSV and a Post-Op CSV to begin.")
        tk.Label(
            self, textvariable=self.status_var,
            bg=BG, fg=MUTED, font=("Segoe UI", 10),
        ).pack(side="bottom", pady=(12, 0))

    # ------------------------------------------------------------------

    def _import_fitcheck(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Fit Check CSV",
            initialdir=self.files_dir,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.fitcheck_path = path
        self.fitcheck_card["subtitle"].configure(text=os.path.basename(path))
        set_card_enabled(self.fitcheck_card, True)
        self._maybe_unlock_report()
        self.status_var.set(f"Fit Check loaded: {os.path.basename(path)}")

    def _import_postop(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Post-Op MicronMapper CSV",
            initialdir=self.files_dir,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        self.postop_path = path
        self.postop_card["subtitle"].configure(text=os.path.basename(path))
        set_card_enabled(self.postop_card, True)
        self._maybe_unlock_report()
        self.status_var.set(f"Post-Op loaded: {os.path.basename(path)}")

    def _maybe_unlock_report(self) -> None:
        if self.fitcheck_path and self.postop_path:
            set_card_enabled(self.report_card, True)
            self.report_card["subtitle"].configure(text="Click to generate report")

    def _generate_report(self) -> None:
        if not self.fitcheck_path or not self.postop_path:
            messagebox.showwarning("Missing files", "Load both Fit Check and Post-Op files first.")
            return

        case_name = os.path.splitext(os.path.basename(self.fitcheck_path))[0]
        output_dir = os.path.join(self.files_dir, case_name)

        self.status_var.set("Generating report...")
        self.update_idletasks()

        try:
            csv_path, png_path = self._ComparisonPipeline(
                fitcheck_csv=self.fitcheck_path,
                postop_csv=self.postop_path,
                output_dir=output_dir,
                case_name=case_name,
            ).run()
        except Exception as exc:
            self.status_var.set("Report generation failed.")
            messagebox.showerror("Report failed", str(exc))
            return

        self.report_card["subtitle"].configure(text="Report ready — see /files")
        self.status_var.set(
            f"Report written to files/{case_name}/ — "
            f"{os.path.basename(csv_path)}, {os.path.basename(png_path)}"
        )
        messagebox.showinfo(
            "Report generated",
            f"Files written to:\n{output_dir}\n\n"
            f"  {os.path.basename(csv_path)}\n"
            f"  {os.path.basename(png_path)}",
        )
        os.startfile(output_dir)
