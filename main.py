"""
main.py
=======
Entry point for ConcoLab - converts TransformedPoints ``.txt`` files into
MicronMapper-compatible CSV files.

Directory layout
----------------
  PROJECT_DIR/
    txt_files/        <- drop .txt input files here
    files/            <- generated .csv outputs (created automatically)
    csv_writer/       <- conversion package
    ui/               <- tkinter interface

Usage
-----
  # Use current working directory as project root
  python main.py

  # Specify an explicit project directory
  python main.py /path/to/project

  # Override the camera serial written to the CSV footer
  python main.py /path/to/project --camera 24902386
"""

import argparse
import os
import sys

from csv_writer import DiscoveryPipeline, DEFAULT_CAMERA_SERIAL


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert TransformedPoints .txt files to MicronMapper CSV. "
            "Reads from PROJECT_DIR/txt_files/ and writes to PROJECT_DIR/files/."
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
    return parser.parse_args()

def main() -> None:
    args = _parse_args()
    pipeline = DiscoveryPipeline(
        project_dir=args.project_dir,
        camera_serial=args.camera_serial,
    )
    results = pipeline.run()
    if pipeline.has_failures(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
