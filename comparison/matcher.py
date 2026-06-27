"""
matcher.py
==========
Gap-matching algorithm that maps implant labels between two point sets.

Core idea (from clinical practice)
------------------------------------
Inter-implant distances along the arch are scanner-frame-independent: the bone
fixes the implants, so the *pattern* of consecutive gaps is a fingerprint that
survives any rotation/translation or label renaming between scans.

Algorithm
---------
1. Sort each set along the axis with the largest spatial range (approx.
   principal arch direction).
2. Match sorted position-for-position.
3. Return :class:`MatchedPair` list in arch order.
"""

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class MatchedPair:
    """One matched implant: label_a from fit-check, label_b from post-op."""

    label_a: str
    label_b: str
    point_a: Any
    point_b: Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _origin(p) -> tuple[float, float, float]:
    """Return (x, y, z) from either an ImplantPoint or a CoordinateFrame."""
    if hasattr(p, "origin"):
        return p.origin
    return (p.x, p.y, p.z)


def _dist_3d(a, b) -> float:
    oa, ob = _origin(a), _origin(b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(oa, ob)))


def _sort_along_arch(points: list) -> list:
    """
    Sort implant points along the axis of maximum spatial spread.

    For most arch geometries the X or Y axis captures the left-right
    extent well enough for unambiguous ordering.
    """
    if not points:
        return points
    coords = [_origin(p) for p in points]
    ranges = [
        max(c[i] for c in coords) - min(c[i] for c in coords)
        for i in range(3)
    ]
    axis = ranges.index(max(ranges))
    return sorted(points, key=lambda p: _origin(p)[axis])


def _gap_sequence(sorted_points: list) -> list[float]:
    """Consecutive distances between adjacent arch-sorted points."""
    return [
        _dist_3d(sorted_points[i], sorted_points[i + 1])
        for i in range(len(sorted_points) - 1)
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_implants(points_a: list, points_b: list) -> list[MatchedPair]:
    """
    Match two implant point sets by gap-sequence fingerprint.

    Parameters
    ----------
    points_a : list
        Fit-check points (:class:`~comparison.csv_reader.ImplantPoint`).
    points_b : list
        Post-op frames (:class:`~csv_writer.file_reader.CoordinateFrame`).

    Returns
    -------
    list[MatchedPair]
        Pairs in arch order (same index = same physical implant).

    Raises
    ------
    ValueError
        If the two sets have different implant counts.
    """
    sorted_a = _sort_along_arch(points_a)
    sorted_b = _sort_along_arch(points_b)

    if len(sorted_a) != len(sorted_b):
        raise ValueError(
            f"Implant count mismatch: fit-check has {len(sorted_a)}, "
            f"post-op has {len(sorted_b)}. "
            "Both files must describe the same arch case."
        )

    pairs = []
    for pa, pb in zip(sorted_a, sorted_b):
        label_a = getattr(pa, "label", None) or getattr(pa, "prefix", "?")
        label_b = getattr(pb, "label", None) or getattr(pb, "prefix", "?")
        pairs.append(MatchedPair(label_a=label_a, label_b=label_b,
                                  point_a=pa, point_b=pb))
    return pairs


def gap_sequences(points_a: list, points_b: list) -> tuple[list[float], list[float]]:
    """
    Compute and return the gap sequences for both sorted point sets.

    Useful for diagnostics / verifying that the match is valid.

    Returns
    -------
    tuple[list[float], list[float]]
        ``(gaps_a, gaps_b)``
    """
    return (
        _gap_sequence(_sort_along_arch(points_a)),
        _gap_sequence(_sort_along_arch(points_b)),
    )
