"""
csv_writer.py
=============
Responsible for writing a MicronMapper-compatible CSV file from a list of
CoordinateFrame objects.

Output format
-------------
Each data row:
    PREFIX, X, Y, Z, nx, ny, nz, tx, ty, tz

Followed by a metadata footer:
    Max divergence angle: PREFIX_A-PREFIX_B  <angle> deg
    Application:, MicronMapper V1.5.0.41871, ...
    Camera:, <serial>

Public API
----------
  MicronMapperCSVWriter(frames, output_path, camera_serial).write()
      -> str  (path to the written file)
"""

import os
from datetime import datetime

from file_reader import CoordinateFrame, max_divergence


class MicronMapperCSVWriter:
    """
    Writes a MicronMapper-compatible CSV for a list of CoordinateFrame objects.

    Parameters
    ----------
    frames : list[CoordinateFrame]
        Frames to serialise, one CSV row each.
    output_path : str
        Destination path for the .csv file.
    camera_serial : str
        Camera serial number written to the metadata footer (default '00000000').
    """

    APPLICATION = "MicronMapper V1.5.0.41871, built 6/5/2025"

    def __init__(
        self,
        frames: list[CoordinateFrame],
        output_path: str,
        camera_serial: str = "00000000",
    ):
        self.frames      = frames
        self.output_path = output_path
        self.camera      = camera_serial

    # ----------------------------------------------------------
    # Public
    # ----------------------------------------------------------

    def write(self) -> str:
        """
        Serialise all frames to a MicronMapper CSV and write to disk.

        Returns
        -------
        str : absolute path to the written file.
        """
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        angle, pa, pb = max_divergence(self.frames)

        with open(self.output_path, "w", newline="", encoding="utf-8") as fh:
            self._write_data_rows(fh)
            self._write_divergence(fh, angle, pa, pb)
            self._write_metadata(fh)

        print(f"  [CSV] -> {self.output_path}")
        return self.output_path

    # ----------------------------------------------------------
    # Private
    # ----------------------------------------------------------

    def _write_data_rows(self, fh) -> None:
        """One row per frame: PREFIX, X, Y, Z, nx, ny, nz, tx, ty, tz."""
        for f in self.frames:
            ox, oy, oz = f.origin
            nx, ny, nz = f.z_axis   # normal  (Z axis)
            tx, ty, tz = f.x_axis   # tangent (X axis)
            fh.write(
                f"{f.prefix},"
                f" {ox:.5f}, {oy:.5f}, {oz:.5f},"
                f"{nx:.6f},{ny:.6f},{nz:.6f},"
                f"{tx:.6f}, {ty:.6f}, {tz:.6f}\r\n"
            )
        fh.write("\r\n")

    def _write_divergence(self, fh, angle: float, pa, pb) -> None:
        """Write the Max divergence angle line."""
        if pa is not None:
            fh.write(f"Max divergence angle: {pa}-{pb} {angle:.1f} deg\r\n")
        else:
            fh.write("Max divergence angle: N/A\r\n")
        fh.write("\r\n")

    def _write_metadata(self, fh) -> None:
        """Write Application and Camera footer lines."""
        now_str = datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")
        fh.write(f"Application:, {self.APPLICATION},   now {now_str}\r\n")
        fh.write(f"Camera:, {self.camera}\r\n")
