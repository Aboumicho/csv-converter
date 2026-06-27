"""
file_pipeline.py
================
Processes a single TransformedPoints ``.txt`` file into a MicronMapper CSV.
"""

import os

from csv_writer.file_reader import TxtReader, all_divergence_pairs
from csv_writer.csv_writer import MicronMapperCSVWriter

DEFAULT_CAMERA_SERIAL = "00000000"


class FilePipeline:
    """
    Processes one TransformedPoints ``.txt`` file and writes the CSV output
    into ``output_dir`` (defaults to ``PROJECT_DIR/files``).

    Parameters
    ----------
    txt_path : str
        Path to the source ``.txt`` file.
    project_dir : str
        Root project directory (parent of ``txt_files/`` and ``files/``).
    camera_serial : str
        Camera serial number for the CSV metadata footer.
    output_dir : str, optional
        Explicit output directory. When omitted, ``project_dir/files`` is used.
    """

    def __init__(
        self,
        txt_path: str,
        project_dir: str,
        camera_serial: str = DEFAULT_CAMERA_SERIAL,
        output_dir: str | None = None,
    ):
        self.txt_path = txt_path
        self.project_dir = project_dir
        self.camera_serial = camera_serial
        self.output_dir = output_dir or os.path.join(project_dir, "files")

    # ----------------------------------------------------------
    def run(self) -> str:
        """
        Read the ``.txt`` file, compute frames and write the CSV.

        Returns
        -------
        str
            Path to the written ``.csv`` file.
        """
        stem = os.path.splitext(os.path.basename(self.txt_path))[0]

        print(f"\n{'-' * 60}")
        print(f"File       : {os.path.basename(self.txt_path)}")
        print(f"Output dir : {self.output_dir}")

        # 1. Parse all frames from the .txt file
        frames = TxtReader(self.txt_path).read()
        if not frames:
            raise ValueError(f"No valid coordinate frames found in {self.txt_path!r}")
        print(f"Frames     : {[f.prefix for f in frames]}")

        # 2. Print divergence table
        pairs = all_divergence_pairs(frames)
        if pairs:
            print("Divergence angles (all pairs, highest first):")
            max_pair = (pairs[0][1], pairs[0][2])
            for angle, pa, pb in pairs:
                tag = " <- MAX" if (pa, pb) == max_pair else ""
                print(f"  {pa}-{pb}: {angle:.2f} deg{tag}")

        # 3. Write CSV
        csv_path = os.path.join(self.output_dir, f"{stem}.csv")
        MicronMapperCSVWriter(
            frames, csv_path, camera_serial=self.camera_serial
        ).write()

        return csv_path
