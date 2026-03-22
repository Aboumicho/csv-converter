"""
main.py
=======
Entry point for the TransformedPoints conversion pipeline.

Directory layout expected / produced
--------------------------------------
  PROJECT_DIR/
    txt_files/                  <- drop .txt input files here
      TransformedPoints.txt
      TransformedPoints_32.txt
      ...
    files/                      <- generated outputs (created automatically)
      TransformedPoints/
        TransformedPoints.csv
        TransformedPoints.stl
      TransformedPoints_32/
        TransformedPoints_32.csv
        TransformedPoints_32.stl
      ...

Usage
-----
  # Use current working directory as project root
  python main.py

  # Specify an explicit project directory
  python main.py /path/to/project

  # Override camera serial and axis length
  python main.py /path/to/project --camera 24902386 --axis-length 8.0

Configuration (edit defaults below if you prefer not to use CLI flags)
----------------------------------------------------------------------
  DEFAULT_CAMERA_SERIAL  – camera serial written to every CSV footer
  DEFAULT_AXIS_LENGTH    – length of STL axis arms in millimetres
"""

import argparse
import glob
import os
import sys

from file_reader import TxtReader, all_divergence_pairs
from csv_writer  import MicronMapperCSVWriter
from stl_writer  import STLWriter

# ---------------------------------------------------------------------------
# Defaults  (override via CLI flags or edit here)
# ---------------------------------------------------------------------------

DEFAULT_CAMERA_SERIAL = "00000000"
DEFAULT_AXIS_LENGTH   = 10.0


# ============================================================
#  FilePipeline  –  processes a single .txt file
# ============================================================

class FilePipeline:
    """
    Processes one TransformedPoints .txt file and writes both output files
    into PROJECT_DIR/files/<stem>/.

    Parameters
    ----------
    txt_path : str
        Path to the source .txt file.
    project_dir : str
        Root project directory (parent of 'txt_files/' and 'files/').
    camera_serial : str
        Camera serial number for the CSV metadata footer.
    axis_length : float
        Length of each axis arm in the generated STL (millimetres).
    """

    def __init__(
        self,
        txt_path: str,
        project_dir: str,
        camera_serial: str = DEFAULT_CAMERA_SERIAL,
        axis_length: float = DEFAULT_AXIS_LENGTH,
    ):
        self.txt_path      = txt_path
        self.project_dir   = project_dir
        self.camera_serial = camera_serial
        self.axis_length   = axis_length

    # ----------------------------------------------------------
    def run(self) -> tuple[str, str]:
        """
        Read the .txt file, compute frames, write CSV and STL.

        Returns
        -------
        (csv_path, stl_path)
        """
        stem       = os.path.splitext(os.path.basename(self.txt_path))[0]
        output_dir = os.path.join(self.project_dir, "files", stem)

        print(f"\n{'─' * 60}")
        print(f"File       : {os.path.basename(self.txt_path)}")
        print(f"Output dir : {output_dir}")

        # 1. Parse all frames from the .txt file
        frames = TxtReader(self.txt_path).read()
        print(f"Frames     : {[f.prefix for f in frames]}")

        # 2. Print divergence table
        pairs = all_divergence_pairs(frames)
        if pairs:
            print("Divergence angles (all pairs, highest first):")
            max_pair = (pairs[0][1], pairs[0][2])
            for angle, pa, pb in pairs:
                tag = " <- MAX" if (pa, pb) == max_pair else ""
                print(f"  {pa}-{pb}: {angle:.2f}°{tag}")

        # 3. Write CSV
        csv_path = os.path.join(output_dir, f"{stem}.csv")
        MicronMapperCSVWriter(
            frames, csv_path, camera_serial=self.camera_serial
        ).write()

        # 4. Write STL
        stl_path = os.path.join(output_dir, f"{stem}.stl")
        STLWriter(
            frames, stl_path, axis_length=self.axis_length
        ).write()

        return csv_path, stl_path


# ============================================================
#  DiscoveryPipeline  –  scans PROJECT_DIR/txt_files/
# ============================================================

class DiscoveryPipeline:
    """
    Discovers every .txt file inside PROJECT_DIR/txt_files/ and runs
    FilePipeline on each one.

    Parameters
    ----------
    project_dir : str
        Root project directory.
    camera_serial : str
        Forwarded to FilePipeline / MicronMapperCSVWriter.
    axis_length : float
        Forwarded to FilePipeline / STLWriter.
    """

    TXT_SUBDIR = "txt_files"

    def __init__(
        self,
        project_dir: str,
        camera_serial: str = DEFAULT_CAMERA_SERIAL,
        axis_length: float = DEFAULT_AXIS_LENGTH,
    ):
        self.project_dir   = os.path.abspath(project_dir)
        self.camera_serial = camera_serial
        self.axis_length   = axis_length

    # ----------------------------------------------------------
    def run(self) -> None:
        """Scan for .txt files, process each one, print a summary."""
        txt_dir = os.path.join(self.project_dir, self.TXT_SUBDIR)
        files   = sorted(glob.glob(os.path.join(txt_dir, "*.txt")))

        if not files:
            print(f"[INFO] No .txt files found in '{txt_dir}'. Exiting.")
            return

        print(f"Project dir   : {self.project_dir}")
        print(f"Input dir     : {txt_dir}")
        print(f"Files found   : {[os.path.basename(f) for f in files]}")
        print(f"Camera serial : {self.camera_serial}")
        print(f"Axis length   : {self.axis_length} mm")

        results = []
        for txt_path in files:
            try:
                csv_path, stl_path = FilePipeline(
                    txt_path      = txt_path,
                    project_dir   = self.project_dir,
                    camera_serial = self.camera_serial,
                    axis_length   = self.axis_length,
                ).run()
                results.append((txt_path, csv_path, stl_path, None))
            except Exception as exc:
                print(f"  [ERROR] {exc}")
                results.append((txt_path, None, None, exc))

        self._print_summary(results)

    # ----------------------------------------------------------
    def _print_summary(self, results: list) -> None:
        ok  = sum(1 for *_, e in results if e is None)
        err = len(results) - ok
        print(f"\n{'=' * 60}")
        print(f"Done: {ok} succeeded, {err} failed.")
        if ok:
            print(f"Outputs written to: {os.path.join(self.project_dir, 'files', '<FILE_STEM>')}/")
        if err:
            for txt_path, *_, exc in results:
                if exc:
                    print(f"  FAILED: {os.path.basename(txt_path)} – {exc}")
        print("=" * 60)


# ============================================================
#  CLI
# ============================================================

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert TransformedPoints .txt files to MicronMapper CSV + binary STL.\n"
            "Reads from PROJECT_DIR/txt_files/  and writes to "
            "PROJECT_DIR/files/<FILE_STEM>/."
        )
    )
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=os.getcwd(),
        help="Root project directory (default: current working directory).",
    )
    parser.add_argument(
        "--camera",
        dest="camera_serial",
        default=DEFAULT_CAMERA_SERIAL,
        help=f"Camera serial number for CSV footer (default: {DEFAULT_CAMERA_SERIAL}).",
    )
    parser.add_argument(
        "--axis-length",
        dest="axis_length",
        type=float,
        default=DEFAULT_AXIS_LENGTH,
        help=f"STL axis arm length in mm (default: {DEFAULT_AXIS_LENGTH}).",
    )
    return parser.parse_args()


# ============================================================
#  Entry-point
# ============================================================

def main() -> None:
    args = _parse_args()
    DiscoveryPipeline(
        project_dir   = args.project_dir,
        camera_serial = args.camera_serial,
        axis_length   = args.axis_length,
    ).run()


if __name__ == "__main__":
    main()
