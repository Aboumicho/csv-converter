"""
file_reader.py
==============
Responsible for:
  - Parsing whitespace-delimited TransformedPoints .txt files
  - Building CoordinateFrame objects (origin + normalised X/Y/Z axes)
  - Computing pairwise divergence angles between frames

Public API
----------
  TxtReader(filepath).read()  ->  list[CoordinateFrame]
  max_divergence(frames)      ->  (angle_deg, prefix_A, prefix_B)
  all_divergence_pairs(frames)->  [(angle_deg, prefix_A, prefix_B), ...]
"""

import itertools
import math
from collections import defaultdict


# ============================================================
#  Math helpers (module-private, re-exported for sibling modules)
# ============================================================

def _sub(a: tuple, b: tuple) -> tuple:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def _normalize(v: tuple) -> tuple:
    mag = math.sqrt(sum(x*x for x in v))
    if mag == 0:
        raise ValueError(f"Zero-length vector {v!r} – check axis points.")
    return tuple(x/mag for x in v)


def _dot(a: tuple, b: tuple) -> float:
    return sum(x*y for x, y in zip(a, b))


def _cross(a: tuple, b: tuple) -> tuple:
    return (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0],
    )


def _angle_deg(n1: tuple, n2: tuple) -> float:
    """Angle in degrees between two unit vectors (numerically clamped)."""
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(n1, n2)))))


# ============================================================
#  CoordinateFrame
# ============================================================

class CoordinateFrame:
    """
    Orthonormal axis frame derived from four raw 3-D points.

    Attributes
    ----------
    prefix  : str    – tooth identifier (e.g. '32', '34')
    origin  : tuple  – (X, Y, Z) of the _Origin point
    z_axis  : tuple  – normalised implant / normal direction  (_Z − origin)
    x_axis  : tuple  – normalised tangent direction           (_X − origin)
    y_axis  : tuple  – normalised binormal direction          (_Y − origin)
    """

    def __init__(self, prefix: str, pts: dict):
        """
        Parameters
        ----------
        prefix : str
            Common prefix shared by the four point names (e.g. '32').
        pts : dict
            Keys '_Origin', '_X', '_Y', '_Z' → (x, y, z) tuples.
        """
        self.prefix = prefix
        self.origin = pts["_Origin"]
        self.z_axis = _normalize(_sub(pts["_Z"], self.origin))
        self.x_axis = _normalize(_sub(pts["_X"], self.origin))
        self.y_axis = _normalize(_sub(pts["_Y"], self.origin))

    def __repr__(self) -> str:
        return (
            f"CoordinateFrame(prefix={self.prefix!r}, "
            f"origin={self.origin}, z_axis={self.z_axis})"
        )


# ============================================================
#  TxtReader
# ============================================================

class TxtReader:
    """
    Reads a whitespace-delimited TransformedPoints .txt file.

    File format (no header, one point per line):
        <PREFIX>_Origin   X   Y   Z
        <PREFIX>_X        X   Y   Z
        <PREFIX>_Y        X   Y   Z
        <PREFIX>_Z        X   Y   Z

    Any number of tooth groups may appear in a single file.
    Lines that are blank or malformed are skipped with a warning.
    """

    SUFFIXES = ("_Origin", "_X", "_Y", "_Z")

    def __init__(self, filepath: str):
        self.filepath = filepath

    # ----------------------------------------------------------
    def read(self) -> list[CoordinateFrame]:
        """
        Parse the file and return one CoordinateFrame per tooth,
        in the order they first appear.

        Returns
        -------
        list[CoordinateFrame]
        """
        raw    = self._parse_lines()
        groups = self._group_by_prefix(raw)
        frames = []
        for prefix, pts in groups.items():
            self._validate(prefix, pts)
            frames.append(CoordinateFrame(prefix, pts))
        return frames

    # ----------------------------------------------------------
    def _parse_lines(self) -> dict:
        """Return {point_name: (x, y, z)} for every valid line."""
        result = {}
        with open(self.filepath, encoding="utf-8-sig") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) != 4:
                    print(
                        f"  [WARN] {self.filepath}:{lineno} – "
                        f"expected 4 fields, got {len(parts)}: {line!r}"
                    )
                    continue
                name = parts[0]
                try:
                    xyz = (float(parts[1]), float(parts[2]), float(parts[3]))
                except ValueError:
                    print(
                        f"  [WARN] {self.filepath}:{lineno} – "
                        f"non-numeric coordinates: {line!r}"
                    )
                    continue
                result[name] = xyz
        return result

    def _group_by_prefix(self, raw: dict) -> dict:
        """Group {suffix: xyz} dicts by tooth prefix, preserving file order."""
        groups: dict[str, dict] = defaultdict(dict)
        for name, xyz in raw.items():
            for suffix in self.SUFFIXES:
                if name.endswith(suffix):
                    groups[name[: -len(suffix)]][suffix] = xyz
                    break

        # Rebuild in first-seen order
        ordered: dict[str, dict] = {}
        for name in raw:
            for suffix in self.SUFFIXES:
                if name.endswith(suffix):
                    prefix = name[: -len(suffix)]
                    if prefix not in ordered:
                        ordered[prefix] = groups[prefix]
                    break
        return ordered

    def _validate(self, prefix: str, pts: dict) -> None:
        missing = [s for s in self.SUFFIXES if s not in pts]
        if missing:
            raise ValueError(
                f"Prefix '{prefix}' is missing row(s) {missing} "
                f"in '{self.filepath}'"
            )


# ============================================================
#  Divergence utilities
# ============================================================

def max_divergence(frames: list[CoordinateFrame]) -> tuple:
    """
    Return the pair of frames with the largest Z-axis divergence angle.

    Returns
    -------
    (angle_deg, prefix_A, prefix_B)
        angle_deg is 0.0 and prefixes are None when fewer than 2 frames.
    """
    if len(frames) < 2:
        return (0.0, None, None)

    worst = (0.0, None, None)
    for fa, fb in itertools.combinations(frames, 2):
        angle = _angle_deg(fa.z_axis, fb.z_axis)
        if angle > worst[0]:
            worst = (angle, fa.prefix, fb.prefix)
    return worst


def all_divergence_pairs(frames: list[CoordinateFrame]) -> list[tuple]:
    """
    Return all pairwise divergence angles, sorted highest first.

    Returns
    -------
    list of (angle_deg, prefix_A, prefix_B)
    """
    pairs = [
        (_angle_deg(fa.z_axis, fb.z_axis), fa.prefix, fb.prefix)
        for fa, fb in itertools.combinations(frames, 2)
    ]
    pairs.sort(reverse=True)
    return pairs
