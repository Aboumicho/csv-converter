"""
pipeline.py
===========
Orchestrates the full fit-check vs post-op comparison.

Usage::

    from comparison import ComparisonPipeline

    csv_path, png_path = ComparisonPipeline(
        fitcheck_csv="path/to/fitcheck.csv",
        postop_txt="path/to/TransformedPoints.txt",
        output_dir="path/to/output/",
    ).run()
"""

import os

from comparison.csv_reader import MicronMapperCSVReader
from comparison.matcher import match_implants, gap_sequences
from comparison.registrar import register_and_compute_deltas
from comparison.report_writer import ComparisonReportWriter


class ComparisonPipeline:
    """
    Parameters
    ----------
    fitcheck_csv : str
        Path to the pre-surgery MicronMapper CSV (fit-check).
    postop_csv : str
        Path to the post-op MicronMapper CSV.
    output_dir : str
        Directory where the report (CSV + PNG) will be written.
    case_name : str, optional
        Used for file names and plot title.  Defaults to the fitcheck stem.
    """

    def __init__(
        self,
        fitcheck_csv: str,
        postop_csv: str,
        output_dir: str,
        case_name: str | None = None,
    ):
        self.fitcheck_csv = fitcheck_csv
        self.postop_csv = postop_csv
        self.output_dir = output_dir
        self.case_name = (
            case_name
            or os.path.splitext(os.path.basename(fitcheck_csv))[0]
        )

    # ------------------------------------------------------------------

    def run(self) -> tuple[str, str]:
        """
        Execute the full pipeline.

        Returns
        -------
        tuple[str, str]
            ``(csv_path, png_path)``
        """
        print(f"\n{'─' * 60}")
        print(f"Fit-check CSV : {os.path.basename(self.fitcheck_csv)}")
        print(f"Post-op CSV   : {os.path.basename(self.postop_csv)}")
        print(f"Output dir    : {self.output_dir}")
        print(f"Case name     : {self.case_name}")

        # 1. Read fit-check implants
        fitcheck_pts = MicronMapperCSVReader(self.fitcheck_csv).read()
        if not fitcheck_pts:
            raise ValueError(
                f"No implant data found in {self.fitcheck_csv!r}. "
                "Check that the file is a valid MicronMapper CSV."
            )
        print(f"Fit-check     : {[p.label for p in fitcheck_pts]}")

        # 2. Read post-op implants
        postop_pts = MicronMapperCSVReader(self.postop_csv).read()
        if not postop_pts:
            raise ValueError(
                f"No implant data found in {self.postop_csv!r}. "
                "Check that the file is a valid MicronMapper CSV."
            )
        print(f"Post-op       : {[p.label for p in postop_pts]}")

        # 3. Gap-match labels
        pairs = match_implants(fitcheck_pts, postop_pts)

        gaps_a, gaps_b = gap_sequences(fitcheck_pts, postop_pts)
        print("\nGap validation (should be near-identical):")
        for i, (ga, gb) in enumerate(zip(gaps_a, gaps_b)):
            print(f"  gap {i+1}: fit-check={ga:.2f} mm  post-op={gb:.2f} mm  diff={abs(ga-gb):.2f} mm")

        print("\nMatched pairs (fit-check → post-op):")
        for p in pairs:
            print(f"  {p.label_a}  →  {p.label_b}")

        # 4. Rigid registration + per-implant residuals
        aligned = register_and_compute_deltas(pairs)

        print("\nMovement residuals after rigid-body registration:")
        for ap in aligned:
            print(
                f"  {ap.label_a}/{ap.label_b}: "
                f"ΔX={ap.delta_x:+.3f}  ΔY={ap.delta_y:+.3f}  "
                f"ΔZ={ap.delta_z:+.3f}  |Δ|={ap.distance_3d:.3f} mm"
            )

        # 5. Write report
        csv_path, png_path = ComparisonReportWriter(
            aligned, self.output_dir, self.case_name
        ).write()

        print(f"\nReport written to: {self.output_dir}")
        return csv_path, png_path
