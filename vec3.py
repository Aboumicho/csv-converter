"""
vec3.py
=======
Lightweight 3-D vector helpers used throughout the conversion pipeline.

All vectors are plain ``(x, y, z)`` tuples — no external dependencies.
"""

import math


def sub(a: tuple, b: tuple) -> tuple:
    """Component-wise subtraction *a − b*."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def normalize(v: tuple) -> tuple:
    """Return the unit vector of *v*.  Raises on zero-length input."""
    mag = math.sqrt(sum(c * c for c in v))
    if mag == 0:
        raise ValueError(f"Zero-length vector {v!r} – check axis points.")
    return tuple(c / mag for c in v)


def dot(a: tuple, b: tuple) -> float:
    """Dot product of two 3-D vectors."""
    return sum(x * y for x, y in zip(a, b))


def cross(a: tuple, b: tuple) -> tuple:
    """Cross product *a × b*."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def angle_deg(n1: tuple, n2: tuple) -> float:
    """Angle in degrees between two unit vectors (numerically clamped)."""
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(n1, n2)))))
