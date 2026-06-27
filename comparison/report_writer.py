"""
report_writer.py
================
Writes the comparison report:

1. **CSV** — per-implant movement table (ΔX, ΔY, ΔZ, 3-D distance after
   rigid-body registration).
2. **PNG** — scatter plot of implant positions: fit-check (hollow markers)
   overlaid with post-op (filled markers) in the post-op coordinate frame,
   with arrows showing each residual movement.

Requires matplotlib and numpy.
"""

import csv
import math
import os


_PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#17becf",
    "#bcbd22", "#7f7f7f",
]


class ComparisonReportWriter:
    """
    Parameters
    ----------
    aligned_points : list[AlignedPoint]
        Output from :func:`~comparison.registrar.register_and_compute_deltas`.
    output_dir : str
        Directory to write report files into (created if absent).
    case_name : str
        Used in file names and plot title.
    """

    def __init__(self, aligned_points: list, output_dir: str, case_name: str = "comparison"):
        self.aligned_points = aligned_points
        self.output_dir = output_dir
        self.case_name = case_name

    # ------------------------------------------------------------------

    def write(self) -> tuple[str, str]:
        """
        Write both report files.

        Returns
        -------
        tuple[str, str]
            ``(csv_path, png_path)``
        """
        os.makedirs(self.output_dir, exist_ok=True)
        csv_path = self._write_csv()
        png_path = self._write_png()
        return csv_path, png_path

    # ------------------------------------------------------------------

    def _write_csv(self) -> str:
        path = os.path.join(self.output_dir, f"{self.case_name}_movement.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([
                "FitCheck_Label", "PostOp_Label",
                "FitCheck_X", "FitCheck_Y", "FitCheck_Z",
                "PostOp_X",    "PostOp_Y",    "PostOp_Z",
                "Delta_X",     "Delta_Y",     "Delta_Z",
                "Distance_3D_mm",
            ])
            for ap in self.aligned_points:
                w.writerow([
                    ap.label_a, ap.label_b,
                    f"{ap.orig_a[0]:.5f}", f"{ap.orig_a[1]:.5f}", f"{ap.orig_a[2]:.5f}",
                    f"{ap.orig_b[0]:.5f}", f"{ap.orig_b[1]:.5f}", f"{ap.orig_b[2]:.5f}",
                    f"{ap.delta_x:+.5f}", f"{ap.delta_y:+.5f}", f"{ap.delta_z:+.5f}",
                    f"{ap.distance_3d:.5f}",
                ])
        print(f"  [CSV] -> {path}")
        return path

    # ------------------------------------------------------------------

    def _write_png(self) -> str:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.lines import Line2D
            from matplotlib.patches import FancyArrowPatch
        except ImportError:
            raise ImportError(
                "matplotlib is required for the PNG report. "
                "Install it with:  pip install matplotlib"
            )

        fig, ax = plt.subplots(figsize=(7, 9))
        ax.set_facecolor("#f8f9fa")
        fig.patch.set_facecolor("white")

        for i, ap in enumerate(self.aligned_points):
            col = _PALETTE[i % len(_PALETTE)]

            # Post-op: filled dot
            bx, by = ap.orig_b[0], ap.orig_b[1]
            ax.plot(bx, by, "o", markersize=18, color=col, zorder=3)

            # Fit-check after registration: hollow dot
            ax_x, ax_y = ap.aligned_a[0], ap.aligned_a[1]
            ax.plot(ax_x, ax_y, "o", markersize=18,
                    markerfacecolor="none", markeredgecolor=col,
                    markeredgewidth=2.5, zorder=3)

            # Arrow: fit-check → post-op (residual movement)
            residual_xy = math.sqrt(ap.delta_x ** 2 + ap.delta_y ** 2)
            if residual_xy > 0.05:
                ax.annotate(
                    "",
                    xy=(bx, by),
                    xytext=(ax_x, ax_y),
                    arrowprops=dict(
                        arrowstyle="-|>",
                        color=col,
                        lw=1.8,
                        mutation_scale=14,
                    ),
                    zorder=4,
                )

            # Label: "FitCheck (PostOp)"
            label_text = f"{ap.label_a}  ({ap.label_b})"
            ax.text(
                bx + 0.6, by + 0.6, label_text,
                fontsize=9, fontweight="bold", color="#111111",
                ha="left", va="bottom", zorder=5,
            )

        # Dashed arch line through post-op points (already in arch order)
        post_xs = [ap.orig_b[0] for ap in self.aligned_points]
        post_ys = [ap.orig_b[1] for ap in self.aligned_points]
        ax.plot(post_xs, post_ys, "--", color="#aaaaaa", linewidth=1.2, zorder=1)

        ax.axhline(0, color="black", linewidth=0.9, zorder=2)
        ax.axvline(0, color="black", linewidth=0.9, zorder=2)
        ax.set_xlabel("X (mm)", fontsize=11)
        ax.set_ylabel("Y (mm)", fontsize=11)
        ax.grid(True, color="#dddddd", linewidth=0.5)
        ax.set_aspect("equal")

        legend_handles = [
            Line2D([0], [0], marker="o", linestyle="none", markersize=10,
                   markerfacecolor="none", markeredgecolor="gray",
                   markeredgewidth=2.5, label="Fit Check (pre-surgery)"),
            Line2D([0], [0], marker="o", linestyle="none", markersize=10,
                   markerfacecolor="gray", label="Post-Op"),
        ]
        ax.legend(handles=legend_handles, loc="best", fontsize=9)

        ax.set_title(
            f"Implant positions\n{self.case_name}",
            fontsize=12, fontweight="bold", pad=12,
        )

        fig.tight_layout()
        path = os.path.join(self.output_dir, f"{self.case_name}_positions.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  [PNG] -> {path}")
        return path
