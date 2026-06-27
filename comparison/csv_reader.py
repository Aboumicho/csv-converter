"""
csv_reader.py
=============
Reads a MicronMapper-compatible CSV (fit-check export) and returns a list
of :class:`ImplantPoint` objects.

Expected row format (comma-delimited)::

    LABEL, X, Y, Z, nx, ny, nz, tx, ty, tz

Blank lines and non-data footer lines are skipped automatically.
"""

from dataclasses import dataclass, field


@dataclass
class ImplantPoint:
    """Parsed implant entry from a MicronMapper CSV row."""

    label: str
    x: float
    y: float
    z: float
    nx: float = field(default=0.0)
    ny: float = field(default=0.0)
    nz: float = field(default=0.0)
    tx: float = field(default=0.0)
    ty: float = field(default=0.0)
    tz: float = field(default=0.0)

    def __repr__(self) -> str:
        return f"ImplantPoint(label={self.label!r}, x={self.x:.3f}, y={self.y:.3f}, z={self.z:.3f})"


class MicronMapperCSVReader:
    """
    Reads a MicronMapper CSV file and returns a list of :class:`ImplantPoint`
    objects.

    Parameters
    ----------
    filepath : str
        Path to the .csv file.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> list[ImplantPoint]:
        """
        Parse the CSV and return one :class:`ImplantPoint` per implant row.

        Returns
        -------
        list[ImplantPoint]
            Points in file order.
        """
        points: list[ImplantPoint] = []

        with open(self.filepath, newline="", encoding="utf-8-sig") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue

                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 4:
                    continue

                label = parts[0]
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    z = float(parts[3])
                except ValueError:
                    continue

                floats: list[float] = []
                for p in parts[4:10]:
                    try:
                        floats.append(float(p))
                    except ValueError:
                        floats.append(0.0)
                while len(floats) < 6:
                    floats.append(0.0)

                points.append(
                    ImplantPoint(
                        label=label,
                        x=x, y=y, z=z,
                        nx=floats[0], ny=floats[1], nz=floats[2],
                        tx=floats[3], ty=floats[4], tz=floats[5],
                    )
                )

        return points
