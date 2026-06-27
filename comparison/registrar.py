"""
registrar.py
============
Least-squares rigid-body registration (rotation + translation, no scaling)
via SVD decomposition (Kabsch algorithm).

Given matched point sets A (fit-check) and B (post-op), finds R and t such
that::

    A_aligned  ≈  R @ A + t  ≈  B

Residuals  Δx, Δy, Δz  (and |Δ| 3-D distance) per implant represent how
much each implant moved *relative to the best-fit arch alignment* — which is
the clinically relevant metric for follow-up comparisons.

Requires numpy.
"""

import math
from dataclasses import dataclass


@dataclass
class AlignedPoint:
    """Per-implant result after rigid registration."""

    label_a: str                 # fit-check label
    label_b: str                 # post-op label
    orig_a: tuple[float, ...]    # fit-check origin (raw)
    orig_b: tuple[float, ...]    # post-op origin (raw)
    aligned_a: tuple[float, ...] # fit-check after rigid transform → B frame
    delta_x: float
    delta_y: float
    delta_z: float
    distance_3d: float


# ---------------------------------------------------------------------------

def _origin(p) -> tuple[float, float, float]:
    if hasattr(p, "origin"):
        return p.origin
    return (p.x, p.y, p.z)


def register_and_compute_deltas(pairs: list) -> list[AlignedPoint]:
    """
    Apply Kabsch rigid-body alignment of fit-check → post-op and compute
    per-implant residuals.

    Parameters
    ----------
    pairs : list[MatchedPair]
        Output of :func:`~comparison.matcher.match_implants`.

    Returns
    -------
    list[AlignedPoint]
        One entry per implant in arch order.

    Raises
    ------
    ImportError
        If numpy is not installed.
    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError(
            "numpy is required for rigid-body registration. "
            "Install it with:  pip install numpy"
        )

    pts_a = np.array([_origin(pair.point_a) for pair in pairs], dtype=float)
    pts_b = np.array([_origin(pair.point_b) for pair in pairs], dtype=float)

    cen_a = pts_a.mean(axis=0)
    cen_b = pts_b.mean(axis=0)

    A_c = pts_a - cen_a
    B_c = pts_b - cen_b

    H = A_c.T @ B_c
    U, _S, Vt = np.linalg.svd(H)

    d = np.linalg.det(Vt.T @ U.T)
    D = np.diag([1.0, 1.0, d])
    R = Vt.T @ D @ U.T
    t = cen_b - R @ cen_a

    results: list[AlignedPoint] = []
    for pair, pa_raw, pb_raw in zip(pairs, pts_a, pts_b):
        aligned = R @ pa_raw + t
        dx = float(pb_raw[0] - aligned[0])
        dy = float(pb_raw[1] - aligned[1])
        dz = float(pb_raw[2] - aligned[2])
        dist = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        results.append(
            AlignedPoint(
                label_a=pair.label_a,
                label_b=pair.label_b,
                orig_a=tuple(float(x) for x in pa_raw),
                orig_b=tuple(float(x) for x in pb_raw),
                aligned_a=tuple(float(x) for x in aligned),
                delta_x=dx,
                delta_y=dy,
                delta_z=dz,
                distance_3d=dist,
            )
        )
    return results
