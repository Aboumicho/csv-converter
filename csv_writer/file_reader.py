"""
file_reader.py
==============
Parses TransformedPoints ``.txt`` files into :class:`CoordinateFrame` objects
and provides divergence-angle helpers.

Input format
------------
Whitespace-delimited rows, four per coordinate frame::

    <PREFIX>_Origin   X  Y  Z
    <PREFIX>_X        X  Y  Z
    <PREFIX>_Y        X  Y  Z
    <PREFIX>_Z        X  Y  Z

A single file may contain several frames (different prefixes).
"""

import math


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _normalize(v):
    mag = math.sqrt(sum(x * x for x in v))
    if mag == 0:
        raise ValueError("Zero-length vector - check Origin/axis points.")
    return tuple(x / mag for x in v)


def _angle_between_deg(n1, n2):
    """Angle in degrees between two unit vectors."""
    cos_theta = max(-1.0, min(1.0, _dot(n1, n2)))
    return math.degrees(math.acos(cos_theta))


# ---------------------------------------------------------------------------
# Coordinate frame
# ---------------------------------------------------------------------------

class CoordinateFrame:
    """
    A right-handed orthonormal frame built from an origin and three axis
    endpoint positions.  Axis directions are derived by subtracting the origin.

    Parameters
    ----------
    frame_dict : dict
        Must contain keys ``prefix``, ``origin``, ``x``, ``y`` and ``z`` where
        each coordinate value is an ``(X, Y, Z)`` tuple.
    """

    def __init__(self, frame_dict: dict):
        origin = frame_dict["origin"]
        self.origin = origin
        self.prefix = frame_dict["prefix"]

        raw_x = _sub(frame_dict["x"], origin)
        raw_y = _sub(frame_dict["y"], origin)
        raw_z = _sub(frame_dict["z"], origin)

        self.z_axis = _normalize(raw_z)   # normal
        self.x_axis = _normalize(raw_x)   # tangent
        self.y_axis = _normalize(raw_y)   # binormal

    def __repr__(self) -> str:
        return f"CoordinateFrame(prefix={self.prefix!r}, origin={self.origin})"


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------

class TxtReader:
    """
    Reads a whitespace-delimited TransformedPoints ``.txt`` file and returns a
    list of :class:`CoordinateFrame` objects, one per detected prefix.
    """

    SUFFIXES = ("Origin", "X", "Y", "Z")

    def __init__(self, filepath: str):
        self.filepath = filepath

    # ----------------------------------------------------------
    def read(self) -> list:
        """
        Parse the file and build coordinate frames.

        Returns
        -------
        list[CoordinateFrame]
            Frames in first-seen order.
        """
        # prefix -> {"Origin": (x,y,z), "X": ..., "Y": ..., "Z": ...}
        groups: dict[str, dict] = {}
        order: list[str] = []

        with open(self.filepath, "r", encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) != 4:
                    print(f"[WARNING] Skipping malformed line: {line!r}")
                    continue

                name, *coords = parts
                if "_" not in name:
                    print(f"[WARNING] Skipping point without prefix: {name!r}")
                    continue

                prefix, suffix = name.rsplit("_", 1)
                if suffix not in self.SUFFIXES:
                    print(f"[WARNING] Unknown suffix in point: {name!r}")
                    continue

                xyz = tuple(float(c) for c in coords)
                if prefix not in groups:
                    groups[prefix] = {}
                    order.append(prefix)
                groups[prefix][suffix] = xyz

        frames: list[CoordinateFrame] = []
        for prefix in order:
            data = groups[prefix]
            missing = [s for s in self.SUFFIXES if s not in data]
            if missing:
                print(f"[WARNING] Frame {prefix!r} missing {missing}; skipping.")
                continue
            frames.append(
                CoordinateFrame(
                    {
                        "prefix": prefix,
                        "origin": data["Origin"],
                        "x": data["X"],
                        "y": data["Y"],
                        "z": data["Z"],
                    }
                )
            )

        return frames


# ---------------------------------------------------------------------------
# Divergence helpers
# ---------------------------------------------------------------------------

def all_divergence_pairs(frames: list) -> list:
    """
    Compute the divergence angle (between Z-axis normals) for every unordered
    pair of frames.

    Returns
    -------
    list[tuple[float, str, str]]
        ``(angle_deg, prefix_a, prefix_b)`` sorted by angle, highest first.
    """
    pairs = []
    for i in range(len(frames)):
        for j in range(i + 1, len(frames)):
            angle = _angle_between_deg(frames[i].z_axis, frames[j].z_axis)
            pairs.append((angle, frames[i].prefix, frames[j].prefix))
    pairs.sort(key=lambda t: t[0], reverse=True)
    return pairs


def max_divergence(frames: list):
    """
    Return the maximum divergence pair.

    Returns
    -------
    tuple[float, str | None, str | None]
        ``(angle_deg, prefix_a, prefix_b)`` for the widest pair, or
        ``(0.0, None, None)`` when fewer than two frames are present.
    """
    pairs = all_divergence_pairs(frames)
    if not pairs:
        return 0.0, None, None
    return pairs[0]
