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
import math
import os
import struct
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sub(a, b):
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])

def _normalize(v):
    mag = math.sqrt(sum(x*x for x in v))
    if mag == 0:
        raise ValueError("Zero-length vector – check Origin/axis points.")
    return tuple(x/mag for x in v)

def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))

def _cross(a, b):
    return (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0],
    )

def _angle_between_deg(n1, n2):
    """Angle in degrees between two unit vectors."""
    cos_theta = max(-1.0, min(1.0, _dot(n1, n2)))
    return math.degrees(math.acos(cos_theta))


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------

class TransformedPointsReader:
    """Parse a TransformedPoints CSV into a frame dict keyed by suffix."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> dict:
        """
        Returns dict with keys 'origin', 'x', 'y', 'z' — each a (X,Y,Z) tuple,
        plus 'prefix' (the common part before _Origin/_X/_Y/_Z).
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
# Frame computation
# ---------------------------------------------------------------------------

class CoordinateFrame:
    """
    Builds a right-handed orthonormal frame from origin + 3 axis endpoint positions.
    Axis directions are derived by subtracting the origin.
    """

    def __init__(self, frame_dict: dict):
        origin = frame_dict["origin"]
        self.origin   = origin
        self.prefix   = frame_dict["prefix"]

        # Raw axis vectors
        raw_x = _sub(frame_dict["x"], origin)
        raw_y = _sub(frame_dict["y"], origin)
        raw_z = _sub(frame_dict["z"], origin)

        # Normalise — Z is the primary axis (implant/normal direction)
        self.z_axis = _normalize(raw_z)   # normal
        self.x_axis = _normalize(raw_x)   # tangent
        self.y_axis = _normalize(raw_y)   # binormal (for completeness)


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

class MicronMapperCSVWriter:
    """
    Writes a single-frame MicronMapper-compatible CSV.
    If you have multiple frames, call write() once per frame and append.
    """

    def __init__(
        self,
        frames: list,
        output_path: str,
        camera_serial: str = "00000000",
        application: str = "MicronMapper V1.5.0.41871, built 6/5/2025",
    ):
        self.frames      = frames
        self.output_path = output_path
        self.camera      = camera_serial
        self.application = application

    # ------------------------------------------------------------------
    def write(self) -> str:
        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)

        with open(self.output_path, "w", newline="", encoding="utf-8") as fh:
            for frame in self.frames:
                ox, oy, oz   = frame.origin
                nx, ny, nz   = frame.z_axis   # normal (Z axis)
                tx, ty, tz   = frame.x_axis   # tangent (X axis)
                fh.write(
                    f"{frame.prefix},"
                    f" {ox:.5f}, {oy:.5f}, {oz:.5f},"
                    f"{nx:.6f},{ny:.6f},{nz:.6f},"
                    f"{tx:.6f}, {ty:.6f}, {tz:.6f}\r\n"
                )

            fh.write("\r\n")

            # Max divergence angle (between first and last frame normals)
            if len(self.frames) >= 2:
                angle = _angle_between_deg(
                    self.frames[0].z_axis, self.frames[-1].z_axis
                )
                fh.write(
                    f"Max divergence angle: "
                    f"{self.frames[0].prefix}-{self.frames[-1].prefix} "
                    f"{angle:.1f} deg\r\n"
                )
            else:
                fh.write("Max divergence angle: N/A\r\n")

            fh.write("\r\n")
            now_str = datetime.now().strftime("%A, %B %d, %Y %I:%M:%S %p")
            fh.write(f"Application:, {self.application},   now {now_str}\r\n")
            fh.write(f"Camera:, {self.camera}\r\n")

        print(f"[OK] CSV  → '{self.output_path}'")
        return self.output_path


# ---------------------------------------------------------------------------
# STL writer — binary format
# ---------------------------------------------------------------------------

class STLWriter:
    """
    Generates a binary STL that visualises the coordinate frame:
      • A small sphere-like octahedron at the origin
      • Three thin rectangular prisms along +X, +Y, +Z (colour by convention)

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
        self._triangles: list = []   # list of (normal, v1, v2, v3)

    # ------------------------------------------------------------------
    def write(self) -> str:
        self._triangles.clear()
        for frame in self.frames:
            self._add_frame_geometry(frame)

        os.makedirs(os.path.dirname(self.output_path) or ".", exist_ok=True)

        with open(self.output_path, "wb") as fh:
            header = b"\x00" * 80
            fh.write(header)
            fh.write(struct.pack("<I", len(self._triangles)))
            for normal, v1, v2, v3 in self._triangles:
                fh.write(struct.pack("<fff", *normal))
                fh.write(struct.pack("<fff", *v1))
                fh.write(struct.pack("<fff", *v2))
                fh.write(struct.pack("<fff", *v3))
                fh.write(b"\x00\x00")          # attribute byte count

        print(f"[OK] STL  → '{self.output_path}' ({len(self._triangles)} triangles)")
        return self.output_path

    # ------------------------------------------------------------------
    # Geometry builders
    # ------------------------------------------------------------------

    def _add_frame_geometry(self, frame: CoordinateFrame) -> None:
        O  = frame.origin
        ZA = frame.z_axis
        XA = frame.x_axis
        YA = frame.y_axis

        r  = self.shaft_radius
        L  = self.axis_length

        # --- origin marker: small octahedron ---
        self._add_octahedron(O, r * 2.5)

        # --- axis shafts: rectangular prisms along each axis ---
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
            n = _normalize(_cross(_sub(v2, v1), _sub(v3, v1)))
            self._triangles.append((n, v1, v2, v3))

    def _add_prism(self, origin, axis, length, radius):
        """
        Square-cross-section prism along `axis` from `origin`.
        Creates 8 triangles (4 side faces × 2 triangles each).
        End caps are omitted to keep the model light.
        """
        # Build a perpendicular basis
        ref = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.9 else (1.0, 0.0, 0.0)
        u = _normalize(_cross(axis, ref))
        v = _normalize(_cross(axis, u))

        r = radius
        tip = (origin[0] + axis[0]*length,
               origin[1] + axis[1]*length,
               origin[2] + axis[2]*length)

        # 4 corners at base and tip
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
            (b0, t0, t1, b1),  # +u face
            (b1, t1, t2, b2),  # -v face
            (b2, t2, t3, b3),  # -u face
            (b3, t3, t0, b0),  # +v face
        ]
        for p0, p1, p2, p3 in side_faces:
            n = _normalize(_cross(_sub(p1, p0), _sub(p2, p0)))
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

        # Derive a base name from the first input file
        base    = os.path.splitext(os.path.basename(self.input_paths[0]))[0]
        csv_out = os.path.join(self.output_dir, f"{base}_MicronMapper.csv")
        stl_out = os.path.join(self.output_dir, f"{base}.stl")

        MicronMapperCSVWriter(
            frames,
            csv_out,
            camera_serial=self.camera_serial,
        ).write()

        STLWriter(
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

    # Default: process the uploaded file
    inputs = sys.argv[1:] if len(sys.argv) > 1 else [
        "/mnt/user-data/uploads/TransformedPoints_32.csv"
    ]

    pipeline = TransformedPointsPipeline(
        input_paths=inputs,
        output_dir="/home/claude/output",
        camera_serial="00000000",   # ← replace with real camera serial if known
        axis_length=10.0,           # ← length of axis arms in the STL (mm)
    )
    pipeline.run()
