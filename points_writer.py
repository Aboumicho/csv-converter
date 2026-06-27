"""
points_writer.py
============================
Reads a TransformedPoints CSV (Point, X, Y, Z — with rows for Origin, X, Y, Z
axis endpoints) and outputs:
  1. A MicronMapper-compatible CSV  (position + Z-normal + X-tangent + metadata)
  2. A binary STL file with a 3-D coordinate-frame marker at the origin

Columns in the output CSV match the MicronMapper format exactly:
  PointName, X, Y, Z, nx, ny, nz, tx, ty, tz

followed by:
  Max divergence angle: <pair> <angle> deg
  Application:, MicronMapper V1.5.0.41871, ...
  Camera:, <serial>
"""

import csv
import os

from vec3 import sub, normalize, cross
from stl_utils import write_binary_stl
from csv_writer.file_reader import CoordinateFrame
from csv_writer.csv_writer import MicronMapperCSVWriter


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------

class TransformedPointsReader:
    """Parse a TransformedPoints CSV into a CoordinateFrame."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> dict:
        """
        Returns dict with keys 'prefix', 'origin', 'x', 'y', 'z' —
        each coordinate value is an (X, Y, Z) tuple.
        """
        rows = {}
        with open(self.filepath, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = row["Point"].strip()
                xyz  = (float(row["X"]), float(row["Y"]), float(row["Z"]))
                rows[name] = xyz

        # Detect prefix (anything before the last '_' segment)
        prefix = None
        for key in rows:
            for suffix in ("_Origin", "_X", "_Y", "_Z"):
                if key.endswith(suffix):
                    candidate = key[: -len(suffix)]
                    prefix = candidate
                    break
            if prefix:
                break

        if prefix is None:
            raise ValueError("Cannot detect prefix — expected rows ending in _Origin/_X/_Y/_Z.")

        return {
            "prefix":  prefix,
            "origin":  rows[f"{prefix}_Origin"],
            "x":       rows[f"{prefix}_X"],
            "y":       rows[f"{prefix}_Y"],
            "z":       rows[f"{prefix}_Z"],
        }


# ---------------------------------------------------------------------------
# STL writer — axis-frame marker geometry
# ---------------------------------------------------------------------------

class AxisMarkerSTLWriter:
    """
    Generates a binary STL that visualises the coordinate frame:
      - A small sphere-like octahedron at the origin
      - Three thin rectangular prisms along +X, +Y, +Z (colour by convention)

    All geometry is centred on frame.origin and scaled to `axis_length`.
    """

    def __init__(
        self,
        frames: list,
        output_path: str,
        axis_length: float = 5.0,
        shaft_radius: float = 0.3,
    ):
        self.frames       = frames
        self.output_path  = output_path
        self.axis_length  = axis_length
        self.shaft_radius = shaft_radius
        self._triangles: list = []

    def write(self) -> str:
        self._triangles.clear()
        for frame in self.frames:
            self._add_frame_geometry(frame)

        write_binary_stl(self.output_path, self._triangles)

        print(f"[OK] STL  → '{self.output_path}' ({len(self._triangles)} triangles)")
        return self.output_path

    # ------------------------------------------------------------------
    # Geometry builders
    # ------------------------------------------------------------------

    def _add_frame_geometry(self, frame) -> None:
        O  = frame.origin
        ZA = frame.z_axis
        XA = frame.x_axis
        YA = frame.y_axis

        r  = self.shaft_radius
        L  = self.axis_length

        self._add_octahedron(O, r * 2.5)

        for axis in (XA, YA, ZA):
            self._add_prism(O, axis, L, r)

    def _add_octahedron(self, centre, half_size):
        """6-vertex octahedron (8 triangles)."""
        c = centre
        h = half_size
        pts = {
            "+x": (c[0]+h, c[1],   c[2]  ),
            "-x": (c[0]-h, c[1],   c[2]  ),
            "+y": (c[0],   c[1]+h, c[2]  ),
            "-y": (c[0],   c[1]-h, c[2]  ),
            "+z": (c[0],   c[1],   c[2]+h),
            "-z": (c[0],   c[1],   c[2]-h),
        }
        faces = [
            (pts["+x"], pts["+y"], pts["+z"]),
            (pts["+y"], pts["-x"], pts["+z"]),
            (pts["-x"], pts["-y"], pts["+z"]),
            (pts["-y"], pts["+x"], pts["+z"]),
            (pts["+y"], pts["+x"], pts["-z"]),
            (pts["-x"], pts["+y"], pts["-z"]),
            (pts["-y"], pts["-x"], pts["-z"]),
            (pts["+x"], pts["-y"], pts["-z"]),
        ]
        for v1, v2, v3 in faces:
            n = normalize(cross(sub(v2, v1), sub(v3, v1)))
            self._triangles.append((n, v1, v2, v3))

    def _add_prism(self, origin, axis, length, radius):
        """
        Square-cross-section prism along `axis` from `origin`.
        Creates 8 triangles (4 side faces × 2 triangles each).
        """
        ref = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
        u = normalize(cross(axis, ref))
        v = normalize(cross(axis, u))

        r = radius
        tip = (origin[0] + axis[0]*length,
               origin[1] + axis[1]*length,
               origin[2] + axis[2]*length)

        def corner(base, du, dv):
            return (base[0] + u[0]*du + v[0]*dv,
                    base[1] + u[1]*du + v[1]*dv,
                    base[2] + u[2]*du + v[2]*dv)

        b0 = corner(origin, +r, +r)
        b1 = corner(origin, -r, +r)
        b2 = corner(origin, -r, -r)
        b3 = corner(origin, +r, -r)
        t0 = corner(tip,    +r, +r)
        t1 = corner(tip,    -r, +r)
        t2 = corner(tip,    -r, -r)
        t3 = corner(tip,    +r, -r)

        side_faces = [
            (b0, t0, t1, b1),
            (b1, t1, t2, b2),
            (b2, t2, t3, b3),
            (b3, t3, t0, b0),
        ]
        for p0, p1, p2, p3 in side_faces:
            n = normalize(cross(sub(p1, p0), sub(p2, p0)))
            self._triangles.append((n, p0, p1, p2))
            self._triangles.append((n, p0, p2, p3))


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class TransformedPointsPipeline:
    """
    Full pipeline:
      1. Read one or more TransformedPoints CSV files
      2. Compute coordinate frames
      3. Write MicronMapper-compatible CSV
      4. Write binary STL
    """

    def __init__(
        self,
        input_paths: list,
        output_dir: str = "output",
        camera_serial: str = "00000000",
        axis_length: float = 5.0,
    ):
        self.input_paths   = input_paths
        self.output_dir    = output_dir
        self.camera_serial = camera_serial
        self.axis_length   = axis_length

    def run(self):
        frames = []
        for path in self.input_paths:
            reader = TransformedPointsReader(path)
            data   = reader.read()
            frame  = CoordinateFrame(data)
            frames.append(frame)
            print(f"[READ] {path}")
            print(f"       prefix  = {frame.prefix}")
            print(f"       origin  = {frame.origin}")
            print(f"       Z-axis  = {frame.z_axis}")
            print(f"       X-axis  = {frame.x_axis}")

        base    = os.path.splitext(os.path.basename(self.input_paths[0]))[0]
        csv_out = os.path.join(self.output_dir, f"{base}_MicronMapper.csv")
        stl_out = os.path.join(self.output_dir, f"{base}.stl")

        MicronMapperCSVWriter(
            frames,
            csv_out,
            camera_serial=self.camera_serial,
        ).write()

        AxisMarkerSTLWriter(
            frames,
            stl_out,
            axis_length=self.axis_length,
        ).write()

        return csv_out, stl_out


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    inputs = sys.argv[1:] if len(sys.argv) > 1 else [
        "/mnt/user-data/uploads/TransformedPoints_32.csv"
    ]

    pipeline = TransformedPointsPipeline(
        input_paths=inputs,
        output_dir="/home/claude/output",
        camera_serial="00000000",
        axis_length=10.0,
    )
    pipeline.run()
